# Omni Mind: Learning by Construction

## A Hybrid of Gradient Descent and Program Synthesis

**Status:** Design paper / thesis. Not results. The ideas are grounded in the Omni language, which is a working system, but the architecture described here is unproven at scale.

---

## Abstract

Current AI learns by gradient descent on massive datasets. That approach works, but it is data-hungry, opaque, and it does not learn the way humans do. This paper proposes a different architecture, built on the Omni language: an agent whose memory is encoded as verified programs that run, whose thought is the execution and composition of those programs, and whose learning is a hybrid of gradient-guided intuition and program synthesis. Gradient descent makes program search tractable by guiding it. Program synthesis makes gradient descent safe and efficient by constraining it to a verified structure. Each fixes the other's core weakness. The result is a system that learns from far less data, retains what it learns perfectly, and improves itself over time.

---

## 1. The Problem

A child learns language from a few million words. A current AI model needs trillions of tokens. A human learns a new concept from one or two examples. A neural network needs thousands.

That gap is not an accident. It is a consequence of the update rule. Gradient descent makes tiny, local adjustments based on a noisy signal. One example moves the weights a fraction of a percent in a direction that might be wrong. You need to see the same pattern thousands of times before it sticks. That is why it needs massive data.

There is also an opacity problem. A trained network is a black box. You cannot inspect what it learned, you cannot verify that it will behave safely, and you cannot reuse its parts. When it learns something new, it risks forgetting something old. When it fails, it gives you a loss value and no explanation of what went wrong.

These are not separate problems. They are all consequences of the same choice: representing knowledge as weights, and updating those weights by gradient descent.

## 2. First Principles: What Learning Actually Requires

Strip learning down to its essentials. It requires four things:

1. **A representation.** A way to encode knowledge and behavior.
2. **An update rule.** A way to improve the representation based on experience.
3. **An evaluation.** A way to tell whether the update helped.
4. **Efficiency.** Learning as much as possible per unit of experience and compute.

Gradient descent is one choice for the update rule. It is a weak one. A stronger update rule — one that understands structure, that can make a large correct jump from a single example, that can explain why something is wrong and not just that it is wrong — would need far less data.

What would that rule look like? It would be one that:

- **Understands structure, not just statistics.** If you show a human one example of a new concept, they can often generalize immediately, because they grasp the underlying rule. Gradient descent cannot do that. It just nudges weights.
- **Can reason about why something is wrong.** A loss value says "this is bad" and nothing about what to fix. A program that fails a test gives you a specific error at a specific place. That is a much richer signal.
- **Can compose and reuse.** Humans learn by building on what they already know. If you already understand addition, learning multiplication is fast. Gradient descent largely starts from scratch each time, or fine-tunes, which is inefficient and causes forgetting.

The thesis of this paper is that the stronger update rule is **program construction, verification, and selection** — not gradient descent alone.

## 3. Memory as Programs

Human memory is not a recording. When you remember something from twenty years ago, you are not replaying a tape. You are reconstructing it from fragments, guided by the present moment. Memory is associative, not indexed. It is compressed — you keep the gist and the lesson, not every frame. And forgetting is not a failure. It is the compression algorithm that lets you generalize from "this specific dog" to "dogs."

Every current approach to AI memory treats it as *storage*, not as a *process*. Context windows stuff more text into the prompt. Retrieval systems are filing cabinets. Fine-tuning bakes knowledge into weights and causes catastrophic forgetting. Summarization compresses by writing prose, which loses structure.

Omni Mind takes a different approach: **memory is encoded as verified Omni programs that run.**

Instead of storing "Caleb prefers his coffee black" as a text string, the system stores it as a small, verified Omni program that encodes the preference as behavior. The memory does not sit there waiting to be read. It runs. Activating a memory means executing it.

Because a memory is a program:

- It is **executable**. Retrieval is execution, not lookup.
- It is **verifiable**. The Omni verifier checks that it respects capabilities, taint, ownership, and structure, and that it cannot do anything unauthorized. It does not prove what a program *means* — only that it obeys the rules. That makes it safe to accumulate memory for decades.
- It is **composable**. Memory-programs call each other and combine. Knowledge grows by composition, not just accumulation.
- It does not **degrade**. A program behaves the same way in ninety years as it does today.

Memories live in a **graph**, not a list. Each node is a memory-program. The edges are associations: this relates to that, this caused that, this is an example of that. When the agent is in a situation, it traverses the graph from the current context, following associations, and the relevant memories activate. That is how humans retrieve — by association, not by keyword search.

## 4. One Layer: Memory and Thought

There is no separate thought layer in Omni Mind. That separation is an artifact of how computers are built — RAM over here, CPU over there — not a fact about minds. A human brain does not have a "memory box" and a "thought box." You think *with* your memories. Reasoning is retrieval plus recombination.

In Omni Mind, thinking is running memory-programs and composing them in new ways. The agent activates the relevant programs, runs them, combines the results, and if the combination is new and useful, it gets verified and saved as a new memory-program. That is learning. There is no separate thought engine. The thought is the execution.

Within the one layer, there are different *kinds* of nodes — memory nodes that return facts and preferences, procedure nodes that do reasoning and planning, skill nodes that do things — but they are all programs in the same graph, all verified, all composable. The distinction between "a memory" and "a thought process" is just what the program does, not a separate layer.

## 5. Forgetting, Done Right

Human forgetting is passive and uncontrolled. You lose details, then you lose the gist, then you lose the whole thing, whether you want to or not. That is a limitation, not a design to replicate.

Omni Mind does not decay the way a human brain does. Memory-programs persist indefinitely, and they get *stronger* with age and use — more trusted, more connected, more central to the graph. A program that has been verified a thousand times and used a hundred times is more reliable than a brand-new one, not less.

Forgetting still exists, but it is controlled, and it takes two forms, neither of which loses knowledge:

- **Distillation.** Discard the raw transcript but keep the lesson as a program. You lose the exact words, you keep the fact that Caleb prefers X. That is not forgetting — that is learning.
- **Garbage collection.** A program is removed only if it is provably unused, superseded by a better one, and nothing depends on it. The verifier guarantees safety *within* a single program, but there is no dependency analysis across the graph yet, so removal safety across programs is not yet guaranteed. You do not lose knowledge — you remove redundancy.

This is how the agent becomes smarter and more capable than a human brain. A human forgets most of what they learn. This system keeps everything that matters, forever, with perfect precision. Learning something new does not overwrite something old. Recall is exact, not fuzzy. And over twenty years, knowledge only grows. It never shrinks.

## 6. The Hybrid: Gradient Descent and Program Synthesis

Program synthesis alone has a problem: search is combinatorially explosive. Searching the space of programs is discrete, and it can blow up. Gradient descent alone has the opposite problem: it is data-hungry, opaque, and unsafe.

The answer is not to choose one. It is to combine them so that each fixes the other's core weakness.

**Gradient descent makes program search tractable.** Pure program search is blind. But if a gradient-trained mind proposes the programs, it has intuition — a sense of which programs are likely to work before they are tried. That prunes the search enormously. The gradient does the "this looks promising" part.

**Program synthesis makes gradient descent safe and efficient.** Pure gradient descent can wander anywhere in weight-space, including into regions that are wrong or unsafe. But if the gradient is tuning parameters inside a program structure — the weights of a network whose architecture is fixed and verified — then it can only explore within a sensible, safe space. The program constrains it.

This is not a compromise. It is a synergy. Each one makes the other easier.

There are three concrete forms the hybrid takes in Omni Mind:

### 6.1 Gradient-guided program search

The proposer — an AI with gradient-trained intuition — proposes a program change. The verifier checks it. The gates measure it. It is adopted or rejected. This is the *shape* of the Omni proposer loop as designed — but in Omni the proposer loop is still design-only (a design document, not implemented code). Making it real, and optimizing how the proposer's intuition improves over time, is the next step.

Program search also has to scale with experience, or it stalls. Even a gradient-trained proposer hits exponential blowup when synthesizing deep logic from scratch. The answer is **library compression** (the DreamCoder pattern): periodically mine frequent subtrees across verified memory-programs and refactor them into reusable `std/` or library nodes. Each promotion shortens the AST depth required for future tasks, so the proposer's search budget buys more as the library grows. Omni already does the beginning of this — the reusable `neuron`, `pid_output`, and `classify_score` helpers in the example programs are library nodes in miniature. Making the mining and promotion systematic is what turns a fixed library into one that grows with the system.

### 6.2 Gradient for perception, programs for reasoning

A gradient-trained model on the accelerator turns raw, fuzzy input — sensor streams, images, messy data — into clean, structured features. Then Omni programs reason over those features, make decisions, and act. The boundary is enforced by the determinism guardrail: accelerator math never feeds a gate or a hash. You get fuzzy perception where you need it, and verified reasoning where it matters, and they never contaminate each other.

The guardrail protects reproducibility, but it does not protect against a wrong perception. If the perception model misclassifies an input, it hands the Omni program a clean-looking wrong feature, and the program deterministically executes the wrong branch. The program is correct — it follows its rules — but the outcome is wrong because the input was wrong. The boundary must therefore carry uncertainty, not just a hard classification. Balanced ternary gives this for free: the perception layer emits a trit, and **0 means "unknown."** When the model is uncertain, it passes 0 across the boundary instead of a confident +1 or −1, and the Omni program branches on it (via `egate` / `if_pos` / `if_neg`) into caution or information-gathering instead of acting on false certainty. Uncertainty is a first-class value in the language, not an afterthought bolted on.

### 6.3 Programs with tunable parameters

A program defines the architecture — the structure, the features, the logic. Gradient descent (or the proposer loop trying values and keeping the ones that measure better) tunes the parameters — the weights, the thresholds, the biases — inside that fixed, verified structure. The network becomes both learnable *and* verifiable. This is the "gradient into program mix" in its most literal form: gradient fills in the numbers, the program provides the shape.

There is a real gap here that must be stated plainly: **gradient descent cannot flow directly through a discrete Omni program.** Pure Omni executes i64 integer arithmetic, integer division, `egate`, and `if_pos`/`if_neg` branches, whose gradients are zero or undefined everywhere. There is no gradient to follow through an Omni AST. Mode 6.3 therefore needs one of two mechanisms. Either a **differentiable shadow graph** is maintained on the accelerator — a continuous relaxation of the program (straight-through estimators or floating-point relaxations) that is trained by gradient descent and then quantized back into verified i64 constants — or the tuning is **derivative-free proposer search**: the proposer loop tries parameter values, measures the result, and adopts or rejects them, with no gradient at all. The shadow graph is true gradient descent; the proposer search is not, but it is simpler and it already exists in Omni's design. Which one is used should be stated explicitly, not left ambiguous.

## 7. Why the Hybrid Is More Data-Efficient

The hybrid needs far less data than pure gradient descent, for three reasons:

1. **Each example is a constraint, not a nudge.** In gradient descent, one example moves the weights a tiny amount in a noisy direction. In program synthesis, one example can eliminate an entire hypothesis. If a program says "classify as fault when temp > 8" and you show it a case where temp is 9 but the system is healthy, that hypothesis is dead. You do not need a thousand more examples to unlearn it.
2. **Errors are informative.** A verifier error tells you the exact location and nature of the problem. A loss value tells you almost nothing about what to fix. Every failure in Omni Mind teaches a specific lesson.
3. **Composition means you do not relearn.** Once you have a verified `neuron` function, you never need to relearn what a neuron is. You just use it. In a neural network, every new task requires retraining the whole network. In Omni Mind, knowledge accumulates in the graph and never degrades.

It is also faster. Verification takes seconds and gives a definitive yes or no. The AI iterates as a programmer, in seconds, instead of waiting hours for a training run to converge.

## 8. Honest Limits

This architecture is a thesis, not a result. The following are real risks and gaps.

**Program search is hard.** It is the central technical risk. Searching the space of programs is discrete and combinatorially explosive. The gradient-guided proposer mitigates it, but it does not solve it. If the search does not scale, the approach stalls.

**Consolidation is underspecified.** "A background process distills experiences into programs" does a lot of work in one sentence. How does it decide what is worth keeping? How does it extract a general lesson from a specific experience? That is itself a learning problem, and it is the least specified part of this design. The mechanism that makes it tractable is **structural anti-unification scored by Minimum Description Length (MDL)**: take multiple episodic traces (concrete program instances), extract their shared AST skeleton into a parameterized function (anti-unification — the least general generalization of the traces), and promote the new abstraction only when it shrinks the total graph size while passing all historical regression fixtures. That is a mechanical, objective criterion — not open-ended summarization. An abstraction is adopted when it provably compresses the graph, and rejected when it does not.

**Not everything is a program.** Some things — recognizing a face, understanding nuance, perceiving the world — are genuinely statistical and fuzzy. They may always be better learned by gradient descent directly. The hybrid addresses this by keeping gradient descent for perception, but the boundary between "fuzzy perception" and "structured reasoning" is not always clean.

**The graph could become unmanageable.** A memory graph with millions of programs raises real questions about traversal efficiency, irrelevant activation, and entanglement. Garbage collection helps, but it is not clear it is sufficient at very large scale.

**It is unproven at scale.** The current paradigm is proven to work at massive scale. This one is not. The programs built so far in Omni are small and structured. Whether this approach scales to human-like intelligence is an open question, and the only way to answer it is to build it.

## 9. Relation to Omni

Omni Mind is built *on* Omni, not part of Omni.

- Omni is the language: the compiler, the VM, the verifier, the ISA, the standard library. It is part one.
- Omni Mind is the Mind layer: the memory graph, the consolidation process, the knowledge representation, the host runtime. It is part two of the Omni universe.
- Omni Mind depends on Omni. It invokes `omnic` to compile and run memory-programs. Omni never depends on Omni Mind.
- Omni Mind is distinct from NetNavi, which is a separate future project.

Omni provides the three things that make this architecture possible: **verifiability** (a memory-program can be checked), **determinism** (a measurement is trustworthy, so selection is reliable), and **composition** (programs can be combined into larger behaviors). Without those, memory-as-programs would not be safe or tractable.

## 10. Status and Next Steps

This is a design paper. No code for Omni Mind exists yet. The Omni language it builds on is a working system with a compiler extensively checked via differential testing and fixed-point checks (not formally proven — there are no mathematical proofs of correctness, only extensive cross-checks), a VM, a proposer loop design, and a growing set of example programs.

The two pieces that will prove or disprove this thesis fastest are:

1. **The memory graph.** A graph of memory-programs that retrieves the right memory by association from a current context.
2. **The consolidation process.** A background job that takes an experience and distills it into a verified program, deciding what is worth keeping and what can be discarded.

If those two work, the thesis starts becoming real. If they do not, the approach stalls, and that failure will itself be informative.

Of the three hybrid modes in §6, **Mode 6.3 is tested first.** The topologies already exist and are verified — `mlp.omni`, `perceptron.omni`, and `agent2.omni` are fixed, budget-verified network structures with clamped weights and thresholds. The search space is just the numeric parameters, which is small, and testing it does not require the full proposer loop (which is still design-only). Mode 6.1 is more important long-term — it is the mode that creates new knowledge — but it needs the proposer loop built first. Mode 6.3 validates the "tunable parameters inside a verified shape" idea now, with what already exists.

---

*Omni Mind. Memory as programs. Thought as execution. Learning as construction, verification, and gradient-guided search.*
