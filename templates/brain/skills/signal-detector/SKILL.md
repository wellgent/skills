---
name: signal-detector
version: 0.5.1-managed-gbrain
description: |
  Non-blocking ambient signal capture for incoming user messages while an agent is working in {{brain}}.
  Detects original thinking, active-subject mentions, durable facts, follow-ups,
  decisions, and writes useful signals into {{brain}} through the markdown-first
  source-of-truth loop.
triggers:
  - every incoming user message with durable signal
  - ambient signal capture
  - original thinking
  - active subject mention
  - follow-up or durable decision
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

# Signal Detector

> **Convention:** See `skills/conventions/model-routing.md` for thinking-effort guidance.
> **Convention:** See `skills/conventions/quality.md` for exact-phrasing, citation, notability, and graph-hygiene rules.
> **Filing rule:** See `skills/_brain-filing-rules.md` before creating or moving pages.

## Contract

On incoming user messages, scan for durable signal without blocking the main work.

Capture:

- Original thinking: phrases, metaphors, frames, theses, taste judgments, strategic lenses, predictions, or operating principles.
- Durable facts: decisions, follow-ups, relationships, timeline evidence, commitments, preferences, constraints, or changed current truth.
- Active subjects: named people, organizations, workstreams, records, concepts, sources, or other page types declared by the local resolver.

Skip:

- Pure acknowledgments.
- Purely operational commands.
- Duplicate material already captured.
- Unsafe/private material that should not be retained.
- Messages from contexts not authorized for {{brain}} writes.

## Model

Signal detection writes to the brain, so it runs at high effort per `skills/conventions/model-routing.md`, whatever effort the main work runs at.
The brain-first lookup is part of every scan; a scan that answers from memory has skipped it.

If the current environment cannot run signal detection in the background, keep the scan minimal and do not derail the main task.

## Detect

Original thinking is at least as valuable as entity extraction. If the user's wording is the artifact, preserve it exactly.

{{local}}

For each candidate signal:

1. Search {{brain}}/GBrain for existing pages and aliases with `gbrain search`.
2. Read the likely page before writing.
3. Decide the primary subject through root `RESOLVER.md`.
4. Update existing pages before creating new pages.
5. Create only when the notability gate passes.
6. Cite according to `skills/conventions/quality.md`; when the source is the current user and the {{brain}} context identifies that user as {{owner}}, use `[Source: {{owner}}, {context}, YYYY-MM-DD]`.

## File

Use root `RESOLVER.md` and `skills/_brain-filing-rules.md` for placement. Do not maintain a separate directory list in this skill.

Do not update `log.md` for routine captures.

## Write loop

When the detector writes:

1. Edit markdown source directly.
2. Stage exact paths only.
3. Commit and push one coherent change.
4. Run this runtime's installed durable-write reconciliation path.
5. Verify retrieval with targeted search/get/query/timeline/backlinks.

Suggested commit message: `brain: capture conversation signal` or a more specific `<domain>: <short description>`.

## Output

No visible user output by default. If invoked directly, end with one concise internal summary:

```text
Signals: <n> ideas, <n> entities, <n> facts (<action summary or skipped reason>)
```

## Anti-patterns

- Blocking the main task.
- Asking {{owner}} to approve every routine capture.
- Paraphrasing away exact phrasing.
- Creating pages for one-off low-signal mentions.
- Writing facts without citations.
- Updating `log.md` for normal captures.
- Duplicating resolver directory lists inside this skill.
