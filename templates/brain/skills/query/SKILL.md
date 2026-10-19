---
name: query
version: 0.5.2-managed-gbrain
description: |
  Answer questions from {{brain}}/GBrain using search, semantic query, page reads,
  backlinks, graph, timelines, and citation propagation.
triggers:
  - what do we know
  - tell me about
  - who is
  - what happened
  - search for
  - look up
  - background on
  - notes on
  - relationship between
  - backlinks or graph question
tools:
  - Bash
  - Read
  - Grep
mutating: false
---

# Query Skill

> **Convention:** See `skills/conventions/brain-first.md` for lookup order.
> **Convention:** See `skills/conventions/brain-routing.md` for brain/source targeting.
> **Convention:** See `skills/conventions/search-modes.md` for active retrieval posture.
> **Convention:** See `skills/conventions/salience-and-recency.md` for current-state versus canonical query choices.
> **Convention:** See `skills/conventions/quality.md` for citation and source-precedence rules.

## Contract

This skill guarantees:

- Answers are grounded in {{brain}}/GBrain content.
- Gaps are explicit.
- Claims cite page slugs, source snippets, or source files.
- Conflicts are surfaced instead of silently resolved.
- User statements outrank compiled truth, which outranks timeline evidence, which outranks external sources.

## Phases

1. Decompose the question into keyword, semantic, page, graph, and timeline lookups.
2. Search exact terms first.
3. Query semantically if search is thin.
4. Read the top relevant full pages only when needed.
5. Use backlinks, graph, and timeline for relationship or recency questions.
6. Synthesize directly with citations.
7. State gaps plainly.

## Primary CLI commands

```bash
gbrain search "query"
gbrain query "question"
gbrain get <slug>
gbrain timeline <slug>
gbrain graph-query <slug> --direction in --depth 2
gbrain orient --since <date>
gbrain ontology <entity>
```

`orient` answers "what happened recently" across the whole brain; `ontology` maps one entity's place in the graph. Reach for them before hand-rolling multi-page timeline or relationship sweeps.

## Output

Keep answers direct. Include citations when they help verify the claim. If the brain lacks evidence, say that instead of filling from general knowledge.

## Anti-patterns

- Answering from general knowledge when {{brain}} has relevant content.
- Hallucinating missing facts.
- Loading large pages when search snippets answer the question.
- Ignoring stale/conflicting source evidence.
- Mutating pages from this read-only skill.
