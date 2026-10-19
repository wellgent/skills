# Brain-First Lookup Convention

Before using external search, enrichment APIs, or general model memory for an active page type, named subject, relationship, decision, evidence timeline, or durable fact, check {{brain}}/GBrain first.

## Lookup order

1. Search exact names and aliases: `gbrain search "query"`.
2. Query semantically when keyword search is thin: `gbrain query "question"`.
3. Read the full page when a candidate slug is relevant: `gbrain get <slug>`.
4. Check relationships and recency when they matter.
   - Backlinks/graph: `gbrain graph-query <slug>`.
   - Timeline: `gbrain timeline <slug>`.
5. Only then go external, under the external research standard below.

## External research

Research that leaves the brain meets one standard, whatever tool runs it:

1. The lookup order above comes first.
2. Classify the question: a quick fact, source discovery, deep research, or extraction from a known source.
3. Treat prior research records as leads (sources, questions), never as inherited verdicts: re-test their conclusions against primary sources.
4. Answer from the authoritative page itself (the official docs, the registry entry, the filing), not from a summary of it.
5. Cite the real URL the fact came from.
6. Land a quick fact inline on the page it serves, with its citation. Land deep research as a run record at {{research_records}}, linked from the pages it informs.

The tool route for each class:

{{external_research}}

## Write boundary

The `gbrain` CLI is the brain-local skill surface. For normal durable {{brain}} writes, edit the markdown source directly.

See `skills/conventions/durable-write.md` for the runtime reconciliation boundary.

Durable write loop:

1. Read `RESOLVER.md` before creating or moving pages.
2. Read `schema.md` and relevant templates before shaping page content.
3. Edit existing pages before creating new ones.
4. Cite every durable fact inline.
5. Stage exact paths only.
6. Commit and push.
7. Run this runtime's installed durable-write reconciliation path.
8. Verify with the runtime's approved GBrain read surface, such as `gbrain get`, `gbrain search`, `gbrain query`, `gbrain timeline`, or backlinks.

Do not write directly to the derived database for normal durable updates. Use a direct database write only when the user explicitly asks for it or a recovery path makes source markdown unavailable, then reconcile back to markdown as soon as possible.
