#!/usr/bin/env python3
"""Mode 6.3 first test — (1+1)-CMA-ES with Margin tuner (host-side harness).

Tuning a Pure Omni program's integer parameters by derivative-free search.
The tuner is host-side (Python); the program under test is Pure Omni and
every candidate is verified by running it through `omnic run`. No Omni
change is needed to run this test.

Method (per PAPER.md SS6.3 / FOUNDATION.md SS10, from the Mode 6.3
monograph): warm-start with 15-20 quasi-random samples (Latin Hypercube),
then (1+1)-CMA-ES with Margin on the integer parameter vector, with
restarts on stagnation (see run_test: the local search can be pulled into
a high-margin basin far from the low-error region, so a climb that has
not improved the error count for 50 evals restarts from a fresh point).

  (1+1)-CMA-ES: one parent, one offspring per iteration. The offspring is
  sampled from N(m, sigma^2 * C); the covariance C adapts by the rank-one
  update from the evolution path (the CMA-ES part); the step size sigma
  adapts by the 1/5 success rule. The mean stays continuous; the candidate
  is discretized (rounded to the nearest integer, clipped to bounds) for
  evaluation.

  Margin: after each update, for each dimension, the probability that a
  sample rounds to a different integer than round(m_i) is forced to be
  at least alpha. The marginal is N(m_i, s_i^2) with s_i = sigma*sqrt(C_ii);
  the distance from m_i to the nearest cell boundary is d_i = 0.5 -
  |m_i - round(m_i)|; the margin requires s_i >= d_i / z_alpha where
  z_alpha = Phi^{-1}(1 - alpha/2). This is enforced by scaling C_ii up.
  This is the margin idea (it keeps the search from locking onto a
  suboptimal integer when the variance shrinks below 0.5). It is not
  Hamano's exact mean-shift correction; it is a per-dimension variance
  floor derived from the same probability. Documented here so the claim
  is precise.

Fitness is lexicographic, per the monograph (SS3): (1) fewest
misclassifications, then (2) largest total margin (sum of |score| over
correctly classified cases). Lower is better; a candidate that fails
verification scores as invalid (errors = inf), never as 0.

Usage:
  python3 tuner.py [--simulate] [--seed N] [--max-evals N] [--only NAME]

  --simulate   score candidates with the Python simulation instead of
               omnic (fast; use to test the tuner logic, not the result).
  --seed N     RNG seed (default 1).
  --max-evals N  evaluation budget for the mlp test (default 300).
  --only NAME  run only 'perceptron' or 'mlp' (default: both).

Environment (for the omnic path):
  OMNIC     path to the omnic binary (default: omnic on PATH, else
            $HOME/workspace/omnic-fix).
  OMNI_DIR  Omni checkout containing a pure/ tree; `omnic run` must be
            invoked from a directory containing pure/ (default:
            $HOME/workspace/omni-fix-m3builtins).

The mlp testbed and dataset are from ~/workspace/omni-mode63-first-test.md.
The answer key (recomputed independently in this repo's history):
  baseline (-8,-8,-5): 3 errors — (9,0,9), (7,7,7), (6,6,6).
  global optimum: 1 error; exactly 6 points reach it, all missing only
  (9,0,9). 0 errors is impossible for this topology (no x0+x2 detector).
"""

import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent  # ~/workspace/omni-mind
MLP_TEMPLATE = REPO / "programs" / "mlp.omni"
PERCEPTRON_FILE = REPO / "programs" / "perceptron.omni"

OMNIC = os.environ.get("OMNIC") or shutil.which("omnic") or str(
    Path.home() / "workspace" / "omnic-fix"
)
OMNI_DIR = os.environ.get("OMNI_DIR") or str(
    Path.home() / "workspace" / "omni-fix-m3builtins"
)

# The 18-case labelled dataset. Ground truth, fixed before tuning:
# fault (+1) iff at least two of the three sensors are >= 8.
DATASET = [
    ((10, 10, 10), 1), ((0, 0, 0), -1), ((10, 0, 0), -1), ((0, 10, 0), -1),
    ((0, 0, 10), -1), ((5, 5, 5), -1), ((8, 8, 8), 1), ((9, 9, 0), 1),
    ((9, 0, 9), 1), ((0, 9, 9), 1), ((8, 8, 0), 1), ((7, 7, 7), -1),
    ((10, 10, 0), 1), ((6, 6, 6), -1), ((-10, -10, -10), -1),
    ((10, 9, 9), 1), ((9, 10, 0), 1), ((0, 9, 10), 1),
]

# The 5 documented mlp goldens (behaviour snapshots of the untuned program).
GOLDENS = [(10, 10, 10), (0, 0, 0), (10, 0, 0), (5, 5, 5), (8, 8, 8)]

# Perceptron 1-D sanity dataset: label = sign(x). Any w > 0 is optimal.
PERCEPTRON_DATASET = [(-10, -1), (-5, -1), (-2, -1), (-1, -1),
                      (1, 1), (2, 1), (5, 1), (10, 1)]

# ---------------------------------------------------------------------------
# Python simulation of the two programs (cross-check; --simulate uses it)
# ---------------------------------------------------------------------------

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def simulate_mlp(x0, x1, x2, b0, b1, t):
    """Return (y, score) exactly as mlp.omni computes them."""
    a0, a1, a2 = _clamp(x0, -10, 10), _clamp(x1, -10, 10), _clamp(x2, -10, 10)
    h0 = max(0, a0 + a1 + b0)
    h1 = max(0, a1 + a2 + b1)
    score = h0 + h1 + t
    y = 1 if score > 0 else (-1 if score < 0 else 0)
    return y, score


def simulate_perceptron(x, target, w):
    """Return (y, w_new) exactly as perceptron.omni computes them."""
    inp = _clamp(x, -10, 10)
    tgt = _clamp(target, -1, 1)
    wt = _clamp(w, -99, 99)
    y = 1 if wt * inp > 0 else (-1 if wt * inp < 0 else 0)
    w_upd = _clamp(wt + tgt * inp, -99, 99)
    w_new = wt if y == tgt else w_upd
    return y, w_new


# ---------------------------------------------------------------------------
# omnic evaluation
# ---------------------------------------------------------------------------

def _run_omnic(omni_file, args, timeout=30):
    """Run `omnic run <file> <args...>` from OMNI_DIR; return the Int value."""
    cmd = [OMNIC, "run", str(omni_file)] + [str(a) for a in args]
    r = subprocess.run(cmd, cwd=OMNI_DIR, capture_output=True, text=True,
                       timeout=timeout)
    out = r.stdout.strip()
    if not out.startswith("Int(") or not out.endswith(")"):
        raise RuntimeError(f"omnic run failed ({cmd}): stdout={out!r} "
                           f"stderr={r.stderr.strip()!r}")
    return int(out[4:-1])


def mlp_variant_text(b0, b1, t):
    """The mlp.omni template with the three parameter literals substituted.

    Each replacement is asserted to occur exactly once, so template drift
    fails loudly instead of silently producing a wrong variant.
    """
    text = MLP_TEMPLATE.read_text()
    subs = [
        ("neuron(a0, a1, -8)", f"neuron(a0, a1, {b0})"),
        ("neuron(a1, a2, -8)", f"neuron(a1, a2, {b1})"),
        # Full code line (the bare "h0 + h1 - 5" also occurs in the header
        # comment, so the substitution must target the code line only).
        ("let score: i64 = h0 + h1 - 5;", f"let score: i64 = h0 + h1 + ({t});"),
    ]
    for old, new in subs:
        if text.count(old) != 1:
            raise RuntimeError(f"template drift: {old!r} occurs "
                               f"{text.count(old)} times in mlp.omni")
        text = text.replace(old, new)
    header = (f"// GENERATED VARIANT — Mode 6.3 tuning candidate "
              f"(b0={b0}, b1={b1}, t={t}). Not the mlp.omni on main.\n")
    return header + text


def eval_mlp_omnic(b0, b1, t, variant_path):
    """Score theta=(b0,b1,t) via omnic: (errors, margin, per-case list)."""
    variant_path.write_text(mlp_variant_text(b0, b1, t))
    errors = []
    margin = 0
    cases = []
    for (x, label) in DATASET:
        packed = _run_omnic(variant_path, x)
        if not 0 <= packed <= 500:
            raise RuntimeError(f"mlp packed out of range: {packed}")
        y = packed // 200 - 1
        score = packed % 200 - 50
        cases.append((x, label, y, score))
        if y != label:
            errors.append((x, label, y))
        else:
            margin += abs(score)
    return len(errors), margin, errors, cases


def eval_mlp_sim(b0, b1, t):
    """Score theta via the Python simulation (same fitness, no omnic)."""
    errors = []
    margin = 0
    cases = []
    for (x, label) in DATASET:
        y, score = simulate_mlp(*x, b0, b1, t)
        cases.append((x, label, y, score))
        if y != label:
            errors.append((x, label, y))
        else:
            margin += abs(score)
    return len(errors), margin, errors, cases


def eval_perceptron_omnic(w):
    """Score a perceptron weight w via omnic: (errors, margin)."""
    errors = 0
    margin = 0
    for (x, label) in PERCEPTRON_DATASET:
        packed = _run_omnic(PERCEPTRON_FILE, [x, label, w])
        y = packed % 3 - 1
        if y != label:
            errors += 1
        else:
            margin += abs(w * _clamp(x, -10, 10))
    return errors, margin


def eval_perceptron_sim(w):
    errors = 0
    margin = 0
    for (x, label) in PERCEPTRON_DATASET:
        y, _ = simulate_perceptron(x, label, w)
        if y != label:
            errors += 1
        else:
            margin += abs(w * _clamp(x, -10, 10))
    return errors, margin


# ---------------------------------------------------------------------------
# (1+1)-CMA-ES with Margin
# ---------------------------------------------------------------------------

class CMAESWithMargin:
    """(1+1)-CMA-ES with a per-dimension margin on integer change.

    State: mean m (continuous), step size sigma, covariance C, evolution
    path pc, smoothed success rate psucc. See the module docstring for the
    exact variant implemented.
    """

    def __init__(self, bounds, x0, sigma0=2.0, alpha=0.1, seed=None):
        self.n = len(bounds)
        self.lo = np.array([b[0] for b in bounds], dtype=float)
        self.hi = np.array([b[1] for b in bounds], dtype=float)
        self.m = np.array(x0, dtype=float)
        self.sigma = float(sigma0)
        self.C = np.eye(self.n)
        self.pc = np.zeros(self.n)
        self.alpha = float(alpha)
        self.rng = np.random.default_rng(seed)
        self.z_alpha = statistics.NormalDist().inv_cdf(1 - alpha / 2)
        # CMA-ES constants (standard values for the rank-one update).
        self.cc = 4.0 / (self.n + 4.0)
        self.c_cov = 2.0 / ((self.n + 1.3) ** 2 + 0.5)
        # 1/5 success rule.
        self.psucc = 0.2
        self.d = 1.0 + self.n / 2.0
        self.sigma_min, self.sigma_max = 0.05, 5.0

    def discretize(self, x):
        return np.clip(np.round(x), self.lo, self.hi).astype(int)

    def sample(self):
        """One offspring: continuous x and its discretized form."""
        L = np.linalg.cholesky(self.C)
        z = self.rng.standard_normal(self.n)
        x = self.m + self.sigma * (L @ z)
        return x, self.discretize(x)

    def enforce_margin(self):
        """Force P(round(sample_i) != round(m_i)) >= alpha per dimension.

        Marginal std s_i = sigma*sqrt(C_ii). Distance from m_i to the
        nearest cell boundary d_i = 0.5 - |m_i - round(m_i)|. The margin
        needs s_i >= d_i / z_alpha; enforce it by scaling C_ii up.
        """
        for i in range(self.n):
            s_i = self.sigma * math.sqrt(self.C[i, i])
            d_i = 0.5 - abs(self.m[i] - round(self.m[i]))
            required = d_i / self.z_alpha
            if s_i < required:
                self.C[i, i] = (required / self.sigma) ** 2

    def update(self, x, success):
        """(1+1) update after evaluating the offspring x.

        success: the offspring's fitness was <= the parent's.
        On success the mean moves to x and the covariance adapts by the
        rank-one update; on failure only sigma shrinks (1/5 rule).
        """
        if success:
            y = (x - self.m) / self.sigma
            self.m = x.copy()
            self.pc = ((1 - self.cc) * self.pc
                       + math.sqrt(self.cc * (2 - self.cc)) * y)
            self.C = ((1 - self.c_cov) * self.C
                      + self.c_cov * np.outer(self.pc, self.pc))
        # 1/5 success rule (smoothed).
        self.psucc = 0.8 * self.psucc + 0.2 * (1.0 if success else 0.0)
        self.sigma *= math.exp((self.psucc - 0.2) / self.d)
        self.sigma = float(np.clip(self.sigma, self.sigma_min, self.sigma_max))
        self.enforce_margin()


def latin_hypercube(bounds, k, rng):
    """k quasi-random points: one per stratum in each dimension."""
    n = len(bounds)
    pts = np.empty((k, n))
    for j, (lo, hi) in enumerate(bounds):
        strata = (np.arange(k) + rng.random(k)) / k
        rng.shuffle(strata)
        pts[:, j] = lo + strata * (hi - lo)
    return np.clip(np.round(pts), [b[0] for b in bounds],
                   [b[1] for b in bounds]).astype(int)


# ---------------------------------------------------------------------------
# The two tests
# ---------------------------------------------------------------------------

def run_test(name, bounds, evaluate, max_evals, seed, warm_k=16, stop_at=None,
             sigma0=2.0, restart_after=50):
    """Warm start + (1+1)-CMA-ES with Margin, with restarts on stagnation.

    evaluate(theta_tuple) -> (errors, margin) with lower lexicographic
    fitness better. stop_at: stop early when errors <= stop_at.

    Restarts: (1+1)-CMA-ES is a local search, and the margin tiebreaker
    can pull it into a high-margin basin far from the low-error region
    (observed: it drifts to the b0=0 / b1=0 boundary, 3 errors, margin
    ~124, and never reaches the 2-error region). Margin improvements do
    NOT reset the stagnation counter — only a lower error count does —
    because the search can keep "succeeding" on margin while never
    improving errors. When the best error count has not improved for
    restart_after evals, the CMA-ES restarts from the next-best warm
    point (then a fresh uniform point once the warm points are used up),
    keeping the global best. Restarts are standard CMA-ES practice
    (IPOP); the method is still (1+1)-CMA-ES with Margin, run as
    independent climbs from the warm start.
    """
    rng = np.random.default_rng(seed)
    cache = {}
    log = []

    def fitness(theta):
        theta = tuple(int(v) for v in theta)
        if theta not in cache:
            errors, margin = evaluate(theta)
            cache[theta] = (errors, -margin)  # lower is better
        return cache[theta]

    # Warm start: Latin Hypercube, k points, sorted by fitness.
    warm_pts = []
    for pt in latin_hypercube(bounds, warm_k, rng):
        f = fitness(pt)
        warm_pts.append((f, tuple(pt)))
        log.append(("warm", tuple(pt), f))
    warm_pts.sort()
    best_fit, best_theta = warm_pts[0]
    print(f"[{name}] warm start ({warm_k}): best {best_theta} "
          f"errors={best_fit[0]} margin={-best_fit[1]}")

    # (1+1)-CMA-ES with Margin; restart on error-count stagnation.
    def fresh_es(mean):
        return CMAESWithMargin(bounds, x0=np.array(mean, dtype=float),
                               sigma0=sigma0, alpha=0.1, seed=seed)
    es = fresh_es(best_theta)
    used_centers = {best_theta}
    n_evals = warm_k
    restarts = 0
    since_error_improve = 0
    best_errors = best_fit[0]
    while n_evals < max_evals:
        x, xd = es.sample()
        f = fitness(xd)
        success = f <= best_fit
        if success:
            best_theta, best_fit = tuple(xd), f
            log.append(("cma", tuple(xd), f, "ACCEPT"))
        else:
            log.append(("cma", tuple(xd), f, "reject"))
        if best_fit[0] < best_errors:
            best_errors = best_fit[0]
            since_error_improve = 0
        else:
            since_error_improve += 1
        es.update(x, success)
        n_evals += 1
        if stop_at is not None and best_fit[0] <= stop_at:
            print(f"[{name}] stop: {best_fit[0]} errors at {best_theta} "
                  f"after {n_evals} evals")
            break
        if since_error_improve >= restart_after:
            restarts += 1
            # Next-best unused warm point, else a fresh uniform point.
            center = None
            for _, pt in warm_pts:
                if pt not in used_centers:
                    center = pt
                    break
            if center is None:
                center = tuple(int(v) for v in rng.uniform(
                    [b[0] for b in bounds], [b[1] for b in bounds]))
            used_centers.add(center)
            es = fresh_es(center)
            since_error_improve = 0
            print(f"[{name}] restart {restarts} at eval {n_evals} from "
                  f"{center} (best still {best_theta} errors={best_fit[0]})")
    print(f"[{name}] final: best {best_theta} errors={best_fit[0]} "
          f"margin={-best_fit[1]} after {n_evals} evals "
          f"({len(cache)} unique, {restarts} restarts)")
    return best_theta, best_fit, n_evals, log


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate", action="store_true",
                    help="score with the Python simulation, not omnic")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-evals", type=int, default=300)
    ap.add_argument("--only", choices=["perceptron", "mlp"], default=None)
    args = ap.parse_args()

    if not args.simulate:
        if not Path(OMNIC).exists() and not shutil.which(OMNIC):
            sys.exit(f"omnic not found: {OMNIC} (set $OMNIC)")
        if not Path(OMNI_DIR, "pure").is_dir():
            sys.exit(f"no pure/ tree in OMNI_DIR: {OMNI_DIR} (set $OMNI_DIR)")

    tmp = Path(tempfile.mkdtemp(prefix="mode63_"))
    variant = tmp / "mlp_variant.omni"

    def eval_mlp(theta):
        b0, b1, t = theta
        if args.simulate:
            e, m, _, _ = eval_mlp_sim(b0, b1, t)
        else:
            e, m, _, _ = eval_mlp_omnic(b0, b1, t, variant)
        return e, m

    def eval_perc(theta):
        (w,) = theta
        if args.simulate:
            return eval_perceptron_sim(w)
        return eval_perceptron_omnic(w)

    if args.only in (None, "perceptron"):
        print("== perceptron 1-D sanity check (any w > 0 is optimal) ==")
        best, fit, n, _ = run_test(
            "perceptron", [(-99, 99)], eval_perc,
            max_evals=60, seed=args.seed, warm_k=8, stop_at=0)
        print(f"   perceptron: {'PASS' if fit[0] == 0 and best[0] > 0 else 'FAIL'} "
              f"(w={best[0]}, errors={fit[0]})")

    if args.only in (None, "mlp"):
        print("== mlp 3-D tuning (theta = b0, b1, t) ==")
        print("   baseline (-8,-8,-5):", eval_mlp((-8, -8, -5)))
        best, fit, n, log = run_test(
            "mlp", [(-16, 0), (-16, 0), (-12, 0)], eval_mlp,
            max_evals=args.max_evals, seed=args.seed, warm_k=16, stop_at=1)
        print(f"   mlp: {'PASS (1-error theta found)' if fit[0] == 1 else 'FAIL'} "
              f"theta={best} errors={fit[0]} margin={-fit[1]}")
        # The tuned variant's goldens, for the record.
        b0, b1, t = best
        if args.simulate:
            gold = [simulate_mlp(*c, b0, b1, t) for c in GOLDENS]
            print("   tuned goldens (y,score):", gold)
        else:
            variant.write_text(mlp_variant_text(b0, b1, t))
            gold = []
            for c in GOLDENS:
                packed = _run_omnic(variant, c)
                gold.append((packed // 200 - 1, packed % 200 - 50, packed))
            print("   tuned goldens (y,score,packed):", gold)

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
