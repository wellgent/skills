# Wellgent Agent Skills

Reusable skills for AI coding agents, by [Wellgent](https://wellgent.ai).

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

`orchestrate` drives a spec-based dev loop and expects the project to carry:

- a dev-loop state contract at `docs/agents/dev-loop.md` and tracker mechanics at `docs/agents/issue-tracker.md` - the contract is authoritative; the skill is the driver's procedure on top of it. The contract's implementer section names the take executor (`Takes: native subagents` or `Takes: codex exec`)
- an engineering skill set providing `to-tickets` and `implement` (for example [mattpocock/skills](https://github.com/mattpocock/skills))
- a GitHub-style issue tracker with labels (`ready-for-agent`, `in-progress`, `needs-human`, `needs-triage`, `needs-info`), sub-issues, and blocking edges

A project missing these can still read the skill as a reference workflow, but the loop's guarantees come from the contract documents.

## License

[MIT](LICENSE)
