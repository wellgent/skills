---
name: brain-ops
version: 0.5.2-managed-gbrain
description: |
  {{brain}} knowledge-base operations for agents working in this repo. The core read/write cycle:
  brain-first lookup, markdown-first durable writes, source attribution, graph
  hygiene, runtime reconciliation verification, and commit discipline.
triggers:
  - {{brain}} read or write
  - brain lookup
  - citation handling
  - durable memory update
  - active page type or durable-context question
tools:
  - Bash
  - Read
  - Edit
  - Grep
mutating: true
writes_pages: true
writes_to:
{{writes_to}}
---

# Brain Operations

> **Convention:** See `skills/conventions/brain-first.md` for CLI lookup order and durable write boundaries.
> **Convention:** See `skills/conventions/brain-routing.md` before crossing brain/source boundaries.
> **Convention:** See `skills/conventions/durable-write.md` for runtime-specific write reconciliation.
> **Convention:** See `skills/conventions/quality.md` for citation, exact-phrasing, notability, and graph-hygiene rules.
> **Convention:** See `skills/conventions/test-before-bulk.md` before batch writes.
> **Filing rule:** See `skills/_brain-filing-rules.md` before creating or moving pages.

## Contract

This skill guarantees:

- {{brain}}/GBrain is checked before external research or general-memory answers.
- The `gbrain` CLI is the read/search/query surface for brain-local skills.
- Normal durable writes are direct markdown edits, not derived-database writes.
- Root `RESOLVER.md` is read before creating or moving pages.
- `schema.md` and relevant templates shape page content.
- Every durable fact gets an inline source citation.
- User corrections are highest-authority data.
- First-class entity or locally important subject mentions remain graph-recoverable.
- Exact paths are staged, committed, pushed when applicable, reconciled through the runtime's durable-write path, and verified.

## Read flow

1. Search exact names, aliases, and nearby concepts.
2. Query semantically if keyword results are thin.
3. Read the full page for relevant slugs.
4. Check timeline/backlinks/graph when recency or relationships matter.
5. Answer with citations and explicit gaps.

Use the `gbrain` CLI:

```bash
gbrain search "query"
gbrain query "question"
gbrain get <slug>
gbrain timeline <slug>
gbrain graph-query <slug> --direction in
```

## Write flow

1. Search/read existing pages first.
2. Use `brain-taxonomist` for new-page filing decisions, then read root `RESOLVER.md` for page-home agreement.
3. Read `schema.md` and templates for page shape.
4. Edit existing pages before creating new ones.
5. Preserve compiled truth above `<!-- timeline -->` and dated evidence below it.
6. Cite every durable fact inline, using `{{owner}}` when {{owner}} is the source.
7. Keep links/backlinks recoverable without timeline spam.
8. Stage exact paths only.
9. Commit and push.
10. Run this runtime's installed durable-write reconciliation path.
11. Verify with targeted `gbrain` search/get/query/timeline/backlinks reads.

## Log boundary

`log.md` is a coarse repo/update ledger. Append it for repo-scale operations such as schema/resolver/template changes, brain-wide source imports, workflow wiring, or meaningful maintenance passes.

Do not append `log.md` for routine signal captures, ordinary subject facts, task movement, or local ledger imports. Those belong on subject pages, generated ledgers, timelines, the target brain's local task/work system, or the relevant local data layer.

## Anti-patterns

- Answering durable questions without checking {{brain}}/GBrain.
- Using external APIs before the brain-first lookup.
- Using derived-database writes as the default durable write path.
- Creating pages before searching aliases and nearby concepts.
- Writing facts without citations.
- Treating pure backlinks as timeline evidence by default.
- Committing unrelated local/editor/runtime files.
