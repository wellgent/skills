---
name: capture
version: 0.2.0-managed-gbrain
description: |
  Simple brain capture workflow for single thoughts, snippets, and inbox notes.
  Writes markdown into the target brain's inbox home through the checkout,
  commits and pushes, and verifies source durability against the brain's write model.
triggers:
  - capture this
  - save this thought
  - remember this
  - ingest this into my brain
  - drop this in the inbox
  - drop this note in the inbox
  - save this note into the brain inbox
  - save to brain
tools:
  - Bash
  - Read
  - Grep
mutating: true
writes_pages:
  - inbox/*
---

# Capture

> **Convention:** See `skills/conventions/durable-write.md` for runtime reconciliation rules.
> **Convention:** See `skills/conventions/brain-routing.md` before capturing into a non-default brain or source.

## Contract

This skill is the simple-save front door for one-off notes.

It guarantees:

- Single thoughts, snippets, and notes can be saved without designing a full page first.
- Captures are markdown-first: the note lands as a file in the checkout, and the derived database follows through the host's reconciliation path.
- Source markdown durability is verified after capture.
- Captures land in the target brain's declared inbox/staging home unless {{owner}} names a specific destination.
- Governed page edits still use `brain-ops`, not capture.

## When To Use

Use this skill for:

- "remember this"
- "capture this thought"
- a single pasted note the owner wants saved
- a small synthesis that should land in an inbox for later filing

Do not use it for:

- bulk imports
- article/media ingestion with metadata
- meeting transcript ingestion
- edits to existing compiled pages
- secrets or credential-bearing text

## Protocol

1. Resolve brain/source context with `skills/conventions/brain-routing.md`.
2. Write the note as a markdown file under the target brain's inbox home (kebab-case filename, frontmatter per the brain's schema and templates).
3. Stage the exact path, commit, and push.
4. Verify source durability: the file exists at the canonical repo path and the push landed on the remote.
5. Database visibility follows the host reconciler; it is eventual, not part of the durability check. A later `gbrain get <slug>` confirms the derived row when needed.

`gbrain capture` is an accepted shortcut only on a runtime that holds a writable local engine for the target brain (the brain host itself). Thin remote clients hold read-only scope; their capture path is the markdown-plus-Git protocol above. When using `gbrain capture` with sensitive content, pass `--stdin` or `--file`, never an inline shell argument.

## Output Format

```text
Captured to `<path>`.
Source durability: <committed and pushed/pending>
Next step: <none or suggested filing review>
```

## Anti-patterns

- Using capture for governed edits to existing pages.
- Capturing secrets through inline shell arguments or into the repo at all.
- Treating derived-database visibility as the durability signal; the committed markdown is the source of truth.
- Looping captures for a batch import.
- Filing everything permanently in inbox without later triage.
