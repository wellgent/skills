# Wellgent Agent Skills

Reusable skills for AI coding agents, by [Wellgent](https://wellgent.ai): the skills we design and run in production, published for anyone to adopt.
The collection grows as our workflow does - `orchestrate` is the first.

Install into a project with the [skills](https://www.skills.sh/) CLI:

```bash
npx skills add wellgent/skills
```

Select specific skills with `-s`:

```bash
npx skills add wellgent/skills -s orchestrate
```

## Skills

- **orchestrate** - run one dev-loop session as the driver: preflight, select, drive one spec end to end, tear down, report.
  Harness-generic: grooming drafts run in fresh subagents of the driving harness; implementation takes run on the executor the project contract names - the harness's native subagents by default, or an external harness via a runner file (`runners/codex.md` ships takes as `codex exec` sessions). Review and every tracker write stay with the driver.

## Conventions these skills assume

`orchestrate` is an **add-on to [mattpocock/skills](https://github.com/mattpocock/skills)**, not a standalone workflow: it drives that set's `to-tickets` (grooming) and `implement` (takes), and rides the triage-label conventions its `setup-matt-pocock-skills` establishes.
Install the mattpocock set into the project first.

The loop's semantics ship with the skill and are read in place - [`dev-loop-protocol.md`](skills/orchestrate/references/dev-loop-protocol.md) - so skill updates carry protocol updates with no per-project reconcile.
Takes always run on the driving harness's native subagent mechanism (Claude Code spawns Claude subagents, Codex its own way); an explicit invocation request may route takes through a runner file instead (`runners/codex.md`).

On top of that, the project carries only what is project-specific:

- a slim declarations contract at `docs/agents/dev-loop.md` - ports, scripts, gate proofs, and any deliberate protocol deviations; on conflict the contract wins. Scaffold it from [`dev-loop-declarations.md`](skills/orchestrate/references/dev-loop-declarations.md)
- tracker mechanics at `docs/agents/issue-tracker.md`, and a project-local `verify` skill for runtime verification (scaffold: [`verify-reference.md`](skills/orchestrate/references/verify-reference.md))
- a GitHub-style issue tracker with labels (`ready-for-agent`, `in-progress`, `needs-human`, `needs-triage`, `needs-info`), sub-issues, and blocking edges

A project missing these can still read the skill as a reference workflow, but the loop's guarantees come from the protocol plus the contract.

## License

[MIT](LICENSE)
