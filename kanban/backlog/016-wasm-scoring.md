---
id: "016"
title: "WASM Scoring Module"
type: feature
status: backlog
estimate: "5d"
size: XL
depends_on: ["008"]
blocks: []
spec: "specs/specs/16-wasm-scoring.md"
tags: [wasm, scoring, frontend]
---

# WASM Scoring Module

Client-side scoring preview using WebAssembly — participants see a score estimate before submitting. Official scores remain server-side.

## Tasks

- [ ] Scoring logic compiled to WASM (Rust or AssemblyScript)
- [ ] WASM module served as static asset
- [ ] Frontend integration: load WASM module, call scoring function on submission preview
- [ ] Score is preview-only — NOT sent to leaderboard
- [ ] Server validates that official scores match WASM output within tolerance
- [ ] `GET /api/scoring/module` — return WASM binary + version hash
- [ ] Scoring criteria schema exposed via API for WASM module configuration

## Security Model

```
Client WASM → preview score (UX only, untrusted)
Server logic → official score (authoritative, in DB)
```

Client score MUST NOT be accepted by the server. Leaderboard reads only from DB `scores` table.

## Notes

- Requires Step 10 (frontend) to be partially complete
- WASM build step added to Dockerfile Stage 1 (alongside Node.js)
- Version hash ensures client WASM matches server scoring criteria
