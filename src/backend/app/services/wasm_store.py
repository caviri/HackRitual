"""
WASM scorer module storage and the event's active-scorer reference.

Modules are content-addressed: stored at ``<data>/scoring/<sha256>.wasm`` and
versioned as ``wasm:sha256:<hash>``. The event config's ``scorer`` key points at
the active module; clearing it falls back to the default Python scorer.
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.services.event import dump_config, get_event, load_config

WASM_MAGIC = b"\x00asm"


def is_valid_wasm(data: bytes) -> bool:
    """A WASM binary starts with the magic `\\0asm` and a version word."""
    return len(data) >= 8 and data[:4] == WASM_MAGIC


def scoring_dir() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(settings.db_path)), "scoring")
    os.makedirs(path, exist_ok=True)
    return path


def wasm_path_for(sha: str) -> str:
    return os.path.join(scoring_dir(), f"{sha}.wasm")


def save_wasm(data: bytes) -> tuple[str, str]:
    """Persist a module by content hash. Returns (sha256, absolute_path)."""
    sha = hashlib.sha256(data).hexdigest()
    path = wasm_path_for(sha)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    return sha, path


# --------------------------------------------------------------------------- #
# Active-scorer reference (lives in event config)
# --------------------------------------------------------------------------- #
def get_active_scorer(db: Session) -> Optional[dict]:
    """The event's configured scorer, or None (→ default Python scorer)."""
    return load_config(get_event(db)).get("scorer")


def set_active_scorer(db: Session, scorer: Optional[dict]) -> None:
    event = get_event(db)
    config = load_config(event)
    if scorer is None:
        config.pop("scorer", None)
    else:
        config["scorer"] = scorer
    event.config_json = dump_config(config)
    db.commit()


def load_wasm_bytes(scorer: dict) -> Optional[bytes]:
    """Read the module bytes for a wasm scorer reference, if present on disk."""
    path = scorer.get("path")
    if not path:
        return None
    abs_path = path if os.path.isabs(path) else os.path.join(scoring_dir(), os.path.basename(path))
    if not os.path.exists(abs_path):
        return None
    with open(abs_path, "rb") as f:
        return f.read()
