# Omni Mind Roadmap

## Where we are

**v0.1 foundation is complete.** All six modules (`memory`, `graph`, `activate`, `learn`, `distill`, `ledger`) plus four goldens, 18/18 passing on Linux via `omnic run` with `--rust` cross-check. Pushed to omni-mind main as `05fcc4c3`.

**Five design decisions are recorded** (from "Engineering Foundations for Mode 6.3, the Proposer Loop, and Ternary-Native Execution," Nov 2026; see PAPER.md §6 and FOUNDATION.md §10):
1. Mode 6.3 tuner: **(1+1)-CMA-ES with Margin**, warm-started with 15–20 quasi-random samples.
2. `distill`: **Stitch** (top-down syntactic anti-unification) + admission gate (ΔMDL > 4 nats AND 100% verifier soundness).
3. Proposer loop: **CEGIS + CEGIS(T) verifier gradient** (assertion violated, minimal failing input, localized AST span, ranked repair templates).
4. Persistence: **Git-backed content-addressed store** (Path B — files in a Git repo, SHA-256 addressing, branch-per-agent isolation).
5. Audit view: **SWUM + AST-W-PDT** (deterministic, zero-LLM summaries).

**Standing decision:** build with these proven components first, then revisit each with first principles once the system works (ternary-native optimizer, verifier-native synthesis, native ternary training without a BF16 master, Omni-native store).

**Blocked right now:** all three implementers are down (Grok, Gemini, Claude out of tokens). Three real Omni bugs have directions ready and are waiting for an implementer. The Mind work below is sequenced so the parts that don't need an implementer can move first.

---

## Phase 1 — Persistence (next)

**Goal:** memories survive across runs. The Mind stops being in-memory-only.

- **Git-backed content-addressed store** (Path B, decided). A `store/` directory: one `.omni` file per memory, `links.txt` with `from to weight` edges, and a runner script that walks +1 edges with a fuel budget, exactly like `walk` in `graph.omni`.
- **Runner constraint:** uses the `run` path only, NOT `--rust`. Each per-memory file is single-function, and Grok's `--rust` single-function memory-budget bug breaks those — so the `--rust` cross-check is unavailable for the store until that bug is fixed. This is why the bug fixes and persistence belong together.
- **Prove it:** create a memory, exit the process, and activate it from a fresh process.
- **Regression tests:** Grok's two test programs plus the `golden_walk` cases, run through the runner.
- **Plan already drafted:** `~/workspace/omni-mind-filesystem-prototype.md` (81 lines).
- **Acceptance:** the `golden_walk` cases pass through the runner; a memory created in one process is retrievable in another.
- **Note:** Path A (host intrinsics + persistent K/V store) remains a separate, undecided track. The prototype neither blocks nor replaces it. The Omni-side work for Path A is the M3 intrinsics follow-up (kv/db/pack5/req.param).

---

## Phase 2 — Mode 6.3 for real

**Goal:** prove tunable parameters inside a verified shape. This is the "test Mode 6.3 first" decision from PAPER.md §10.

- **Make parameters variable.** The `mlp` / `perceptron` / `agent2` topologies exist as example programs, but their weights and thresholds are hardcoded literals. Turn them into tunable parameters.
- **Define an objective.** What "better" means — e.g., classification accuracy on a golden set, or a measured metric from the P7 harness. Without an objective, the search space is not actually searchable.
- **Run the tuner.** (1+1)-CMA-ES with Margin: warm-start with 15–20 quasi-random samples, then run CMA-ES directly on the integer parameter vector. Mixed-Integer Bayesian Optimization is the fallback only if tests are expensive (>100 ms); `omnic run` evaluates in milliseconds, so CMA-ES is primary.
- **Acceptance:** a tuned program measures better than its hardcoded baseline on the objective, and still passes the verifier.
- **Depends on:** nothing blocked. Uses existing `run` + verifier. The arg bug doesn't bite (no function takes >2 args).

---

## Phase 3 — Distill for real

**Goal:** replace the `distill.omni` stub (currently identity) with real consolidation.

- **Stitch anti-unification.** Given two program ASTs, find their least general generalization by replacing differing subtrees with fresh λ-bound variables.
- **Admission gate.** A candidate abstraction enters the library only if it passes two formal checks: it compresses the corpus by at least δ_MDL nats (e.g., 4 nats) **and** preserves 100% verifier soundness across all rewritten programs.
- **Acceptance:** two similar memories distill into one shared abstraction that compresses the corpus and keeps every program passing the verifier.
- **Depends on:** Phase 1 (needs a corpus of stored memories to distill from).

---

## Phase 4 — Audit view

**Goal:** deterministic, hallucination-free summaries of what a program does — before the proposer loop starts auto-committing.

- **SWUM** (Software Word Usage Model): a deterministic rule engine that parses identifiers into grammatical parts and maps AST control-flow nodes into canonical English clauses.
- **AST-W-PDT**: converts the token stream back into a structurally normalized AST (relabeling identifiers by semantic role), then traverses it with deterministic grammar templates (`if-cond-then`, `loop-over-range`, `return-expr`).
- **Moreno's Stereotype Identification:** classifies functions as accessor, mutator, predicate, or controller.
- **Must land before the proposer loop starts auto-committing** (Caleb's sequencing decision). The audit view lands as both M3-shaped text and the plain-language summary in the same step.
- **Acceptance:** every proposed commit gets a reproducible, diff-friendly summary; two runs of the same program produce byte-identical summaries; no LLM narration anywhere.
- **Depends on:** the decompiler (M3-shaped text). The summary needs a gateable form.

---

## Phase 5 — Proposer loop

**Goal:** verified self-improvement, 100% AI-maintainable, no human intervention.

- **CEGIS.** The proposer generates a candidate consistent with all accumulated counterexamples; the verifier tests it against the full specification. If it fails, the verifier returns a concrete counterexample the next proposal must satisfy — each round is monotonically more correct.
- **CEGIS(T) verifier gradient.** The verifier returns structured feedback, not bare pass/fail: the exact assertion violated, the minimal failing input witness, the localized AST span where the trace diverged, and ranked repair templates.
- **Tuner + distill + store.** (1+1)-CMA-ES with Margin tunes parameters; Stitch distills new abstractions; the Git-backed store holds the growing library.
- **Auto-commit.** On +1t ADOPT, the proposer auto-commits to the `flywheel/auto` branch (Caleb's §6 Q3 decision). The merge gate is the automated verification pipeline (CI + Linux verification).
- **Acceptance:** the loop proposes, verifies, measures, and adopts a real improvement with no human in the loop.
- **Depends on:** Phases 1–4, **plus automated Linux verification as the merge gate**. Today Lilith's Linux verification is tap-triggered by Caleb; an auto-merge without an automated Linux check would repeat the Round 2 failure mode (merged with no Linux run). That automation is a prerequisite, not an afterthought.

---

## Phase 6 — Scale

**Goal:** the graph grows to millions of memories without falling over.

- **Traversal efficiency.** Walking a graph of millions of programs, not two.
- **Activation relevance.** Which memories to activate from a cue, and which to leave alone.
- **Entanglement.** Cross-graph dependencies — what breaks when a memory is distilled or retired.
- **Garbage collection at scale.** Sleep-time GC (prune stale records, deduplicate skills, compact traces) must keep up with growth.
- **This is the open question.** PAPER.md §8 is honest about it: the approach is unproven at scale, and it is not clear GC alone is sufficient at very large scale. The only way to answer it is to build it and measure.
- **Acceptance:** defined by measurement once Phases 1–5 work at small scale. The P7 measurement loop gives us the tools to measure.
- **Depends on:** Phases 1–5 working at small scale first.

---

## Phase 7 — First principles revisit

**Goal:** replace each proven component with a ternary-native / Omni-native version — once the system works.

- **Ternary-native optimizer.** A search method that exploits the ternary structure of the parameter space, rather than treating it as a generic integer vector.
- **Verifier-native synthesis.** A feedback format suited to a capability/taint/ownership verifier, rather than CEGIS (which was built for SMT solvers checking logical formulas).
- **Native ternary training.** Train ternary weights without a BF16 master copy (the Straight-Through Estimator's binary crutch).
- **Omni-native store.** A store for memories built on Omni itself, rather than Git (a binary filesystem tool).
- **This happens after the system works, not instead of building it.** If the proven components work well enough that the first-principles versions never become necessary, that is a good outcome, not a failure — but the questions stay on the list.

---

## Phase 8 — NetNavi

**Goal:** the agent layer on top of Omni Mind. A real personal AI companion / digital being, in the Mega Man Battle Network sense.

- **Goals.** What the Navi is trying to achieve, over days and months, not just one turn.
- **Memory of its operator.** Who Caleb is, what he cares about, what they've built together.
- **Persistent presence.** A continuous being, not a session that starts and ends.
- **The bond.** The relationship between operator and Navi, built over time.
- **NetNavi is a separate future project**, not the name for the Mind layer. The Mind is the memory/thought substrate; the Navi is the being built on it.
- **Depends on:** Omni Mind working (Phases 1–5 at minimum). The proposer loop completing part one (Omni) is what makes the Navi layer possible.

---

## Omni core dependencies (what the Mind needs from Omni)

The Mind is built *on* Omni, not part of it. These Omni-side items gate Mind progress:

- **Three bug fixes** (directions ready, need an implementer):
  - `run` silently passes 0 for args past the third (`~/workspace/omni-run-arg-fix-grok.md`, 155 lines).
  - `compile-wasm` keeps only the first function in any file with an `include` — every program becomes the same 75-byte `std_clamp` module yet prints PASS (`~/workspace/omni-compile-wasm-fix-grok.md`, 157 lines).
  - `--rust` fails a memory-budget check on any single-function file (`~/workspace/omni-rust-single-fn-budget-fix-grok.md`, 173 lines). This one directly blocks the `--rust` cross-check for the Phase 1 store.
- **M3 intrinsics follow-up** (storage + pack5 + req.param) — unblocks Path A persistence and `kv_ledger_service` / `pack5_decision_controller` via `run`. Documented in `~/workspace/omni-counter/omni-m3-code9-followup.md`.
- **Roadmap order:** 7th M3 benchmark → M3 flywheel → proposer loop → Phase 2a syscall intrinsics (literal zero Rust). The no-Rust chain is already proven (m2.elf rebuilds itself byte-for-byte with no Rust process running). The oracle decision — keep Rust as a permanent differential-testing reference, pinned to a toolchain file, vs delete it for literal zero Rust — is still open.
- **Accelerator work** (after P7-3): tensor ops as a host capability with a pure-Omni software fallback; dispatch to the Z13's XDNA NPU (~50 TOPS) via ONNX Runtime; hard guardrail that accelerator math never feeds a gate or a hash.

---

## What "the big codebase" looks like

Not one big program. The codebase is a system of many small verified programs plus the tooling that grows and governs them:

- **The Mind layer:** `memory`, `graph`, `activate`, `learn`, `distill`, `ledger` — plus the `store/` (persistence), the tuner (Mode 6.3), the proposer (CEGIS loop), and the audit view. A growing `std/` library of verified components, mined from experience by Stitch and admitted only through the MDL + soundness gate.
- **The Omni core it stands on:** the compiler, the verifier, the VM, the M3 frontend, the P7 measurement loop, the proposer-loop design. The frozen hashes and gates that keep all of it honest.
- **The scale shape:** millions of small `.omni` programs (memories) held in a content-addressed store, composed into a graph, activated by association, tuned by CMA-ES, distilled by Stitch, proposed by CEGIS, verified by the verifier, summarized by SWUM/AST-W-PDT, and garbage-collected in sleep time. The "big codebase" is the graph and the library, not a single file.

---

*Omni Mind. Memory as programs. Thought as execution. Learning as construction, verification, and gradient-guided search.*
