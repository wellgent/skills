# Readiness

Header: `FLOW.md`, stage 1.
The iteration's first spec brief waits until the readiness report is green.

1. **Carry over.** Read the previous iteration's Retro report on its map for watch items and pending trials, and its two merged Audit reports beside its ledger file.
2. **Review every source** in `~/repos/wellgent-skills/source-log.md` against its upstream, in full, and record the version seen and today's date on each.
   `flow sources` prints each source as `same`, `changed`, `read` (a page you read yourself) or `unknown` (an upstream this host cannot reach: check it by hand).
   For a `changed` source read what changed between the two versions: release notes, or the diff of the skills the flow pins.
   - Unchanged: `flow sources seen --unchanged` stamps them all.
   - A regular update: apply it to the flow repo without asking, reading `writing-for-agents` before any skill edit, then `flow sources seen <name>`, which also moves a skill source's pin; commit and push.
   - A major change (a new, replaced or obsolete skill, a new tool in a stage's area): one item in the Readiness round with what changed, the stage it touches, what it adds or replaces, and your recommendation. The client picks adopt, adopt and watch, or skip. A skip is logged in the source log with its reason and raised again only when upstream changes it.
3. **Propagate.** `flow ready <owner>/<repo>` checks the four targets: the flow repo, the driving brain (flow config, card, labels, the lead's pins), the project (pins at the source log's commits, `AGENTS.md`, `docs/agents/dev-loop.md`, `CODING_STANDARDS.md`) and the run host (harnesses, CLIs, folder trust).
   For each `behind` line re-run the setup skill that owns it, read as a file: `~/repos/wellgent-skills/setup/setup-brain/SKILL.md` for `brain` and `host`, `setup/setup-project/SKILL.md` for `project`.
   Propagation is done when `flow ready <owner>/<repo>` exits 0.
4. **Audit input.** Reuse the closing Audit when `main` has not moved since its scanner row's commit.
   Otherwise, and on a project's first run, run the Audit step of [iteration](iteration.md) Close now and triage its findings the same way.
5. **Pending checks.** A blocking check that is red on `main` stays out of the check command until it is green: list it in the report, and make getting it green and adding it part of the iteration's cleanup spec.
6. **Report.** Post the readiness report from `templates/artifacts/readiness-report.md` as a comment on the map, and append `flow ledger stage readiness <owner>/<repo> <green|red> <comment link>`.

Green means every line of the stage's quality bar holds.
On red, fix what is behind and report again.
