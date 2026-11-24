# Omni-Mind Foundation

**Version:** 0.2 (ternary adaptation)  
**Date:** 2026-11-24  
**Substrate:** Omni (pure-default, 236-line classified seed, verifier + P7 flywheel live)  
**Status:** Design foundation — no implementation yet

---

## 0. Purpose

Omni-Mind is the memory-and-thought layer that lives on Omni.

A memory is not a stored string, vector, or document.  
A memory is a small, verified Omni program.  
Activating a memory means executing it.  
Thinking means composing memory-programs.  
Learning means verifying a new program and adding it to the graph.  
Forgetting means distilling a lesson and retiring what is redundant.

**Every judgment in Omni-Mind is a balanced ternary trit.** There are three values, and only three: `+1`, `0`, and `-1`. The `0` is not an error, not a default, and not indecision — it is a first-class value meaning "unknown." A memory can be strong (`+1`), unproven (`0`), or weak (`-1`). An association can support (`+1`), be unknown (`0`), or contradict (`-1`). A perception can be confident (`+1`), uncertain (`0`), or wrong (`-1`). The system never forces a binary choice when it genuinely does not know. That honesty is what makes it trustworthy.

This document defines the minimal foundation required to make that real without breaking Omni's locks.

---

## 1. Non-Negotiable Constraints (inherited from Omni)

1. Every memory-program must pass the pure verifier (capability, linear ownership, taint) before it can be stored or executed.
2. Composition and retrieval must stay inside current pure limits (iterative only, SSA/label caps, no recursion in core modules) or be explicitly outlined into shallow helpers.
3. Adopt / reject / distill decisions use the existing P7 judge (`+1t` / `0t` / `-1t`) and measurement gates. No silent commits.
4. The trusted computing base remains the pure verifier. Omni-Mind code is untrusted relative to it.
5. No new opcodes. No renumbering. Stage-0 seed stays minimal.
6. Machine-readable `error[<CODE>]` with spans on every rejection.
7. **All confidence, strength, and association values are trits.** Wherever the system expresses a judgment — how strong a memory is, how much an edge supports a traversal, how confident an activation is — it is a balanced ternary value (`+1` / `0` / `-1`). There are no booleans and no continuous confidence scores in the Mind layer. A `0` (unknown) is a legitimate value that triggers information-gathering, not a failure.

---

## 2. Core Model

### 2.1 Memory
A memory is a triple:

- `id` — stable content hash of the verified `.omni_bc`
- `program` — the verified token stream (or source that lowers to it)
- `meta` — capability summary, taint summary, measured cost (words, steps, arena), a short deterministic gist, and a **ternary strength trit** (`+1` = strong / trusted, `0` = unproven / uncertain, `-1` = weak / deprecated)

Memories are immutable once verified. Updates create new memories. Strength is not part of the immutable program — it is metadata that changes as the memory proves itself or misleads. A memory that is used successfully and verified repeatedly strengthens toward `+1`. A memory that produces a wrong result or contradicts a trusted memory weakens toward `-1`. A new memory starts at `0` (unproven) and must earn its strength.

### 2.2 Graph
Memories form a directed graph:

- Nodes = memories
- Edges = typed relations (`triggers`, `requires`, `refines`, `contradicts`, `distilled-from`)
- Each edge carries a **ternary weight** (`+1` = strong / supporting, `0` = weak / unknown, `-1` = contradictory / inhibiting)
- Edges are themselves small verified facts (or pure data with verifier-checked labels)

Retrieval is associative traversal, not key lookup. A cue (another memory or a small probe program) walks the graph under a fuel budget. The walk respects edge weights: it follows `+1` edges preferentially, avoids `-1` edges (they are contradictions, not paths), and treats `0` edges as "explore if fuel allows" — a weak association is worth following only when there is budget to spare. A `contradicts` edge is always `-1`; a `triggers` edge is `+1` when the trigger is reliable and `0` when it is speculative.

### 2.3 Activation
Activating a memory = running its program on the pure VM (or native ELF) with:
- the current context as input,
- a fuel / step ceiling,
- the capability set narrowed via `cap_narrow` to only what that memory needs.

The result is a new value **plus a ternary confidence trit**. The memory returns both what it computed and how confident it is in the result: `+1` = confident (act on it), `0` = uncertain (gather more information before acting), `-1` = contradicts the context (do not trust it). The caller branches on the trit via `egate` / `if_pos` / `if_neg` — it never acts on a `0` as if it were a `+1`, and it never ignores a `-1`. A memory that returns `0` is not failing; it is honestly reporting that it does not know, and that honesty is what lets the caller decide to seek more evidence instead of acting on false certainty.

### 2.4 Learning
Learning is the only mutation:

1. Propose a candidate program (hand-written, composed, or emitted).
2. Verify it (pure verifier). Reject on any error.
3. Measure it (P7 metrics).
4. Judge against existing related memories (`+1t` adopt, `0t` hold, `-1t` reject).
5. On adopt: insert node + edges, record in the ledger.
6. On reject: discard, optionally emit a structured repair hint.

The `0t` (hold) verdict is a legitimate third state, not indecision. It means "insufficient evidence to adopt or reject." A held candidate stays in a ternary limbo — it is not adopted, not rejected, and can be re-judged when more evidence arrives. The system does not force a binary adopt/reject when the evidence does not support one.

### 2.5 Forgetting / Distillation
Forgetting is compression, not deletion of knowledge:

- A distill step proposes a smaller program that preserves measured behavior on a golden set.
- If the distilled form measures `+1t` or `0t` on the golden set and is strictly smaller, the original can be retired (edge marked `distilled-from`, original removed from hot set).
- Knowledge is not lost; the lesson remains as the distilled program.

The decision to retire is itself ternary: `+1` = retire (the distilled form is strictly better), `0` = keep both (the distilled form is equivalent but the original has value as a variant or a fallback), `-1` = do not retire (the distilled form is worse). A `distilled-from` edge carries the verdict: it is `+1` when the original is fully superseded, `0` when the original is kept as a variant.

---

## 3. Minimal Foundation Scope (v0.1)

Build only this:

1. **Memory record format** (pure Omni struct / arena layout)  
   id, bc bytes, cap mask, taint summary, cost triple, gist hash, **strength trit**.

2. **In-memory graph** (arena-backed, iterative)  
   add node, add typed **trit-weighted** edge, bounded walk from a cue that respects edge weights (`+1` follow, `-1` avoid, `0` explore if fuel allows).

3. **Activate**  
   `activate(id, context) -> (result, confidence_trit)` that loads, narrows caps, runs under fuel limit, and returns the value plus a ternary confidence.

4. **Learn**  
   `learn(candidate_source) -> adopt | hold | reject` that runs verify → measure → judge → insert. The `hold` (`0t`) outcome is a first-class result, not an error.

5. **Distill stub**  
   `distill(id, golden_set) -> smaller_id | keep_both | reject` using the existing judge. The ternary verdict decides whether the original is retired, kept as a variant, or the distillation is refused.

6. **Ledger**  
   Append-only record of adopt / hold / reject / distill decisions with the trit verdict and hashes. The ledger is a ternary decision log, not a binary pass/fail log.

No persistence beyond a single process yet. No distribution. No numeric training. No natural-language interface.

---

## 4. Suggested Module Layout (pure Omni)

```
mind/
  memory.omni       // record format + hash + strength trit
  graph.omni        // arena graph + trit-weighted bounded walk
  activate.omni     // load + cap_narrow + run + confidence trit
  learn.omni        // verify + measure + judge + insert
  distill.omni      // propose smaller + judge (ternary retire)
  ledger.omni       // append-only ternary decision log
  mind_main.omni    // public entry points
```

All iterative. All includable. All must pass m2-lint and participate in pure fixed-point checks when they touch the compiler.

All Mind modules use the ternary decision primitives (`egate`, `std_trit_mux`, `if_pos` / `if_neg`, `<=>`) rather than binary branches. The foundation is `std/trit.omni` — the ternary decision algebra is the language the Mind layer thinks in.

---

## 5. First Goldens

- `memory_roundtrip_golden.omni` — create, hash, retrieve by id
- `graph_walk_golden.omni` — cue walks to expected node under fuel limit
- `graph_trit_walk_golden.omni` — cue follows `+1` edges, avoids `-1` edges, and explores `0` edges only when fuel allows; a walk that would follow a `-1` edge is refused
- `activate_golden.omni` — known memory runs and returns expected value
- `activate_confidence_golden.omni` — a memory that is uncertain returns `0` confidence, and the caller gathers more information instead of acting
- `learn_adopt_golden.omni` — candidate that measures `+1t` is inserted
- `learn_hold_golden.omni` — candidate that measures `0t` is held (not adopted, not rejected) and can be re-judged
- `learn_reject_golden.omni` — candidate that fails verifier or measures `-1t` is refused
- `distill_golden.omni` — smaller equivalent is accepted, original retired
- Negative: missing cap, taint leak, fuel exhaustion, graph cycle under budget, activation that returns `-1` confidence is not acted on

---

## 6. Integration with Existing Omni

- Use pure M3/M2/M4 for every compile and run.
- Use `cap_narrow` before every activation.
- Use P7 `judge_better` / `p7-measure` for adopt/reject.
- Use existing error contract for all rejections.
- Do not modify the pure verifier or the 236-line seed for v0.1.
- All Mind decisions go through ternary judgments, not binary booleans. Wherever a module must choose, it produces a trit (`+1` / `0` / `-1`) and the caller branches on it.

---

## 7. Explicit Non-Goals (v0.1)

- Persistent storage
- Distributed graph
- Natural-language front end
- GPU / NPU training
- Automatic program synthesis beyond what the existing reflective host already allows
- Raising SSA/label caps
- Any change to the trusted verifier
- Continuous confidence scores in the Mind layer (all confidence is ternary)

---

## 8. Success Criteria for the Foundation

The foundation is real when:

- A pure Omni program can create three memories, link them, activate one from a cue, learn a fourth that measures `+1t`, and distill one into a smaller form.
- All of the above is differentially locked (pure path, 0-diff where it touches compiler seeds).
- Every rejection produces a machine-readable error with a span.
- The classified seed remains 236 lines.
- `p7-measure` / `p7-canary` still pass with 0 regressions.
- **Every judgment in the system is a trit, and `0` (unknown) is used as a legitimate value.** A walk respects edge weights. An activation returns a confidence trit. A hold (`0t`) is a real outcome. No decision in the Mind layer is forced into a binary when the evidence supports a third value.

---

## 9. Immediate Next Step

Implement `memory.omni` + `graph.omni` + one golden that creates two memories and walks from one to the other.  
Nothing else.  
That single vertical slice proves the model can exist inside the current pure pipeline.

The golden should demonstrate ternary edge weights: a walk that follows a `+1` edge to the expected node, refuses to follow a `-1` edge, and treats a `0` edge as "explore if fuel allows."

---

**End of foundation.**  
This is the smallest complete shape that makes "memory is a verified program that runs" true on top of today's Omni without compromising its locks — and every judgment in it is a balanced ternary trit.
