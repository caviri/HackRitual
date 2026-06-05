# 16 — WASM Scoring Module

**Milestone:** MVP-3
**Priority:** Medium
**Dependencies:** [08-scoring-basic](08-scoring-basic.md), [14-task-queue-worker](14-task-queue-worker.md)
**Specs reference:** §7.5 (Scoring Modules), §11 (Client-side WASM/WebGPU)

---

## Overview

Replace or supplement the Python scoring function with a WASM module for deterministic, portable scoring. WASM modules are executed server-side using `wasmtime-py` with time/memory limits. Optionally, the same WASM can run client-side for preview — but client results are never trusted for the leaderboard.

---

## Tasks

### 16.1 WASM Scoring Interface

Define a standard WASM interface for scorers:

**WASM module must export:**
```
score(input_ptr: i32, input_len: i32) -> i32  // returns output_ptr
get_output_len() -> i32                        // returns last output length
alloc(size: i32) -> i32                        // allocate memory
dealloc(ptr: i32, size: i32)                   // free memory
```

**Input format (JSON bytes):**
```json
{
  "submission": {
    "title": "...",
    "description": "...",
    "payload": { ... }
  },
  "files": [
    { "name": "...", "sha256": "...", "size": 12345 }
  ]
}
```

**Output format (JSON bytes):**
```json
{
  "score": 85.5,
  "breakdown": { "accuracy": 70, "style": 15.5 },
  "status": "scored",
  "error": null
}
```

### 16.2 Server-Side WASM Runtime

```python
# backend/app/scoring/wasm_scorer.py

import wasmtime

class WasmScorer(BaseScorer):
    def __init__(self, wasm_path: str, time_limit_ms: int = 5000, memory_limit_mb: int = 64):
        self.engine = wasmtime.Engine(wasmtime.Config())
        self.store = wasmtime.Store(self.engine)

        # Configure limits
        self.store.set_limits(
            memory_size=memory_limit_mb * 1024 * 1024,
        )

        # Load module
        self.module = wasmtime.Module.from_file(self.engine, wasm_path)
        self.linker = wasmtime.Linker(self.engine)
        self.instance = self.linker.instantiate(self.store, self.module)

        # Get exports
        self.score_fn = self.instance.exports(self.store)["score"]
        self.alloc_fn = self.instance.exports(self.store)["alloc"]
        self.get_output_len = self.instance.exports(self.store)["get_output_len"]
        self.memory = self.instance.exports(self.store)["memory"]

    def score(self, submission_data: dict, files: list[dict]) -> ScoreResult:
        input_json = json.dumps({
            "submission": submission_data,
            "files": files,
        }).encode("utf-8")

        # Write input to WASM memory
        input_ptr = self.alloc_fn(self.store, len(input_json))
        self.memory.write(self.store, input_ptr, input_json)

        # Execute with timeout
        try:
            output_ptr = self.score_fn(self.store, input_ptr, len(input_json))
            output_len = self.get_output_len(self.store)

            # Read output from WASM memory
            output_bytes = self.memory.read(self.store, output_ptr, output_ptr + output_len)
            result = json.loads(output_bytes)

            return ScoreResult(
                score_value=result["score"],
                breakdown=result.get("breakdown"),
                status=result.get("status", "scored"),
                error=result.get("error"),
            )
        except Exception as e:
            return ScoreResult(score_value=0, status="failed", error=str(e))
```

### 16.3 WASM Module Management

#### Upload WASM module (admin)
`POST /api/admin/scoring/upload-wasm`

**Request:** multipart/form-data with `.wasm` file

**Server logic:**
1. Validate file is a valid WASM module (parse headers)
2. Compute SHA-256 hash for versioning
3. Store at `/data/scoring/<sha256>.wasm`
4. Update event config with scorer reference
5. Test-run with a sample input to verify it works
6. Return module info

**Response:**
```json
{
  "scorer_type": "wasm",
  "scorer_version": "sha256:a3b7c9d2...",
  "file_size_bytes": 245760,
  "validated": true,
  "test_result": {
    "score": 50.0,
    "status": "scored",
    "execution_time_ms": 12
  }
}
```

#### Get current scorer info
`GET /api/admin/scoring/info`

```json
{
  "scorer_type": "wasm",
  "scorer_version": "sha256:a3b7c9d2...",
  "uploaded_at": "2026-02-20T10:00:00Z",
  "memory_limit_mb": 64,
  "time_limit_ms": 5000
}
```

### 16.4 Scorer Version Tracking

Every score record includes `scorer_version`:
- For Python scorer: `"python-default-1.0"`
- For WASM scorer: `"wasm:sha256:a3b7c9d2..."`

This enables:
- Identifying which scorer version produced each score
- Triggering re-scores when the module changes
- Reproducible export (manifest includes scorer version)

### 16.5 WASM Safety Limits

| Limit | Default | Configurable |
|-------|---------|-------------|
| Execution time | 5000ms | `WASM_TIME_LIMIT_MS` |
| Memory | 64 MB | `WASM_MEMORY_LIMIT_MB` |
| Stack size | 1 MB | `WASM_STACK_SIZE_MB` |

If a WASM module exceeds limits:
- Execution is terminated
- Score status set to `failed`
- Error message: "Scoring module exceeded time/memory limit"

### 16.6 Client-Side WASM Preview (Optional)

Serve the WASM module to the browser for client-side preview scoring:

#### Download WASM for preview
`GET /api/scoring/preview-module`

- Returns the WASM file if client preview is enabled
- Returns `404` if preview is disabled
- **Client scores are NEVER used for the leaderboard**

#### Frontend integration

```typescript
// frontend/src/lib/wasm-preview.ts

export class WasmPreview {
  private instance: WebAssembly.Instance | null = null;

  async load(): Promise<boolean> {
    try {
      const response = await fetch('/api/scoring/preview-module');
      if (!response.ok) return false;

      const buffer = await response.arrayBuffer();
      const module = await WebAssembly.compile(buffer);
      this.instance = await WebAssembly.instantiate(module);
      return true;
    } catch {
      return false;
    }
  }

  preview(submissionData: object): PreviewResult | null {
    if (!this.instance) return null;
    // ... pass data to WASM, read result
    // Display with clear "PREVIEW — not official" label
  }
}
```

UI must clearly label preview scores:
```
Preview Score: 85.5 (unofficial — for reference only)
Official score will appear after server processing.
```

### 16.7 Batch Re-Score

When a new WASM module is uploaded:

`POST /api/admin/scoring/rescore-all`

```json
{
  "confirm": true,
  "reason": "Updated scoring module v2"
}
```

- Queues re-score tasks for all non-withdrawn submissions
- Uses the task queue (task 14)
- Tracks progress in admin UI
- Old scores are replaced, logged in audit

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/admin/scoring/upload-wasm` | Admin | Upload WASM scorer |
| GET | `/api/admin/scoring/info` | Admin | Current scorer info |
| POST | `/api/admin/scoring/rescore-all` | Admin | Re-score all submissions |
| GET | `/api/scoring/preview-module` | Public | Download WASM for preview |

---

## Acceptance Criteria

- [ ] WASM module uploaded by admin and validated
- [ ] Server-side WASM execution with time and memory limits
- [ ] Scorer version tracked on every score record
- [ ] Scores from WASM are deterministic (same input → same output)
- [ ] Client-side WASM preview loads and runs in browser
- [ ] Client preview scores clearly labeled as unofficial
- [ ] Batch re-score works via task queue
- [ ] Failed WASM execution produces clear error messages
- [ ] Export manifest includes scorer type, version, and hash

---

## Developer Notes

- `wasmtime` is the recommended Python WASM runtime (maintained by Bytecode Alliance)
- Install: `pip install wasmtime`
- WASM modules can be written in Rust, C, AssemblyScript, or any language targeting WASM
- Provide a template WASM scorer project (Rust) in the repo for event organizers
- Test with deliberately slow/large WASM to verify limits work
- The WASM interface uses JSON for simplicity — binary formats (MessagePack) could improve performance later
- Client-side WebGPU preview is mentioned in specs but out of scope for MVP-3 (future enhancement)
