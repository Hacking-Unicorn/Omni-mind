# Mode 6.3 first test — tunable parameters + a working tuner

The first Mode 6.3 result that is a **measurement, not a design**.
PAPER.md §10 named the gap: the topologies existed (`programs/mlp.omni`,
`programs/perceptron.omni`, `programs/agent2.omni`) but "the numeric
parameters are hardcoded literals for now, and there is no objective yet —
so the 'search space' is not actually searchable until the parameters are
made variable and an objective is defined." This directory closes that gap
for `mlp.omni`.

## Testbed and objective

**Program:** `programs/mlp.omni` — three sensors, two ReLU hidden neurons,
a sign output. Parameter vector `theta = (b0, b1, t)`: the two hidden
biases and the output threshold, currently `(-8, -8, -5)`. Search ranges:
`b0, b1` in `[-16, 0]`, `t` in `[-12, 0]`.

**Objective:** an 18-case labelled dataset (see `tuner.py`). Ground truth,
fixed before tuning: **fault (+1) iff at least two of the three sensors
are >= 8; otherwise healthy (-1).** Fitness is lexicographic, per the
monograph (§3): (1) fewest misclassifications, then (2) largest total
margin (sum of |score| over correctly classified cases).

**Answer key** (recomputed independently by exhaustive grid search over
`b0, b1, t` in `[-20, 5]`, 17,576 points, simulated from the program's
arithmetic — not guessed):
- Baseline `(-8, -8, -5)`: **3 errors** — (9,0,9), (7,7,7), (6,6,6).
- Global optimum: **1 error.** Exactly 6 points reach it, all missing
  only (9,0,9): `(-14,-16,-1)`, `(-14,-15,-1)`, `(-14,-14,-1)`,
  `(-13,-15,-2)`, `(-13,-14,-2)`, `(-12,-14,-3)`.
- **0 errors is impossible for this topology.** The network pairs adjacent
  sensors only (`x0+x1`, `x1+x2`); it has no `x0+x2` detector, so (9,0,9)
  — two high sensors with a low middle one — cannot be separated from the
  healthy cases. The fix for the last error is a third hidden neuron
  (`ReLU(x0+x2+b2)`), i.e. a proposer-loop structural change, not more
  tuning.

## The tuner (`tuner.py`)

A host-side Python harness (no Omni change). For each candidate theta it
writes a variant file with the three literals substituted, runs it through
`omnic run` once per dataset case (18 runs), and scores it. The variant is
a normal `.omni` file, so the verifier still checks every candidate — a
candidate that fails verification scores as invalid, not as 0. `main`
takes exactly the 3 sensor inputs, so the 3-arg `run` limit does not bite;
the parameters are baked into the file, not passed as args.

**Method:** warm-start with 16 quasi-random samples (Latin Hypercube),
then **(1+1)-CMA-ES with Margin** on the integer vector. The mean stays
continuous; the candidate is discretized (rounded, clipped to bounds) for
evaluation. The covariance adapts by the rank-one update; the step size
adapts by the 1/5 success rule. The Margin forces the per-dimension
probability of the discretized sample differing from the mean's
discretization to be at least alpha=0.1, by scaling the covariance
diagonal — this keeps the search from locking onto a suboptimal integer
when the variance shrinks below 0.5. (This is a per-dimension variance
floor derived from the margin probability, not Hamano's exact mean-shift
correction; the code documents the exact variant.)

**Restarts:** (1+1)-CMA-ES is a local search. If the best error count has
not improved for 50 evals, the climb restarts from the next-best warm
point (then a fresh uniform point), keeping the global best. Restarts are
standard CMA-ES practice (IPOP).

**Sanity check first:** `perceptron.omni` as a 1-D test — its weight `w`
is already an input, so the tuner searches `w` directly for a 1-D labelled
set (label = sign(x)). Any `w > 0` is optimal.

## Results (verified via `omnic run`, Linux)

Run: `python3 tuner.py --seed 1 --max-evals 300` (omnic at
`~/workspace/omnic-fix`, checkout `~/workspace/omni-fix-m3builtins`).

- **Perceptron 1-D sanity check: PASS.** Found `w=85`, 0 errors, in 9
  evals (warm start already had a `w > 0`).
- **MLP 3-D tuning: PASS.** Baseline `(-8,-8,-5)` scores (3 errors,
  margin 103) via omnic. Warm start best was `(-12,-14,-2)` (2 errors).
  The CMA-ES climbed to **`(-14, -16, -1)` — 1 error, margin 40 — in 29
  evals** (16 warm + 13 CMA-ES), 0 restarts. This is one of the 6 global
  optima.
- **The tuned variant** (`mlp_tuned.omni`, a proposal — see below)
  verified independently via omnic on all 18 cases: **17/18 correct.**
  The only miss is **(9,0,9)**, the topology ceiling, exactly as the
  answer key predicts. All 5 documented classifications are unchanged;
  the packed goldens change (recorded, not judged against the old numbers):
  - (10,10,10) -> 459 (was 469), y=+1
  - (0,0,0) -> 49 (was 45), y=-1
  - (10,0,0) -> 49 (was 47), y=-1
  - (5,5,5) -> 49 (was 49), y=-1
  - (8,8,8) -> 451 (was 461), y=+1

## What this proves, and what it does not

- **Proves:** variable parameters + a defined objective + a working
  derivative-free tuner inside a verified shape — the exact gap PAPER.md
  §10 names. The search climbs (warm start 2 errors -> CMA-ES 1 error),
  it does not guess (6/17,576 grid points reach 1 error; random search
  would not be expected to find one).
- **Does not prove:** the proposer loop (still design-only), in-Omni
  tuning (the tuner here is host-side), or scale (3 parameters, 18 cases).

## Limitations (honest)

- **Seed sensitivity.** The (1+1) local search is not robust across
  seeds on this landscape. In simulation: 3/5 seeds reach a 1-error theta
  within 300 evals; 5/8 within 1000 evals. The failures converge to
  2-error points (notably `(-1,-12,-12)`, margin 106) and cannot make the
  final step — only 22 of the 113 2-error points are adjacent to a
  1-error point, and the margin tiebreaker pulls climbs toward
  high-margin boundary points rather than toward the 1-error cluster.
  The omnic run reported above used seed 1, which passes in 29 evals.
  This is a real limitation of the (1+1) local search here, and a topic
  for the first-principles revisit (a ternary-native optimizer). It does
  not change the result: a 1-error theta was found and verified.
- **The margin tiebreaker can mislead.** Total margin is higher at some
  2-error boundary points (margin ~106) than at the 1-error optima
  (margin 40-60), because a confidently-wrong classifier can still have
  large |score| on its correct cases. Errors dominate lexicographically,
  so this does not corrupt the ranking — but it does pull the local search
  away from the low-error region. A margin that rewards being confidently
  right without rewarding confidently-wrong extremes is an open question.
- **The tuner is host-side.** In-Omni tuning (the tuner itself as an Omni
  program) is a later step, not this test.

## Phase 2 follow-up — 3-neuron topology (`mlp3_tuned.omni`) + tuner hardening

Phase 2 proved the tuner could hit the 2-neuron global optimum (`1` error),
but `1` error was a topology ceiling (`(9,0,9)` unseparable) and the tuner was
seed-sensitive (`3/5` in 300 evals, `5/8` in 1000). This follow-up fixes both:
adds the missing third hidden neuron (`h2 = ReLU(x0 + x2 + b2)`) in a new
proposal file `mlp3_tuned.omni` (leaving `programs/mlp.omni` and
`mode63/mlp_tuned.omni` untouched), and hardens `tuner.py` so it reaches `0`
errors reliably across seeds.

### 4-D topology & exhaustive answer key

- **Topology:** `h0 = ReLU(x0+x1+b0)`, `h1 = ReLU(x1+x2+b1)`,
  `h2 = ReLU(x0+x2+b2)`, `score = h0 + h1 + h2 + t`, `y = sign(score)`.
- **Parameter vector:** `theta = (b0, b1, b2, t)` with `b0, b1, b2` in
  `[-16, 0]` and `t` in `[-12, 0]` (`63,869` points in the search box).
- **Exhaustive answer key** (vectorized over `[-20, 5]^4`, `456,976` points,
  simulated from the exact program arithmetic; cross-checked `18/18` against
  `omnic run` before tuning):
  - Baseline `(-8, -8, -8, -5)`: **3 errors** (uncapped margin `143`,
    capped-2 margin `27`).
  - **Global optimum: 0 errors.** Exactly **14** points reach `0` errors in
    `[-20, 5]^4`, and all 14 lie inside `[-16, 0]^3 x [-12, 0]` (`0.022%` of
    the search box, 1 in 4,562 points):
    - `(-12, -14, -14, -3)` (uncapped margin `74`, capped-2 margin `32`)
    - `(-13, -14, -14, -2)` (uncapped `70`, capped-2 `34`)
    - `(-14, -14, -14, -1)` (uncapped `66`, capped-2 `27`)
    - `(-13, -14, -15, -2)` (uncapped `66`, capped-2 `33`)
    - `(-13, -15, -14, -2)` (uncapped `65`, capped-2 `33`)
    - `(-14, -14, -15, -1)` (uncapped `62`, capped-2 `27`)
    - `(-14, -15, -14, -1)` (uncapped `61`, capped-2 `27`)
    - `(-13, -15, -15, -2)` (uncapped `61`, capped-2 `32`)
    - `(-14, -14, -16, -1)` (uncapped `58`, capped-2 `26`)
    - `(-14, -15, -15, -1)` (uncapped `57`, capped-2 `26`)
    - `(-14, -16, -14, -1)` (uncapped `56`, capped-2 `26`)
    - `(-14, -15, -16, -1)` (uncapped `53`, capped-2 `25`)
    - `(-14, -16, -15, -1)` (uncapped `52`, capped-2 `25`)
    - `(-14, -16, -16, -1)` (uncapped `48`, capped-2 `24`)
  - **Adjacency:** in `[-20, 5]^4`, `51 / 392` (`13.0%`) 1-error points are
    L1-adjacent to a 0-error point (`789 / 9,270` = `8.5%` 2-error adjacent to
    1-error). Inside the search box `[-16, 0]^3 x [-12, 0]`, `45 / 312`
    (`14.4%`) 1-error points are L1-adjacent to a 0-error point (`537 / 3,922`
    = `13.7%` 2-error adjacent to 1-error).
  - **Why uncapped margin failed in 4-D:** at 0-error optima, total uncapped
    margin is `48..74` (median `61`), whereas 1-error points reach `127` and
    2-error points reach `155`. The top-20 1-error points by uncapped margin
    sit at mean L1 distance **`21.75`** from the 0-error cluster (`0/20`
    L1-adjacent), pulling every climb away from the 0-error region.

### Tuner hardening changes (`tuner.py`)

The method stays **(1+1)-CMA-ES with Margin**, with the dataset, ground-truth
rule, and lexicographic `(errors, -margin)` ordering unchanged:

1. **Warm-start `16 -> 32`** Latin Hypercube points to cover the 4-D box.
2. **Independent local restarts (`restart_after = 30`):**
   - Margin improvements still do **not** reset the stagnation counter — only
     a lower error count does.
   - Each restart gets its own derived RNG sub-seed (fixing a Phase 2 bug
     where every restart passed the same `seed`, replaying identical Gaussian
     steps) and its own local `parent_fit` (so restarts from higher-error warm
     points can actually climb instead of being compared against the global
     best), while global `best_fit` / `best_theta` are always preserved.
   - Restarts alternate between `best_theta` (fresh covariance, alternating
     `sigma0` and `1.5*sigma0`) and the next-best unused warm / uniform point.
3. **Per-case margin cap (`margin_cap = 2`):**
   - Each correctly classified case contributes `min(|score|, 2)` to the
     tiebreaker (`--margin-cap 0` disables the cap).
   - **Why `cap = 2` (from the data, not tuned to seed 1):** across the 14
     zero-error optima, per-case `|score|` has median `1..3` (overall median
     `2`), while easy cases `(10,10,10)` reach `13..17` and high-margin
     1-error traps reach `|score| > 20`. Capping at `2` drops the top-20
     1-error points' mean L1 distance to the 0-error cluster from `21.75`
     (`cap=None`) → `8.75` (`cap=4`) → `5.30` (`cap=3`) → **`4.20` (`cap=2`,
     `2/20` L1-adjacent)**, while still preferring non-borderline (`|score| >= 2`)
     classifications over `|score| = 1` (unlike `cap=1`, which degenerates to
     constant `18 - errors`).
4. **Hamano's `1/N` margin probability (`alpha = 1 / max(4, n)` = `0.25` in
   4-D):** with the old `alpha = 0.1`, `(1 - 0.1)^4 = 65.6%` of steps at low
   `sigma` were no-ops rounding back to `round(m)`.

### Measured reliability (10-seed simulation + 5-seed `omnic`, `--max-evals 1000`)

Ablation on 4-D `mlp3` in simulation (`--max-evals 1000`):

| Configuration | Seeds `1..10` (0 err) | Holdout `11..20` | Combined `1..30` |
|---|---:|---:|---:|
| Old tuner defaults (`w=16, r=50, cap=None`) | `0/10` | `0/10` | — |
| Hardened restarts + `w=32` + `alpha=0.25`, **uncapped (`--margin-cap 0`)** | `0/10` | `1/10` | `2/30` |
| Hardened restarts + `w=32` + `alpha=0.25`, **`--margin-cap 3`** | `6/10` | — | `13/30` |
| **Hardened tuner (`w=32, r=30, alpha=0.25, --margin-cap 2`)** | **`8/10`** | **`9/10`** | **`25/30` (83.3%)** |

Per-seed simulation (`seeds 1..10`, `--margin-cap 2`, `--max-evals 1000`):
- **8/10 PASS** (median `390` evals): seed 1 (`561`, `(-14,-14,-16,-1)`),
  seed 2 (`54`, `(-12,-14,-14,-3)`), seed 3 (`298`, `(-12,-14,-14,-3)`),
  seed 4 (`493`, `(-13,-14,-14,-2)`), seed 5 (`97`, `(-12,-14,-14,-3)`),
  seed 6 (`421`, `(-13,-15,-15,-2)`), seed 7 (`845`, `(-14,-14,-14,-1)`),
  seed 8 (FAIL, 1 err at `(-5,-12,-12,-8)`), seed 9 (FAIL, 1 err at
  `(-3,-12,-12,-10)`), seed 10 (`359`, `(-13,-14,-15,-2)`).
- Comparison against old 2-neuron baseline: `5/8` (`62.5%`) reached the old
  1-error ceiling in 1000 evals; on the harder 26x-larger 4-D space, the
  hardened tuner reaches **0 errors** on `8/10` (`80%`, `25/30` = `83.3%`).

Live `omnic` runs on Linux (WSL2, `OMNIC=$HOME/workspace/omnic-main` built
from `omni` `main @ d5789de`, `OMNI_DIR=$HOME/workspace/omni-main`):
- **Perceptron 1-D sanity check (`--seed 1`): PASS** (`w=84`, `0` errors in
  `8` evals).
- **MLP3 4-D via `omnic` (`seeds 1..5`, `--max-evals 1000`): 5/5 PASS** (all
  reach `0` errors, matching simulation eval-for-eval):
  - Seed 1: `(-14, -14, -16, -1)` — `0` errors, capped margin `26` in `561` evals (`519` unique, `12` restarts)
  - Seed 2: `(-12, -14, -14, -3)` — `0` errors, capped margin `32` in `54` evals (`54` unique, `0` restarts)
  - Seed 3: `(-12, -14, -14, -3)` — `0` errors, capped margin `32` in `298` evals (`266` unique, `7` restarts)
  - Seed 4: `(-13, -14, -14, -2)` — `0` errors, capped margin `34` in `493` evals (`435` unique, `13` restarts)
  - Seed 5: `(-12, -14, -14, -3)` — `0` errors, capped margin `32` in `97` evals (`95` unique, `1` restart)

### Proposal file (`mode63/mlp3_tuned.omni`) & 3-way verification

Recorded proposal: `mode63/mlp3_tuned.omni` with **`theta = (-12, -14, -14, -3)`**
(found by 3 of 5 live `omnic` seeds and highest uncapped margin `74` among all
14 zero-error optima). Verified across all 18 cases **three ways** (`omnic run`,
`omnic run-wasm`, `omnic run --rust`) with **18/18 exact agreement and 0 errors**.

Documented 5 goldens (all 5 classifications unchanged):
- `(10, 10, 10)` -> `467` (`y=+1`, `score=+17`; was `459` on 2-neuron tuned, `469` on untuned) — `run=Int(467)`, `run-wasm=467`, `--rust=Int(467)`
- `(0, 0, 0)` -> `47` (`y=-1`, `score=-3`; was `49` / `45`) — `run=Int(47)`, `run-wasm=47`, `--rust=Int(47)`
- `(10, 0, 0)` -> `47` (`y=-1`, `score=-3`; was `49` / `47`) — `run=Int(47)`, `run-wasm=47`, `--rust=Int(47)`
- `(5, 5, 5)` -> `47` (`y=-1`, `score=-3`; was `49` / `49`) — `run=Int(47)`, `run-wasm=47`, `--rust=Int(47)`
- `(8, 8, 8)` -> `455` (`y=+1`, `score=+5`; was `451` / `461`) — `run=Int(455)`, `run-wasm=455`, `--rust=Int(455)`

### Residual limitations (honest)

- **Not 10/10 across all seeds:** `2/10` seeds (`8` and `9` in `1..10`, `5/30`
  overall) still stall at 1-error points (`(-5,-12,-12,-8)` and
  `(-3,-12,-12,-10)`, capped-2 margin `33`) within `1000` evals because only
  `45/312` (`14.4%`) of 1-error points in the box are L1-adjacent to the
  14-point 0-error island.
- **Host-side tuner:** `tuner.py` is still Python on the host; in-Omni tuning
  and a ternary-native optimizer remain Phase 7 work.
- **Small benchmark:** 4 integer parameters, 18 cases; scaling to deeper nets
  (`agent2.omni`) is future work.

## Adoption

`mlp_tuned.omni` (2-neuron Phase 2 history) and `mlp3_tuned.omni` (3-neuron
0-error proposal) are **separate proposal files**, not edits to `mlp.omni` on
main. `programs/mlp.omni` and `mode63/mlp_tuned.omni` remain untouched.
Adoption goes through the `learn` verdict (ADOPT / HOLD / REJECT) per
FOUNDATION.md — the tuner proposes, the Mind decides.

## Next steps

- Phase 3 — `distill` for real (Stitch anti-unification + ΔMDL / soundness admission gate).
- `agent2.omni` (more parameters, deeper net).
- A ternary-native optimizer (Phase 7 first-principles revisit of the tuner).

## Reproduce

```sh
cd mode63
export OMNIC=$HOME/workspace/omnic-main
export OMNI_DIR=$HOME/workspace/omni-main
python3 tuner.py --seed 1 --max-evals 1000        # full run (omnic)
python3 tuner.py --simulate --seed 1              # fast, simulation only
python3 tuner.py --simulate --seed 1 --margin-cap 0  # uncapped ablation
```

Environment: `OMNIC` (default `$HOME/workspace/omnic-main`), `OMNI_DIR`
(default `$HOME/workspace/omni-main`, must contain `pure/`).
