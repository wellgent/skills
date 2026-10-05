# Readiness

Header: `FLOW.md`, stage 1.
The iteration's first spec brief waits until the readiness report is green.

1. **Carry over.** Read the previous iteration's Retro report on its map for watch items and pending trials, and its two merged Audit reports beside its ledger file.
2. **Review every source** in `~/repos/wellgent-skills/source-log.md` against its upstream, in full, and record the version seen and today's date on each.
   - Unchanged: done.
   - A regular update: apply it to the flow repo without asking, reading `writing-for-agents` before any skill edit; commit and push.
   - A major change (a new, replaced or obsolete skill, a new tool in a stage's area): one item in the Readiness round with what changed, the stage it touches, what it adds or replaces, and your recommendation. The client picks adopt, adopt and watch, or skip. A skip is logged in the source log with its reason and raised again only when upstream changes it.
3. **Propagate.** Bring the four targets current by re-running the setup skills under `~/repos/wellgent-skills/setup/`: the flow repo, the driving brain (flow config, card, labels), the project (pins by commit sha, `AGENTS.md`, `docs/agents/dev-loop.md`, `CODING_STANDARDS.md`) and the run host (harnesses and CLIs).
4. **Audit input.** Reuse the closing Audit when `main` has not moved since its scanner row's commit.
   Otherwise, and on a project's first run, run the Audit step of [iteration](iteration.md) Close now and triage its findings the same way.
5. **Pending checks.** A blocking check that is red on `main` stays out of the check command until it is green: list it in the report, and make getting it green and adding it part of the iteration's cleanup spec.
6. **Report.** Post the readiness report from `templates/artifacts/readiness-report.md` as a comment on the map, and append `flow ledger stage readiness <owner>/<repo> <green|red> <comment link>`.

Green means every line of the stage's quality bar holds.
On red, fix what is behind and report again.
