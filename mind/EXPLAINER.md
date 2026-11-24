# Omni-Mind v0.1 — Vertical Slice Explainer

The first working code in Omni-Mind: two memories, one trit-weighted edge,
and a bounded walk between them. This is the vertical slice from
FOUNDATION.md §9 — the smallest thing that proves the model can exist
inside the current pure pipeline.

## Files

- `memory.omni` — memory record and activation. A memory is a verified
  program (a function) identified by a small integer id. `mem_activate(id, ctx)`
  runs it and returns a packed `(value + 100) * 10 + (confidence + 1)`,
  where confidence is a trit (+1 = confident, 0 = uncertain, -1 = contradicts).
  `mem_strength(id)` returns the memory's strength trit.
- `graph.omni` — the memory graph. `edge_weight(from, to)` returns the
  edge's ternary weight (+1 = strong/support, 0 = weak/unknown, -1 =
  contradictory/inhibiting). `walk(start, fuel)` walks from a node for up
  to `fuel` steps, following +1 edges only, and returns the final node id.
  The walk is iterative (a `while` loop), not recursive, so it stays inside
  the 64-frame call-depth cap.
- `golden_walk.omni` — the golden. `main(start, fuel)` walks from `start`,
  activates the node the walk ends on, and returns its value.

## The slice

- Memory 0 ("greeting"): value 42, confidence +1 (trusted).
- Memory 1 ("farewell"): value 99, confidence +1 (trusted).
- Edge 0 -> 1: weight +1 (greeting triggers farewell, strong).
- Edge 1 -> 0: weight -1 (farewell contradicts greeting, do not follow).
- All other pairs: weight 0 (no edge / unknown).

## Running it

From the omni repo root (the `pure/` tree must be present), with the
mind/ directory copied in:

```
omnic run mind/golden_walk.omni <start> <fuel>
```

## Expected outputs (verified on Linux, main @ 6e8cfa0d, both `run` and `--rust`)

| Call | Result | Why |
|------|--------|-----|
| `main(0, 10)` | 99 | Walk 0 -> 1 via the +1 edge, activate 1 |
| `main(1, 10)` | 99 | No +1 edge from 1, stay at 1, activate 1 |
| `main(0, 0)`  | 42 | Fuel 0, stay at 0, activate 0 |
| `main(0, 1)`  | 99 | One step 0 -> 1, activate 1 |
| `main(2, 10)` | 0  | Unknown node 2, no edge, activate -> 0 (confidence 0) |

## Notes

- **Includes are file-relative, not repo-root-relative.** `golden_walk.omni`
  includes `memory.omni` and `graph.omni` (bare names), not
  `mind/memory.omni` — the resolver prepends the including file's directory,
  so `mind/memory.omni` doubles to `mind/mind/memory.omni` and fails.
  The `std/` includes still use the `std/` prefix.
- **The 3-arg `run` limit shaped the API.** Every function takes at most
  two arguments (`mem_activate` takes id + ctx, `walk` takes start + fuel,
  `edge_weight` takes from + to). No function needs a fourth argument, so
  the known `run` arg bug (4th+ args arrive as 0) does not bite here.
- **Context is reserved, not used.** `mem_activate` takes a `ctx` argument
  for future context-sensitive activation; the memories in this slice ignore
  it (folded in as `+ ctx * 0`).
- **No persistence yet.** This slice is in-memory only. `kv_put`/`db_get`
  do not work via `run` (M3_CODE_9, the intrinsics follow-up), so memories
  do not survive a single process. Persistence is the next phase.
- **No pack5.** The slice does not use `pack5_bytes`/`pack5_tdot`
  (also M3_CODE_9 via `run`). Those are for Mode 6.3, later.
