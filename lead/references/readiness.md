# Readiness

Header: `FLOW.md`, stage 1.
Readiness runs at every lead session start, before the argument is taken.
Its report is the session start report.

1. **Carry over.** Read the latest Audit report and Retro report beside the ledger (`ledger/<repo>/`) when they exist: the Retro's watch items, the Audit's notable problems still open.
2. **Review every source** in `~/repos/wellgent-skills/source-log.md` against its upstream, in full, and record the version seen and today's date on each.
   `flow sources` prints each source as `same`, `changed`, `read` (a page you read yourself) or `unknown` (an upstream this host cannot reach: check it by hand).
   For a `changed` source read what changed between the two versions: release notes, or the diff of the skills the flow pins.
   - Unchanged: `flow sources seen --unchanged` stamps them all.
   - A regular update: apply it to the flow repo without asking, reading `writing-for-agents` before any skill edit, then `flow sources seen <name>`, which also moves a skill source's pin; commit and push.
   - A major change (a new, replaced or obsolete skill, a new tool in a stage's area): one question in a [request](rounds.md) with what changed, the stage it touches, what it adds or replaces, and your recommendation. The client picks adopt, adopt and watch, or skip. A skip is logged in the source log with its reason and raised again only when upstream changes it.
3. **Propagate.** `flow ready <owner>/<repo>` checks the four targets: the flow repo, the driving brain (flow config, card, labels, the lead's pins), the project (pins at the source log's commits, `AGENTS.md`, `docs/agents/dev-loop.md`, `CODING_STANDARDS.md`) and the run host (harnesses, CLIs, folder trust).
   For each `behind` line re-run the setup skill that owns it, read as a file: `~/repos/wellgent-skills/setup/setup-brain/SKILL.md` for `brain` and `host`, `setup/setup-project/SKILL.md` for `project`.
   Propagation is done when `flow ready <owner>/<repo>` exits 0.
4. **Usage and load.** Count the sessions the planned work spawns in parallel.
   Read the usage headroom of both harnesses on this host (`/usage` in Claude Code, `/status` in Codex, each in a scratch tab when this session runs the other harness) and the host's load average against the parallelism.
   Headroom short of the planned sessions before the next reset, or load already at the parallelism: plan fewer parallel steps and say so in the report.
5. **Pending checks.** A blocking check that is red on `main` stays out of the check command until it is green: list it in the report with the ticket that gets it green.
6. **Advise.** One line, `none` or an Audit or a Retro with the number behind it, from `flow ledger rollup <owner>/<repo>`: the health check trend over the window moving the wrong way, an escaped defect in authorization, money or data integrity (a `bug` row with an area since the last Retro row), a project with no Audit report, or many landings since the last Retro row.
   The client starts the flow or does not; nothing reminds after this line.
   An audit or retro lead session writes `none`.
7. **Report.** Print the readiness report from `templates/artifacts/readiness-report.md` in this session, append `flow ledger stage readiness <owner>/<repo> <green|red> [<comment link>]`, and post it as a comment on the map when the session works one.

Green means every line of the stage's quality bar holds.
On red, fix what is behind and report again; the first spawn waits for green.
