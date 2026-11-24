# Omni Programs — Usability Series

Programs built to test Omni usability. All run via `omnic run` on `main`
(the M3 builtins fix is merged; build `omnic` from the repo root with
`rustc -O omni_rust_bootstrap.rs -o omnic`). Run them from the repo root so the
relative `pure/` paths resolve.

## The programs

### 1. Thermostat — `thermostat.omni`

A thermostat controller. Given the current temperature and the target,
decide heat / off / cool and pack the answer into one i64:
`action * 100 + magnitude`, where action is 0 = off, 1 = heat, 2 = cool,
and magnitude is how far off target (0..10, clamped).

Uses `std_clamp`, `egate`, `std_trit_mux`, `iabs` — the builtins the M3
fix unblocked. **6/6 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (20, 22) | 102 | 2 cold, heat |
| (22, 22) | 0 | at target, off |
| (25, 22) | 203 | 3 hot, cool |
| (10, 22) | 110 | 12 cold, clamped to 10, heat |
| (35, 22) | 210 | 13 hot, clamped to 10, cool |
| (22, 20) | 202 | 2 hot, cool |

### 2. Trit pack — `trit_pack.omni`

Packs three balanced trits (-1, 0, +1) into one number with base-3
positional encoding: `(t0+1)*9 + (t1+1)*3 + (t2+1)`, result 0..26.
Each trit is clamped to [-1, 1] first. This is the @PACK5 packing done
by hand (pack5_bytes still needs an array literal and does not run from
disk yet). **5/5 test cases pass.**

| Input | Output |
|---|---|
| (1, 1, 1) | 26 |
| (-1, -1, -1) | 0 |
| (0, 0, 0) | 13 |
| (1, 0, -1) | 21 |
| (5, -5, 0) | 19 (clamped) |

### 3. Running stats — `running_stats.omni`

Given three sensor readings, returns the max and the min packed into one
i64: `(max + 50) * 100 + (min + 50)`. Inputs are clamped to [-50, 49]
so the packing stays unambiguous. **5/5 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (3, 7, 2) | 5752 | max 7, min 2 |
| (5, 5, 5) | 5555 | max 5, min 5 |
| (-3, 0, 4) | 5447 | max 4, min -3 |
| (100, -100, 0) | 9900 | clamped to 49 and -50 |
| (0, 0, 0) | 5050 | max 0, min 0 |

### 4. Collatz — `collatz.omni` (the advanced one)

The Collatz sequence analyzer. Start from n; if even, halve it; if odd,
replace it with 3n+1; repeat until you reach 1. Returns
`steps * 100000 + peak`, where steps is how many steps it took (capped
at max_steps) and peak is the highest value reached (clamped to 99999
for the packing).

This is the most advanced program in the series: it uses a `while` loop,
a helper function (`collatz_step`), integer division, `egate`,
`std_trit_mux`, `imax`, and `std_clamp` together. The loop condition
encodes a conjunction without a boolean AND — `(cur - 1) * (budget - steps)`
is nonzero exactly when cur != 1 AND steps < budget, so the loop stops
when either the sequence reaches 1 or the step budget runs out.
**5/5 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (6, 100) | 800016 | 8 steps, peak 16 |
| (1, 100) | 1 | already 1, 0 steps, peak 1 |
| (27, 200) | 11109232 | 111 steps, peak 9232 |
| (10, 3) | 300016 | budget cap: 3 steps, peak 16 |
| (7, 100) | 1600052 | 16 steps, peak 52 |

Notably, this proves loops, helper functions, and integer division all
work via `run` on the fix branch — none of those had been exercised by
the earlier programs.

### 5. PID sim — `pid_sim.omni` (the hyper-complex one)

A complete closed-loop control system: a PID controller driving a
first-order plant toward a target, simulated step by step. The same
controller that runs real robots, drones, thermostats, and industrial
processes. Gains Kp=1, Ki=1, Kd=1; integral with anti-windup (clamped
to [-10, 10]); output saturation (clamped to [-99, 99]); plant gain 1/4.
A helper function (`pid_output`) computes each control step; `main`
runs the simulation loop and packs the final value and final error into
one i64: `(cur + 100) * 400 + (err + 200)`.
**5/5 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (16, 0, 4) | 46600 | converges exactly to 16 in 4 steps |
| (0, 0, 5) | 40200 | already there, stays put |
| (10, 0, 3) | 44200 | converges exactly to 10 in 3 steps |
| (20, 0, 5) | 48599 | ends at 21, 1 past target — the integral term overshoots slightly, which is real PID behavior |
| (10, 5, 2) | 43801 | starts halfway there, ends at 9 |

The (20, 0, 5) overshoot is not a bug: it is the integral term doing
its job a little too well, the classic PID tradeoff. Anti-windup keeps
it to 1 instead of much worse.

### 6. Perceptron — `perceptron.omni` (a learning machine)

A single perceptron that LEARNS — the atom of neural networks, running
in the language built for AI. Given an input, a target (-1 or +1), and
the current weight, it predicts with sign(w*x), compares, and updates
the weight by the perceptron rule (w += target*x) only when wrong.
Returns `(w_new + 100) * 3 + (y + 1)`, packing the new weight and the
prediction. Call it repeatedly with new examples and the weight
converges to a classifier. The update is selected with
`egate` + `std_trit_mux`: the gate is 0 when the prediction matches
(no update) and nonzero when it does not.
**5/5 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (2, 1, 0) | 307 | undecided at w=0, learns w=2 |
| (2, 1, 5) | 317 | already right, w stays 5 |
| (3, -1, 4) | 305 | wrong, w drops from 4 to 1 |
| (-2, -1, 3) | 309 | already right, w stays 3 |
| (5, 1, 90) | 572 | already right, w stays 90 |

### 7. Mandelbrot — `mandelbrot.omni` (a fractal)

The Mandelbrot set escape-time calculator: the set of complex numbers c
for which z = z^2 + c, starting from 0, stays bounded forever. Counts
how many iterations a point takes to escape (|z| > 2), or reports the
step limit if it never does. Fixed-point arithmetic, scale 100. The
loop condition uses the same product trick as Collatz: f * (max_iter -
iter) is nonzero exactly while the point is still inside AND steps
remain, where f is 1 inside and 0 outside.
**5/5 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (0, 0, 100) | 100 | c=0, never escapes, in the set |
| (200, 0, 100) | 2 | c=2, escapes almost immediately |
| (100, 0, 100) | 3 | c=1, escapes in 3 steps |
| (-100, 0, 100) | 100 | c=-1, oscillates 0 -> -1 -> 0, in the set |
| (50, 50, 100) | 5 | c=0.5+0.5i, escapes in 5 steps |

### 8. MLP — `mlp.omni` (a neural network, a program for AI)

A real multi-layer perceptron forward pass: three inputs, a hidden layer
of two ReLU neurons, and a sign output. The perceptron was one neuron
that learns; this is a network that decides. Framed as a fault
classifier over three sensor readings (temperature, vibration,
pressure): h0 fires when temperature + vibration is high, h1 fires
when vibration + pressure is high, and the output fires only when the
combined evidence clears a threshold. A single sensor being high is not
enough — that is what the hidden layer buys over a single perceptron.
Returns `(y + 1) * 200 + (score + 50)`, packing the classification
(+1 fault, -1 healthy) and the raw evidence score.
**5/5 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (10, 10, 10) | 469 | all high, fault, score 19 |
| (0, 0, 0) | 45 | all low, healthy, score -5 |
| (10, 0, 0) | 47 | one high, not enough, healthy, score -3 |
| (5, 5, 5) | 49 | middling, healthy, score -1 |
| (8, 8, 8) | 461 | all elevated, fault, score 11 |

### 9. Agent — `agent.omni` (a large program: a complete autonomous agent)

A full sense-decide-act loop in a single program — 129 lines, five
functions, five stages. It reads three sensors, classifies the system's
health with the MLP, decides how serious the situation is, computes a
control action with the PID controller, and reports everything packed
into one number. It composes the MLP, the PID controller, and the sensor
statistics into one system, and the decision in stage 3 changes what
stage 4 does — the classifier steers the controller. That coupling is
what makes it a system rather than a bag of functions.
**6/6 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (10, 10, 10) | 2200100 | fault, emergency, control -99 |
| (0, 0, 0) | 10000 | healthy, normal, control 0 |
| (10, 0, 0) | 7010 | healthy, normal, control -30 |
| (5, 5, 5) | 8500 | healthy, normal, control -15 |
| (10, -10, 0) | 1008520 | healthy but spread 20, caution, control -15 at half strength |
| (-8, 0, 0) | 12408 | healthy, normal, control +24, heat |

The (10, -10, 0) case is the one that shows the system working: no
single reading is alarming, the MLP says healthy, but the sensors
disagree by 20 — so it drops to caution mode and halves the control
output. No single component would have caught that; only the pipeline
does.

### 10. Agent2 — `agent2.omni` (the agent, deeper)

The agent expanded: the classifier is now a deeper network (two hidden
layers — three detectors in layer 1, two combiners in layer 2), and the
report now includes the raw evidence score. The second layer is what
depth buys: a fault needs two weak signals to agree, not just one
strong one. The (8, 8, 8) case shows it — the shallow network scores it
11, the deep network scores it 7, because the second layer demands more
agreement before it fires hard.
**7/7 test cases pass.**

| Input | Output | Meaning |
|---|---|---|
| (10, 10, 10) | 22560100 | fault, emergency, score 23, control -99 |
| (0, 0, 0) | 10000 | healthy, normal, score -5, control 0 |
| (10, 0, 0) | 7010 | healthy, normal, score -5, control -30 |
| (5, 5, 5) | 8500 | healthy, normal, score -5, control -15 |
| (10, -10, 0) | 10008520 | healthy, spread 20, caution, score -5, control -15 at half strength |
| (-8, 0, 0) | 12408 | healthy, normal, score -5, control +24 |
| (8, 8, 8) | 22240100 | fault, emergency, score 7, control -99 |

### How big can this get?

The caps are per-function (1024 AST nodes) and per-module (~2,388
functions), not per-program — a program scales by composing more
functions and more modules. So 10k lines is achievable, but not by
hand-writing 10k lines of distinct logic in one sitting. A real 10k-line
Omni codebase would be built from: a standard library of reusable
components (math, control, ML, I/O); many specialized modules (different
agents, different networks); data tables and knowledge bases (a trained
network's weights, a fault-signature database) — often generated, not
hand-written; and generated code from a higher-level spec. The agent
grows that way: add a module, add a layer, add a table, and the program
gets bigger without any single function getting close to a cap.

## New bug found: `run` drops arguments past the third

While writing these, a real bug surfaced. `omnic run` only delivers the
first three arguments to `main`; the 4th and later arrive as 0. The Rust
frontend (`eval`) delivers all arguments fine, so this is specific to
the `run` file path (Pure M3 / Pure-M4 arg passing).

Evidence (repro in `arg_repro.omni`, returns `d * 100 + e`):

- `run arg_repro.omni 1 2 3 4 5` → `Int(0)`, expected 405.
- `run arg_repro.omni 0 0 0 7 8` → `Int(0)`, expected 708.
- `eval "fn main(a,b,c,d) -> i64 { return d; }" 0 0 0 9` → `Int(9)`, correct.

This is why the first drafts of `trit_pack` (5 args) and `running_stats`
(4 args) gave wrong answers: the 4th/5th arguments were silently zero.
Both programs were redesigned to three arguments and now pass. A five-trit
pack (a full byte, 0..242) and a four-reading stats version are blocked
until this is fixed.

This is a separate bug from M3_CODE_9 (which Grok is fixing now). It
should go to Grok as its own fix after the builtins PR lands.

## What is still blocked

- The K/V-backed counter service (Program #2 in the original plan) needs
  the host intrinsics (`kv_get`, `kv_put`) and `req.param` to work via
  `run` — that is the M3 follow-up, not yet done.
- Five-trit packing and four-reading stats need the argument bug fixed.
- `pack5_bytes` needs array-literal call handling (same follow-up).
