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

## Adoption

`mlp_tuned.omni` is a **separate file / proposal**, not an edit to
`mlp.omni` on main. `mlp.omni` on main does not change in this test.
Adoption goes through the `learn` verdict (ADOPT / HOLD / REJECT) per
FOUNDATION.md — the tuner proposes, the Mind decides.

## Next steps

- `agent2.omni` (more parameters, deeper net).
- The structural proposer step: adding the third neuron (`ReLU(x0+x2+b2)`)
  via CEGIS, per PAPER.md §6.1 — the fix for the (9,0,9) ceiling.
- A ternary-native optimizer (first-principles revisit of the tuner).

## Reproduce

```sh
cd mode63
python3 tuner.py --seed 1 --max-evals 300        # full run (omnic)
python3 tuner.py --simulate --seed 1             # fast, simulation only
```

Environment: `OMNIC` (default `~/workspace/omnic-fix`), `OMNI_DIR`
(default `~/workspace/omni-fix-m3builtins`, must contain `pure/`).
