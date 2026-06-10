"""
WASM scorer — deterministic, portable, sandboxed scoring (MVP-3).

An uploaded `.wasm` module is run server-side via `wasmtime` under time and
memory limits. The module exchanges JSON over linear memory:

    alloc(size) -> ptr          allocate scratch for the input
    score(ptr, len) -> out_ptr  run; return a pointer to the output JSON
    get_output_len() -> len     length of that output
    memory                       exported linear memory

Input  : {"submission": {...}, "files": [...]}
Output : {"score": float, "breakdown": {...}, "status": "scored", "error": null}

`wasmtime` is an optional dependency — import is lazy so the rest of the platform
runs without it; `wasmtime_available()` reports whether the runtime is present.
"""

from __future__ import annotations

import json

from app.scoring.base import BaseScorer, ScoreResult


def wasmtime_available() -> bool:
    try:
        import wasmtime  # noqa: F401

        return True
    except Exception:
        return False


class WasmScorer(BaseScorer):
    """Runs an uploaded WASM module as the scorer."""

    def __init__(
        self,
        wasm_bytes: bytes,
        version: str,
        time_limit_ms: int = 5000,
        memory_limit_mb: int = 64,
    ) -> None:
        import wasmtime

        self.version = version
        self._time_limit_ms = time_limit_ms

        config = wasmtime.Config()
        # Fuel meters execution so a runaway module can be cut off.
        try:
            config.consume_fuel = True
            self._fuel = True
        except Exception:
            self._fuel = False

        self._engine = wasmtime.Engine(config)
        self._store = wasmtime.Store(self._engine)

        # Best-effort memory ceiling (API varies across wasmtime versions).
        try:
            self._store.set_limits(memory_size=memory_limit_mb * 1024 * 1024)
        except Exception:
            pass

        self._module = wasmtime.Module(self._engine, wasm_bytes)
        self._linker = wasmtime.Linker(self._engine)
        self._instance = self._linker.instantiate(self._store, self._module)
        self._exports = self._instance.exports(self._store)

    def _fuel_top_up(self) -> None:
        if not self._fuel:
            return
        # Fuel units roughly track instructions; scale off the time budget.
        units = max(1_000_000, self._time_limit_ms * 2_000)
        for setter in ("set_fuel", "add_fuel"):
            fn = getattr(self._store, setter, None)
            if fn is not None:
                try:
                    fn(units)
                    return
                except Exception:
                    continue

    def score(self, submission_data: dict, files: list[dict]) -> ScoreResult:
        try:
            self._fuel_top_up()
            payload = json.dumps(
                {"submission": submission_data, "files": files}
            ).encode("utf-8")

            store = self._store
            alloc = self._exports["alloc"]
            score_fn = self._exports["score"]
            get_len = self._exports["get_output_len"]
            memory = self._exports["memory"]

            input_ptr = alloc(store, len(payload))
            memory.write(store, payload, input_ptr)

            output_ptr = score_fn(store, input_ptr, len(payload))
            output_len = get_len(store)
            raw = memory.read(store, output_ptr, output_ptr + output_len)
            result = json.loads(bytes(raw))

            return ScoreResult(
                score_value=float(result.get("score", 0)),
                breakdown=result.get("breakdown"),
                status=result.get("status", "scored"),
                error=result.get("error"),
            )
        except Exception as exc:  # noqa: BLE001 — a bad module is a failed score
            return ScoreResult(
                score_value=0.0,
                status="failed",
                error=f"scoring module error: {exc}"[:300],
            )
