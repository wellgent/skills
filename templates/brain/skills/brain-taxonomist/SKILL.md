---
name: brain-taxonomist
version: 0.1.0-managed-gbrain
description: |
  Schema-pack-aware filing gate for new brain pages. Reads the active
  GBrain schema pack instead of hardcoding directory tables, then recommends
  the correct source path and page type before writes happen.
triggers:
  - where does this brain page go
  - file this in the brain
  - brain taxonomist
  - taxonomy check
  - refile brain page
  - create brain page
  - where should this new brain page go
  - where should this brain page go
  - recommend path for new brain page
  - which directory does this page go
tools:
  - Bash
  - Read
  - Grep
mutating: false
---

# Brain Taxonomist

> **Convention:** See `skills/conventions/schema-evolution.md` before proposing schema-pack changes.
> **Convention:** See `skills/_brain-filing-rules.md` and root `RESOLVER.md` for local filing prose.

## Contract

This skill determines where a new {{brain}} page belongs before an agent writes it.

It guarantees:

- New-page filing is checked against the active schema pack, not a hardcoded directory table.
- The recommendation names the matched page type, path prefix, and reasoning.
- Ambiguous cases are surfaced to {{owner}} instead of silently guessed.
- Missing schema coverage is reported as a schema-evolution question, not papered over with the closest type.
- Existing pages are updated in place when they already cover the subject.

## When To Use

Consult this skill before:

- creating any new brain page
- moving/refiling a brain page
- starting a bulk import that will create pages
- choosing between two plausible page homes

Do not use it for:

- appending to an existing page
- adding timeline evidence to an existing page
- ordinary citation or frontmatter repair on an existing path

## Protocol

1. Identify the primary subject: what future {{owner}} search would expect to find.
2. Search for an existing page first.
3. Read root `RESOLVER.md`, `schema.md`, and `skills/_brain-filing-rules.md`.
4. Inspect the active schema pack:

```bash
gbrain schema show --json
```

If the runtime supports per-repo/source flags, pass the active repo/source explicitly.

5. Match the primary subject to an active `page_types[]` entry and its canonical `path_prefixes[]`.
6. If multiple types fit, prefer the most specific active type whose prefix and semantics match the content.
7. If no type fits, stop and report the schema gap using `skills/conventions/schema-evolution.md`.
8. Recommend the path, but let `repo-architecture` and `brain-ops` handle the actual write flow.

## Output Format

```text
File/update this at `<path>`.
Reasoning:
- Primary subject: <person/company/concept/project/source/etc.>
- Matched page type: <type>
- Canonical prefix: <prefix>
- Existing pages checked: <slugs or none>
- Confidence: <high/medium/low>
```

If no schema type fits:

```text
No active schema-pack type cleanly fits this content.
Suggested next step: treat this as a schema-evolution question before creating a page.
```

## Anti-patterns

- Keeping a local directory table inside this skill.
- Creating a new page before searching existing aliases.
- Treating a support/provenance/raw-import directory as compiled subject knowledge.
- Using a deferred directory unless root `RESOLVER.md` says it is active.
- Auto-applying schema-pack changes to make a single file fit.
