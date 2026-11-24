# Omni Mind

The Mind layer built on Omni. Memory and thought, unified in a single layer, where memory is not stored as data but encoded as verified Omni programs that run.

Omni is the language — part one. Omni Mind is the mind that lives on top of it — part two of the Omni universe. It is distinct from NetNavi, which is a separate future project.

## The idea in one paragraph

A human does not store a video of the past. Memory is reconstruction from fragments, guided by the present moment. It is associative, not indexed. It is compressed — you keep the gist and the lesson, not every frame. And forgetting is not a failure; it is the compression algorithm that lets you generalize.

Omni Mind takes that seriously. Instead of storing "Caleb prefers his coffee black" as a text string in a database, it stores it as a small, verified Omni program that encodes the preference as behavior. The memory does not sit there waiting to be read. It runs. Activating a memory means executing it. Thinking means running memory-programs and composing them in new ways. Learning means verifying a new program and adding it to the graph. Forgetting means distilling a lesson out of a transcript and retiring what is provably redundant — never losing knowledge, only removing noise.

## First principles

**Memory is reconstruction, not playback.** When you remember something from twenty years ago, you are not replaying a tape. You are rebuilding it from fragments, guided by current context, current beliefs, and current needs. That is why memories shift — and why they are useful. They adapt.

**Memory is associative, not indexed.** You do not look up a memory by an ID. You get there by a smell, a song, a place, a feeling. Memory is a web, not a filing cabinet.

**Memory is compressed.** You do not remember every detail of every day. You remember the gist, the meaning, the emotional weight. Details fade; structure persists. A ninety-year-old remembers the feeling of a moment and the fact that it mattered, not the exact words spoken.

**Forgetting is a feature.** If you remembered everything, you would be paralyzed. Forgetting is how you go from "this specific dog" to "dogs." It is the compression algorithm.

**The goal of memory is not preservation. It is the ability to act well in the future.** A memory that does not help you act better is dead weight.

## What is wrong with how we do memory now

Every current approach treats memory as *storage*, not as a *process*.

- **Context windows** stuff more text into the prompt. Brute force. No compression, no priority, no forgetting. It does not scale, it does not prioritize, and it does not learn.
- **RAG** is a filing cabinet. You retrieve by surface similarity, not by what matters. It does not consolidate, it does not forget, it does not reorganize.
- **Fine-tuning** bakes knowledge into weights. Slow, expensive, and it causes catastrophic forgetting — new learning destroys old learning.
- **Summarization** compresses, but by having a model write prose, which loses structure in an uncontrolled way.

They all assume the goal is to preserve information. It is not. The goal is to act well.

## The architecture

### Memory-programs

Each memory is a small, verified Omni program. A preference, a fact, a skill, a lesson — each one is code, not text. Because it is a program:

- It is **executable**. Activating a memory means running it, not retrieving it.
- It is **verifiable**. The Omni verifier checks that it respects capabilities, taint, ownership, and structure, and that it cannot do anything unauthorized. It does not prove what a program *means* — only that it obeys the rules. That makes it safe to accumulate memory for decades.
- It is **composable**. Memory-programs call each other and combine. Knowledge grows by composition, not just accumulation.
- It does not **degrade**. A program behaves the same way in ninety years as it does today.

### The graph

Memories live in a graph, not a list. Each node is a memory-program. The edges are associations: this relates to that, this caused that, this is an example of that. When the agent is in a situation, it traverses the graph from the current context, following associations, and the relevant memories activate. That is how humans retrieve — by association, not by keyword search.

### Activation

Retrieval is traversal, not lookup. Starting from the current context, the agent follows the strongest associations and runs the programs it reaches. The right memory surfaces at the right time because it is connected to the present moment, not because it matched a query string.

### Consolidation

A background process — the proposer loop, or a dedicated consolidation pass — takes the day's experiences, extracts the reusable patterns, writes them as verified programs, and adds them to the graph. The raw transcript can then be discarded. You keep the lesson, not the recording. That is how you get ninety-year memory: you do not keep every detail, you keep the distilled programs that encode what mattered.

### Forgetting

Forgetting is controlled, not passive. It takes two forms, and neither one loses knowledge:

- **Distillation.** Discard the raw transcript but keep the lesson as a program. You lose the exact words, you keep the fact that Caleb prefers X. That is not forgetting — that is learning.
- **Garbage collection.** A program is removed only if it is provably unused, superseded by a better one, and nothing depends on it. The verifier guarantees safety *within* a single program, but there is no dependency analysis across the graph yet, so removal safety across programs is not yet guaranteed. You do not lose knowledge — you remove redundancy.

## Memory and thought are one layer

There is no separate thought layer. That separation is an artifact of how computers are built — RAM over here, CPU over there — not a fact about minds. A human brain does not have a "memory box" and a "thought box." You think *with* your memories.

In Omni Mind, thinking is running memory-programs and composing them in new ways. The agent activates the relevant programs, runs them, combines the results, and if the combination is new and useful, it gets verified and saved as a new memory-program. That is learning. There is no separate thought engine. The thought is the execution.

Within the one layer, there are different *kinds* of nodes — memory nodes that return facts and preferences, procedure nodes that do reasoning and planning, skill nodes that do things — but they are all programs in the same graph, all verified, all composable. The distinction between "a memory" and "a thought process" is just what the program does, not a separate layer.

## Better than a human brain

Human forgetting is passive and uncontrolled. You lose details, then you lose the gist, then you lose the whole thing, whether you want to or not. That is a limitation, not a design to replicate.

Omni Mind does not decay the way a human brain does:

- **Perfect retention of what matters.** A memory-program that encodes a real lesson, a real preference, a real skill — it stays. Forever. It does not fade. It does not get weaker with age. If anything, it gets stronger: more trusted, more connected, more central to the graph.
- **No catastrophic forgetting.** Learning something new does not overwrite something old. Programs are separate and composable. There is no interference.
- **Exact recall.** Human recall is fuzzy and reconstructive. Omni Mind recall is exact — run the program, get the exact answer. No "I think it was something like..."
- **Cumulative growth.** Over twenty years, knowledge only grows. It never shrinks. The system does not learn, forget, and relearn. It learns and keeps.
- **Unbounded capacity in principle.** A human brain has finite capacity. A memory graph can grow as large as needed, limited by storage, not by a fixed neural substrate.

That is how the agent becomes smarter and more capable than a human brain: a human's ability to learn, plus perfect retention, plus the ability to compose everything it has ever learned into something new.

## Relation to Omni

Omni Mind is built *on* Omni, not part of Omni.

- Omni is the language: the compiler, the VM, the verifier, the ISA, the standard library. It is part one.
- Omni Mind is the Mind layer: the memory graph, the consolidation process, the knowledge representation, the host runtime. It is part two of the Omni universe.
- Omni Mind depends on Omni. It invokes `omnic` to compile and run memory-programs. Omni never depends on Omni Mind.
- Omni Mind is distinct from NetNavi, which is a separate future project.

## Status

Design only. No code yet. This document is the vision. The first code will be the memory graph and the consolidation process.

## Further reading

- [PAPER.md](PAPER.md) — *Omni Mind: Learning by Construction.* The full design paper: why gradient descent is data-hungry, why memory should be programs, why memory and thought are one layer, and how a hybrid of gradient descent and program synthesis makes learning faster and less data-intensive.
