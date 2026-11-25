#!/usr/bin/env python3
"""Mode 6.3 tuner — (1+1)-CMA-ES with Margin (host-side harness).

Tuning a Pure Omni program's integer parameters by derivative-free search.
The tuner is host-side (Python); the program under test is Pure Omni and
every candidate is verified by running it through `omnic run`. No Omni
change is needed to run this test.

Method (per PAPER.md SS6.3 / FOUNDATION.md SS10, from the Mode 6.3
monograph): warm-start with quasi-random samples (Latin Hypercube; 32
points for 4-D mlp3, 8 for 1-D perceptron), then (1+1)-CMA-ES with Margin
on the integer parameter vector, with independent local restarts on
error-count stagnation (every 30 evals without error improvement; margin
improvements do NOT reset the stagnation counter — only a lower error
count does). Restarts alternate between the global best theta (fresh
covariance, alternating sigma0 and 1.5*sigma0) and the next-best unused
warm point (then fresh uniform points), each with its own local parent
fitness and derived RNG sub-seed.

  (1+1)-CMA-ES: one parent, one offspring per iteration. The offspring is
  sampled from N(m, sigma^2 * C); the covariance C adapts by the rank-one
  update from the evolution path (the CMA-ES part); the step size sigma
  adapts by the 1/5 success rule. The mean stays continuous; the candidate
  is discretized (rounded to the nearest integer, clipped to bounds) for
  evaluation.

  Margin: after each update, for each dimension, the probability that a
  sample rounds to a different integer than round(m_i) is forced to be
  at least alpha (default 1/max(4, n), i.e. 0.25 in 4-D per Hamano et al.'s
  1/(N*lambda) rule). The marginal is N(m_i, s_i^2) with
  s_i = sigma*sqrt(C_ii); the distance from m_i to the nearest cell
  boundary is d_i = 0.5 - |m_i - round(m_i)|; the margin requires
  s_i >= d_i / z_alpha where z_alpha = Phi^{-1}(1 - alpha/2). This is
  enforced by scaling C_ii up. This is a per-dimension variance floor
  derived from the same probability (not Hamano's exact mean-shift
  correction).

Fitness is lexicographic, per the monograph (SS3): (1) fewest
misclassifications, then (2) largest capped total margin (sum of
min(|score|, margin_cap) over correctly classified cases; default
margin_cap=2 derived from the 4-D answer key's 0-error |score| median
of 2, preventing high-margin 1-error traps from pulling climbs away from
the 0-error cluster). Lower is better; a candidate that fails verification
scores as invalid (errors = inf), never as 0.

Usage:
  python3 tuner.py [--simulate] [--seed N] [--max-evals N] [--only NAME]
                   [--margin-cap N]

  --simulate      score candidates with the Python simulation instead of
                  omnic (fast; use to test the tuner logic, not the result).
  --seed N        RNG seed (default 1).
  --max-evals N   evaluation budget for the mlp test (default 1000).
  --only NAME     run only 'perceptron' or 'mlp' (default: both).
  --margin-cap N  per-case |score| cap for mlp margin tiebreaker
                  (default 2; 0 = uncapped).

Environment (for the omnic path):
  OMNIC     path to the omnic binary (default: omnic on PATH, else
            $HOME/workspace/omnic-main).
  OMNI_DIR  Omni checkout containing a pure/ tree; `omnic run` must be
            invoked from a directory containing pure/ (default:
            $HOME/workspace/omni-main).

4-D 3-neuron mlp3 answer key (exhaustive grid [-20,5]^4, 456,976 points):
  baseline (-8,-8,-8,-5): 3 errors (margin 143).
  global optimum: 0 errors; 14 points reach it (all inside [-16,0]^3 x [-12,0]),
  highest uncapped margin 74 at (-12,-14,-14,-3), symmetric optimum at
  (-14,-14,-14,-1) (margin 66).
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
    Path.home() / "workspace" / "omnic-main"
)
OMNI_DIR = os.environ.get("OMNI_DIR") or str(
    Path.home() / "workspace" / "omni-main"
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


def simulate_mlp(x0, x1, x2, b0, b1, b2, t):
    """Return (y, score) for the 3-neuron mlp3 topology."""
    a0, a1, a2 = _clamp(x0, -10, 10), _clamp(x1, -10, 10), _clamp(x2, -10, 10)
    h0 = max(0, a0 + a1 + b0)
    h1 = max(0, a1 + a2 + b1)
    h2 = max(0, a0 + a2 + b2)
    score = h0 + h1 + h2 + t
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


def mlp_variant_text(b0, b1, b2, t):
    """The 3-neuron mlp3 variant built from the mlp.omni template.

    Substitutes b0, b1, inserts h2 = neuron(a0, a2, b2) after the h1 line,
    and updates the score line to h0 + h1 + h2 + (t). Each target pattern is
    asserted to occur exactly once, so template drift fails loudly.
    """
    text = MLP_TEMPLATE.read_text()
    h1_line = "    let h1: i64 = neuron(a1, a2, -8);"
    h1_new = (f"    let h1: i64 = neuron(a1, a2, {b1});\n"
              f"    let h2: i64 = neuron(a0, a2, {b2});")
    subs = [
        ("neuron(a0, a1, -8)", f"neuron(a0, a1, {b0})"),
        (h1_line, h1_new),
        # Full code line (the bare "h0 + h1 - 5" also occurs in the header
        # comment, so the substitution must target the code line only).
        ("let score: i64 = h0 + h1 - 5;",
         f"let score: i64 = h0 + h1 + h2 + ({t});"),
    ]
    for old, new in subs:
        if text.count(old) != 1:
            raise RuntimeError(f"template drift: {old!r} occurs "
                               f"{text.count(old)} times in mlp.omni")
        text = text.replace(old, new)
    header = (f"// GENERATED VARIANT — Mode 6.3 3-neuron tuning candidate "
              f"(b0={b0}, b1={b1}, b2={b2}, t={t}). Not the mlp.omni on main.\n")
    return header + text


def _margin_contrib(score, margin_cap):
    m = abs(score)
    if margin_cap is not None and margin_cap > 0 and m > margin_cap:
        return margin_cap
    return m


def eval_mlp_omnic(b0, b1, b2, t, variant_path, margin_cap=2):
    """Score theta=(b0,b1,b2,t) via omnic: (errors, margin, err_list, cases)."""
    variant_path.write_text(mlp_variant_text(b0, b1, b2, t))
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
            margin += _margin_contrib(score, margin_cap)
    return len(errors), margin, errors, cases


def eval_mlp_sim(b0, b1, b2, t, margin_cap=2):
    """Score theta via the Python simulation (same fitness, no omnic)."""
    errors = []
    margin = 0
    cases = []
    for (x, label) in DATASET:
        y, score = simulate_mlp(*x, b0, b1, b2, t)
        cases.append((x, label, y, score))
        if y != label:
            errors.append((x, label, y))
        else:
            margin += _margin_contrib(score, margin_cap)
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

def run_test(name, bounds, evaluate, max_evals, seed, warm_k=32, stop_at=None,
             sigma0=2.0, restart_after=30, alpha=None):
    """Warm start + (1+1)-CMA-ES with Margin, with independent local restarts.

    evaluate(theta_tuple) -> (errors, margin) with lower lexicographic
    fitness better. stop_at: stop early when errors <= stop_at.

    Restarts: (1+1)-CMA-ES is a local search, and margin ties can trap a
    climb in a suboptimal basin. Margin improvements do NOT reset the
    stagnation counter — only a lower error count does. When the current
    climb's error count has not improved for restart_after evals, CMA-ES
    restarts with fresh covariance and a derived RNG sub-seed, alternating
    between the global best_theta (alternating sigma0 and 1.5*sigma0) and
    the next-best unused warm point (then fresh uniform points). Each
    restart tracks its own local parent_fit so climbs from warm points can
    descend, while global best_fit / best_theta are always preserved.
    """
    rng = np.random.default_rng(seed)
    if alpha is None:
        alpha = 1.0 / max(4, len(bounds))
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
        tpt = tuple(int(v) for v in pt)
        f = fitness(tpt)
        warm_pts.append((f, tpt))
        log.append(("warm", tpt, f))
    warm_pts.sort()
    best_fit, best_theta = warm_pts[0]
    print(f"[{name}] warm start ({warm_k}): best {best_theta} "
          f"errors={best_fit[0]} margin={-best_fit[1]}")

    # (1+1)-CMA-ES with Margin; independent local restarts on stagnation.
    def fresh_es(mean, sig=sigma0):
        sub_seed = int(rng.integers(0, 2**31 - 1))
        return CMAESWithMargin(bounds, x0=np.array(mean, dtype=float),
                               sigma0=sig, alpha=alpha, seed=sub_seed)

    es = fresh_es(best_theta)
    parent_fit = best_fit
    local_best_errors = best_fit[0]
    used_centers = {best_theta}
    n_evals = warm_k
    restarts = 0
    since_error_improve = 0
    if stop_at is not None and best_fit[0] <= stop_at:
        print(f"[{name}] stop: {best_fit[0]} errors at {best_theta} "
              f"after {n_evals} evals")
    else:
        while n_evals < max_evals:
            x, xd = es.sample()
            txd = tuple(int(v) for v in xd)
            f = fitness(txd)
            success = f <= parent_fit
            if success:
                parent_fit = f
                log.append(("cma", txd, f, "ACCEPT"))
            else:
                log.append(("cma", txd, f, "reject"))
            if f < best_fit:
                best_theta, best_fit = txd, f
            if parent_fit[0] < local_best_errors:
                local_best_errors = parent_fit[0]
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
                if restarts % 2 == 1:
                    center = best_theta
                    sig = sigma0 * 1.5 if (restarts // 2) % 2 == 1 else sigma0
                else:
                    center = None
                    for _, pt in warm_pts:
                        if pt not in used_centers:
                            center = pt
                            break
                    if center is None:
                        center = tuple(int(v) for v in rng.uniform(
                            [b[0] for b in bounds], [b[1] for b in bounds]))
                    used_centers.add(center)
                    sig = sigma0
                parent_fit = fitness(center)
                local_best_errors = parent_fit[0]
                es = fresh_es(center, sig=sig)
                since_error_improve = 0
                print(f"[{name}] restart {restarts} at eval {n_evals} from "
                      f"{center} (sigma0={sig:.1f}, best still {best_theta} "
                      f"errors={best_fit[0]})")
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
    ap.add_argument("--max-evals", type=int, default=1000)
    ap.add_argument("--only", choices=["perceptron", "mlp"], default=None)
    ap.add_argument("--margin-cap", type=int, default=2,
                    help="per-case |score| cap for mlp margin (0 = uncapped)")
    args = ap.parse_args()
    margin_cap = args.margin_cap if args.margin_cap > 0 else None

    if not args.simulate:
        if not Path(OMNIC).exists() and not shutil.which(OMNIC):
            sys.exit(f"omnic not found: {OMNIC} (set $OMNIC)")
        if not Path(OMNI_DIR, "pure").is_dir():
            sys.exit(f"no pure/ tree in OMNI_DIR: {OMNI_DIR} (set $OMNI_DIR)")

    tmp = Path(tempfile.mkdtemp(prefix="mode63_"))
    variant = tmp / "mlp3_variant.omni"

    def eval_mlp(theta):
        b0, b1, b2, t = theta
        if args.simulate:
            e, m, _, _ = eval_mlp_sim(b0, b1, b2, t, margin_cap=margin_cap)
        else:
            e, m, _, _ = eval_mlp_omnic(b0, b1, b2, t, variant,
                                        margin_cap=margin_cap)
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
        print(f"== mlp3 4-D tuning (theta = b0, b1, b2, t; margin_cap={margin_cap}) ==")
        print("   baseline (-8,-8,-8,-5):", eval_mlp((-8, -8, -8, -5)))
        best, fit, n, log = run_test(
            "mlp3", [(-16, 0), (-16, 0), (-16, 0), (-12, 0)], eval_mlp,
            max_evals=args.max_evals, seed=args.seed, warm_k=32, stop_at=0,
            restart_after=30)
        print(f"   mlp3: {'PASS (0-error theta found)' if fit[0] == 0 else 'FAIL'} "
              f"theta={best} errors={fit[0]} margin={-fit[1]}")
        # The tuned variant's goldens, for the record.
        b0, b1, b2, t = best
        if args.simulate:
            gold = [simulate_mlp(*c, b0, b1, b2, t) for c in GOLDENS]
            print("   tuned goldens (y,score):", gold)
        else:
            variant.write_text(mlp_variant_text(b0, b1, b2, t))
            gold = []
            for c in GOLDENS:
                packed = _run_omnic(variant, c)
                gold.append((packed // 200 - 1, packed % 200 - 50, packed))
            print("   tuned goldens (y,score,packed):", gold)

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
