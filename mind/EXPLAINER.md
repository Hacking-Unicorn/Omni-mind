# Omni-Mind v0.1 — Vertical Slice Explainer

The first working code in Omni-Mind: two memories, one trit-weighted edge,
a bounded walk between them, cue-based activation with a confidence trit,
a ternary learn verdict (ADOPT / REJECT / HOLD), a distill stub, and a
minimal decision ledger. This is the v0.1 foundation from FOUNDATION.md §3
and §9 — the smallest thing that proves the model can exist inside the
current pure pipeline.

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
- `activate.omni` — cue-based activation. `activate(cue)` finds the memory
  matching the cue and runs it, returning the same packed result as
  `mem_activate`. A cue with no matching memory returns confidence 0
  (unknown) — a first-class outcome, not an error. The caller must gather
  more information instead of acting on it.
- `learn.omni` — ternary judgment. `learn(candidate, evidence)` returns a
  verdict trit: +1 ADOPT (evidence >= 2), -1 REJECT (evidence <= -1),
  0 HOLD (evidence 0 or 1). HOLD is a legitimate state: a held candidate
  is kept for re-judgment when more evidence arrives, never forced into
  an ADOPT or a REJECT.
- `distill.omni` — consolidation stub. `distill(id)` returns the memory
  unchanged (identity). Full distillation (anti-unification + MDL) is a
  later phase.
- `ledger.omni` — decision ledger (minimal). The ledger state is a packed
  i64: `count * 10 + (last + 1)`. `ledger_append(state, decision)` records
  a verdict trit and returns the new state; `ledger_count(state)` returns
  how many decisions were recorded; `ledger_last(state)` returns the most
  recent verdict. The full ledger (content-addressed, hash-chained,
  persistent) comes later, once storage works.
- `golden_walk.omni` — golden for the walk. `main(start, fuel)` walks from
  `start`, activates the node it lands on, and returns its value.
- `golden_activate.omni` — golden for activation + confidence.
  `main(cue)` returns the packed activation result so the confidence is
  visible.
- `golden_learn.omni` — golden for learn + HOLD. `main(candidate, evidence)`
  returns the verdict trit.
- `golden_ledger.omni` — golden for distill + ledger. `main(id, decision)`
  distills the memory and records the decision, returning
  `distilled_id * 100 + ledger_state`.

## The slice

- Memory 0 ("greeting"): value 42, confidence +1 (trusted).
- Memory 1 ("farewell"): value 99, confidence +1 (trusted).
- Edge 0 -> 1: weight +1 (greeting triggers farewell, strong).
- Edge 1 -> 0: weight -1 (farewell contradicts greeting, do not follow).
- All other pairs: weight 0 (no edge / unknown).
- Cue 1 (morning) -> memory 0. Cue 2 (evening) -> memory 1. Other cues -> none.

## Running it

From the omni repo root (the `pure/` tree must be present), with the
mind/ directory copied in:

```
omnic run mind/golden_walk.omni <start> <fuel>
omnic run mind/golden_activate.omni <cue>
omnic run mind/golden_learn.omni <candidate> <evidence>
omnic run mind/golden_ledger.omni <id> <decision>
```

## Expected outputs (verified on Linux, main @ 6e8cfa0d, both `run` and `--rust`)

### golden_walk (5/5)

| Call | Result | Why |
|------|--------|-----|
| `main(0, 10)` | 99 | Walk 0 -> 1 via the +1 edge, activate 1 |
| `main(1, 10)` | 99 | No +1 edge from 1, stay at 1, activate 1 |
| `main(0, 0)`  | 42 | Fuel 0, stay at 0, activate 0 |
| `main(0, 1)`  | 99 | One step 0 -> 1, activate 1 |
| `main(2, 10)` | 0  | Unknown node 2, no edge, activate -> 0 (confidence 0) |

### golden_activate (4/4)

| Call | Result | Why |
|------|--------|-----|
| `main(1)` | 1422 | Memory 0, value 42, conf +1 |
| `main(2)` | 1992 | Memory 1, value 99, conf +1 |
| `main(3)` | 1001 | No memory, value 0, conf 0 (gather info, don't act) |
| `main(0)` | 1001 | No memory, value 0, conf 0 |

### golden_learn (6/6)

| Call | Result | Why |
|------|--------|-----|
| `main(50, 3)`  | 1  | Strong evidence, ADOPT |
| `main(50, 2)`  | 1  | Evidence 2, ADOPT |
| `main(50, 1)`  | 0  | Weak evidence, HOLD |
| `main(50, 0)`  | 0  | No evidence, HOLD |
| `main(50, -1)` | -1 | Contradictory, REJECT |
| `main(50, -2)` | -1 | REJECT |

### golden_ledger (3/3)

| Call | Result | Why |
|------|--------|-----|
| `main(0, 1)`  | 12  | distill 0 -> 0, ledger +1 -> state 12 |
| `main(1, -1)` | 110 | distill 1 -> 1, ledger -1 -> state 10 |
| `main(2, 0)`  | 211 | distill 2 -> 2, ledger 0 -> state 11 |

Total: 18/18 across the four goldens, plus `--rust` cross-checks agreeing
on sampled cases from each golden.

## Notes

- **Includes are file-relative, not repo-root-relative.** Goldens include
  bare names (`memory.omni`, `graph.omni`, `activate.omni`, ...), not
  `mind/memory.omni` — the resolver prepends the including file's directory,
  so `mind/memory.omni` doubles to `mind/mind/memory.omni` and fails.
  The `std/` includes still use the `std/` prefix. Module files do not
  include std/ themselves; the golden includes std/ first, then the modules.
- **The 3-arg `run` limit shaped the API.** Every function takes at most
  two arguments. No function needs a fourth argument, so the known `run`
  arg bug (4th+ args arrive as 0) does not bite here.
- **Context is reserved, not used.** `mem_activate` takes a `ctx` argument
  for future context-sensitive activation; the memories in this slice ignore
  it (folded in as `+ ctx * 0`). Likewise `learn` folds the candidate in
  as `+ candidate * 0` because v0.1 does not store adopted candidates.
- **No persistence yet.** This slice is in-memory only. `kv_put`/`db_get`
  do not work via `run` (M3_CODE_9, the intrinsics follow-up), so memories
  and ledger entries do not survive a single process. Persistence is the
  next phase. That is also why `learn` does not store adopted candidates
  and the ledger resets each run.
- **No pack5.** The slice does not use `pack5_bytes`/`pack5_tdot`
  (also M3_CODE_9 via `run`). Those are for Mode 6.3, later.
- **The Omni Mind code is Pure Omni.** The `.omni` files contain no Rust.
  The `--rust` runs used for verification are a differential cross-check
  (the Rust reference implementation as the oracle), not a dependency:
  the Pure VM runs the Mind code on its own.
