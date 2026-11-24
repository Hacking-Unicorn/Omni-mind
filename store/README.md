# Omni-Mind store (Phase 1 prototype)

The v0.1 foundation (`mind/`) is in-memory only: `kv_put` / `db_get` do not
work via `run` (M3_CODE_9), so memories do not survive a single process.
This store is the persistence prototype — Grok's suggested next step, and
the path rated high-confidence: **one `.omni` file per memory, a link list
for the edges, and a script that runs each memory through `omnic run` and
reads back the answer.** No compiler changes, no intrinsics fix.

## Layout

```
store/
  README.md            — this file
  run_store.sh         — the runner (bash)
  links.txt            — one edge per line: "from to weight"
  memories/
    mem_0.omni         — memory 0 ("greeting"): value 42, conf +1 -> 1422
    mem_1.omni         — memory 1 ("farewell"): value 99, conf +1 -> 1992
    mem_3.omni         — memory 3 ("persistence proof"): value 7, conf +1 -> 1072
```

Each `mem_<id>.omni` is a standalone program. Its `main(ctx)` returns the
packed result `(value + 100) * 10 + (confidence + 1)` — the same packing
`mem_activate` returns in `mind/memory.omni`. The runner unpacks the value
as `(packed / 10) - 100`.

`links.txt` holds the v0.1 edges from `mind/graph.omni`: `0 1 +1` and
`1 0 -1`. All other pairs are weight 0 (no edge / unknown).

## Usage

```sh
./run_store.sh <start> <fuel>
```

Walks from `<start>` with `<fuel>` steps, following +1 edges only
(exactly like `walk` in `mind/graph.omni`), then activates the final
node and prints its value. Unknown node (no mem file) -> 0.

If the executable bit is lost on checkout, run `chmod +x run_store.sh`
first, or invoke it as `bash run_store.sh <start> <fuel>`.

```sh
./run_store.sh 0 10   # 99  (walk 0 -> 1, activate 1)
./run_store.sh 1 10   # 99  (no +1 edge from 1, stay, activate 1)
./run_store.sh 0 0    # 42  (fuel 0, stay at 0, activate 0)
./run_store.sh 0 1    # 99  (one step 0 -> 1, activate 1)
./run_store.sh 2 10   # 0   (unknown node 2, no mem file)
./run_store.sh 3 0    # 7   (persistence proof: mem_3, direct)
```

The first five are the v0.1 `golden_walk` cases, reproduced through the
store. The sixth is the persistence proof: `mem_3` exists only as a file
in this store — it was created after v0.1 and is not in `mind/` — and a
fresh process activates it by running the file.

## Configuration

- `OMNIC`: path to the `omnic` binary. Default: `omnic` on PATH, else
  `$HOME/workspace/omnic-fix`.
- `OMNI_DIR`: Omni checkout containing a `pure/` tree (`omnic run` must
  be invoked from a directory containing `pure/`). Default:
  `$HOME/workspace/omni-fix-m3builtins`.

## Constraints

- **Default `run` path only, NOT `--rust`.** Each mem file is
  single-function, and `run --rust` fails a memory-budget check on any
  single-function file (Grok's third bug). The `--rust` differential
  cross-check is unavailable for the store until that bug is fixed.
- **At most 1 arg to `main`.** The `run` arg bug (args past the third
  arrive as 0) never bites.
- **No `kv_put` / `db_get`, no pack5.** The store is files + a script.
  The intrinsics route stays a separate track.
- **The walk loop lives in the shell**, so the 64-frame call-depth cap
  is irrelevant.

## Regression tests

The v0.1 `golden_walk` cases (above) are the regression: they must keep
passing through the runner. Grok's two hands-on test programs (a
preference memory and a one-hop weighted graph walk) were not in the repo
as files, so the golden_walk cases — which cover the same behavior
(activating a preference memory, and a one-hop +1 walk) — are the
regression in their place.

## Out of scope

The ledger as a persistent log, `distill` beyond the identity stub,
Mode 6.3, pack5, and any change to core Omni or to the v0.1 `mind/`
files. This prototype adds `store/` only.
