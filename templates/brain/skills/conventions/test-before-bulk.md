# Test Before Bulk Convention

Never run a batch operation before testing a small sample.

## Process

1. Read the relevant skill first.
2. Get the prompt, command, or logic right.
3. Test on 3-5 representative items.
4. Inspect the actual output.
5. Fix the skill, convention, or routine if the sample is weak.
6. Only then run bulk work with throttling, checkpoints, and a clear stop condition.

## Applies to

- media/article/meeting ingestion batches
- person/company enrichment batches
- citation and frontmatter repair batches
- backfill operations
- first-time cron/Autonomy jobs
- schema migration or refiling batches

## Bulk safety rules

- Prefer `--dry-run`, `--test`, or read-only modes when available.
- Commit in small exact-path batches when source files change.
- Keep generated output reviewable.
- Stop on pattern-level quality problems instead of cleaning later.

## Anti-patterns

- Writing a one-off shell script when a skill exists.
- Running a big import without reading sample output.
- Treating "we can clean it later" as a plan.
- Committing hundreds of generated changes in one opaque batch.
