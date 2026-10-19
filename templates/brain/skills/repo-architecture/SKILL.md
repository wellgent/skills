---
name: repo-architecture
version: 0.5.1-managed-gbrain
description: |
  {{brain}} filing decisions: where new brain files go, when to update existing
  pages, and how to keep source-of-truth markdown, citations, links, and
  templates aligned.
triggers:
  - repo boundary
  - resolver structure
  - filing rules
  - template layout
  - support file boundary
  - support file
  - root resolver
  - schema agreement
  - generated asset boundary
  - generated assets
tools:
  - Bash
  - Read
  - Grep
mutating: false
---

# Repo Architecture

> **Filing rule:** Root `RESOLVER.md` is authoritative for {{brain}} filing. This local copy delegates to it.
> **Filing gate:** Use `skills/brain-taxonomist/SKILL.md` for new-page path/type recommendations from the active schema pack.
> **Convention:** See `skills/_brain-filing-rules.md` for the active directory map.
> **Convention:** See `skills/conventions/schema-evolution.md` before proposing schema-pack changes.
> **Convention:** See `skills/conventions/quality.md` for notability and graph hygiene.

## Contract

This skill guarantees:

- New pages are filed by primary subject and active schema-pack type.
- Existing pages are updated before new pages are created.
- Root `RESOLVER.md` is read before creating or moving pages.
- `schema.md` and templates control page shape.
- Ambiguous placements are named instead of guessed.

## Protocol

1. Identify the primary subject: what would future {{owner}} search for?
2. Search exact names, aliases, and nearby concepts.
3. For new pages, consult `brain-taxonomist` to match the active schema pack.
4. Read root `RESOLVER.md`.
5. If page shape matters, read `schema.md` and the relevant template.
6. Pick the active home from root `RESOLVER.md`; use `skills/_brain-filing-rules.md` only as a compact support map.
7. If no active home fits, use `schema-evolution.md` and ask before activating new schema/directory behavior.
8. Preserve deterministic links and citations.

## Output

Advisory format:

```text
File/update this at `<path>` because the primary subject is <reason>. Read/update <existing pages> first.
```

## Anti-patterns

- Filing by file format or source channel.
- Creating a page before searching.
- Using the local raw/provenance home for compiled subject knowledge.
- Treating deferred directories as active without an explicit resolver change.
