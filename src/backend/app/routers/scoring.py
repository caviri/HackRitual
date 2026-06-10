"""
WASM scorer management (MVP-3, Step 16).

Admins upload a `.wasm` scorer (validated and test-run before it goes live),
inspect the active scorer, and queue a re-score of every submission. The module
can also be served to the browser for unofficial client-side preview.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    File as FastAPIFile,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.submission import Submission
from app.models.user import User
from app.services import task_queue, wasm_store
from app.services.audit import log_action

admin_wasm_router = APIRouter(prefix="/api/admin/scoring", tags=["scoring"])
public_scoring_router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@admin_wasm_router.post("/upload-wasm")
async def upload_wasm(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Validate, store, test-run, and activate an uploaded WASM scorer."""
    from app.scoring.wasm_scorer import WasmScorer, wasmtime_available

    if not wasmtime_available():
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "WASM runtime not available on this deployment",
        )

    data = await file.read()
    if not wasm_store.is_valid_wasm(data):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "not a valid WASM module (bad magic)"
        )

    sha, _path = wasm_store.save_wasm(data)
    version = f"wasm:sha256:{sha}"

    # Test-run with a sample input before going live.
    try:
        scorer = WasmScorer(
            data,
            version=version,
            time_limit_ms=settings.wasm_time_limit_ms,
            memory_limit_mb=settings.wasm_memory_limit_mb,
        )
        start = time.perf_counter()
        result = scorer.score(
            {"title": "sample", "description": "sample", "payload_json": {"k": 1}}, []
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"module failed to load/run: {exc}",
        )
    if result.status != "scored":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"module test run did not score: {result.error}",
        )

    scorer_ref = {
        "type": "wasm",
        "version": version,
        "path": f"{sha}.wasm",
        "size_bytes": len(data),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "time_limit_ms": settings.wasm_time_limit_ms,
        "memory_limit_mb": settings.wasm_memory_limit_mb,
    }
    wasm_store.set_active_scorer(db, scorer_ref)
    log_action(
        db,
        "scoring.wasm_uploaded",
        actor_id=admin.id,
        target_type="scorer",
        target_id=version,
        metadata={"size_bytes": len(data)},
    )
    db.commit()

    return {
        "scorer_type": "wasm",
        "scorer_version": version,
        "file_size_bytes": len(data),
        "validated": True,
        "test_result": {
            "score": result.score_value,
            "status": result.status,
            "execution_time_ms": elapsed_ms,
        },
    }


@admin_wasm_router.get("/info")
def scorer_info(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """The active scorer — WASM module reference, or the default Python scorer."""
    scorer = wasm_store.get_active_scorer(db)
    if scorer and scorer.get("type") == "wasm":
        return {
            "scorer_type": "wasm",
            "scorer_version": scorer.get("version"),
            "uploaded_at": scorer.get("uploaded_at"),
            "memory_limit_mb": scorer.get("memory_limit_mb"),
            "time_limit_ms": scorer.get("time_limit_ms"),
        }
    from app.scoring import DefaultScorer

    return {
        "scorer_type": "python",
        "scorer_version": DefaultScorer().version,
        "memory_limit_mb": None,
        "time_limit_ms": None,
    }


@admin_wasm_router.post("/rescore-all")
def rescore_all(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Queue a re-score for every non-withdrawn submission (via the task queue)."""
    subs = (
        db.query(Submission.id)
        .filter(
            Submission.event_id == settings.event_id,
            Submission.status != "withdrawn",
        )
        .all()
    )
    for (sub_id,) in subs:
        task_queue.enqueue(db, "score_submission", ref_id=sub_id)
    log_action(
        db,
        "scoring.rescore_all",
        actor_id=admin.id,
        target_type="event",
        target_id=settings.event_id,
        metadata={"queued": len(subs)},
    )
    db.commit()
    return {"queued": len(subs)}


@public_scoring_router.get("/preview-module")
def preview_module(db: Session = Depends(get_db)) -> Response:
    """Serve the active WASM module for unofficial client-side preview."""
    scorer = wasm_store.get_active_scorer(db)
    if not scorer or scorer.get("type") != "wasm":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no WASM scorer configured")
    data = wasm_store.load_wasm_bytes(scorer)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "module not found")
    return Response(
        content=data,
        media_type="application/wasm",
        headers={"Cache-Control": "no-store"},
    )
