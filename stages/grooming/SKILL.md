---
name: grooming
description: The grooming step of the development flow's Plan stage - one spec cut into a ticket graph with to-tickets.
disable-model-invocation: true
---

# Grooming

The step `grooming` inside the Plan stage:

- **Role:** lead writes the spec; groomer cuts tickets (step `grooming`).
- **Runs:** per spec.
- **Input:** the spec brief, UX notes, design record.
- **Output:** the spec and its ticket graph.
- **Quality bar:** the lead approves the ticket graph; every contract example and every UX state is covered by a ticket; blocking edges serialize work that cannot run in parallel.
- **Tools:** `to-spec`, `to-tickets`.

You are the **groomer** for the spec named in your start prompt.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.

`to-tickets` is pinned in the project; read its `SKILL.md` from the project's skills directory and follow it as written, with its templates unchanged.
This skill adds only what the flow needs on top.

## Steps

1. **Read the input.**
   The spec is the body of the target issue.
   Read the UX notes and the design record it links, in full.

2. **Run `to-tickets` on the spec**, with these additions:
   - **Contract examples.** Each ticket's acceptance criteria name the contract examples it implements, each as the operation and the example with its literal values copied from the design record. Every example in the record is named by exactly one ticket.
   - **UX states.** Every flow, state and string in the UX notes is delivered by a ticket.
   - **Blocking edges.** Build runs every unblocked ticket at once, each in its own worktree. Two tickets that change the same module, schema or shared file get a blocking edge between them, so the graph alone keeps them apart.
   - **The quiz.** The lead is the user `to-tickets` quizzes. Post the proposed breakdown as one comment on the spec issue, send its link with `flow ask`, and wait for the reply. Revise and ask again until the lead approves.
   - **Publishing.** Tickets are sub-issues of the spec with native blocking edges, per the project's tracker doc.

3. **Check the graph as published.**
   List every contract example and every UX state against the ticket that covers it, and fix any gap.
   Done when the list has no uncovered line and every ticket names its examples.

4. **Report.**
   End the session with `flow report done <link to the spec issue>`.
