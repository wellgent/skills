# AGENTS.md reference sections

The two sections below are what this workflow contributes to a target project's `AGENTS.md`. Merge them in during step 3 of the skill: if a section already exists, update it in place rather than appending a duplicate; keep the project's own sections (deployment, env wiring, stack notes) untouched around them.

Project-specific sections written by other skills stay out of scope here - in particular `## Agent skills` (issue tracker, triage labels, domain docs), which `/setup-matt-pocock-skills` writes when run inside the project.

---

## Development workflow (Matt's skills)

`ask-matt` is the router: it maps an intent to the right skill. Prefer these over ad-hoc approaches for the work they cover:

- **Plan / triage** - `to-spec`, `to-tickets`, `triage`, `grilling`, `grill-with-docs`
- **Build** - `tdd` (red-green-refactor), `implement`, `prototype`
- **Understand / design** - `wayfinder`, `codebase-design`, `domain-modeling`, `improve-codebase-architecture`, `research`
- **Debug** - `diagnosing-bugs`
- **Review / merge / handoff** - `code-review`, `resolving-merge-conflicts`, `handoff`
- **Verify at runtime** - `next-dev-loop` is the dev-time verification flow: confirm a change works in the running `next dev` (its `/_next/mcp` view plus `agent-browser`'s browser view), launched and driven per the repo's `verify` skill.
- **Dev loop** - `orchestrate` (drive specs end to end per the skill's shipped protocol and the repo's dev-loop declarations: groom via a fresh subagent, deliver via fresh native-subagent take sessions in their own worktrees, gate yourself; push only on green).
- **Where things live** - project rules an agent consults are docs: `docs/agents/dev-loop.md` (the dev-loop contract), `issue-tracker.md`, `triage-labels.md`, `domain.md`, and this file; procedures an agent runs are skills under `.agents/skills/`; pinned skills and files marked managed are vendor-owned and replaced on update, never edited here - the project-owned `verify` skill carries one such file, its `protocol.md`.
- **Outside the loop** - a session that is not the orchestrator (manual or agent-driven) runs dev servers on the dev-loop contract's off-loop port; for work alongside a possibly-live loop session it takes its own worktree rather than the main checkout, and it never pushes commits it did not author.
- **Landing** - `main` history stays linear. Commit on `main` or on a branch or worktree; a branch lands by rebasing onto `origin/main`, fast-forwarding (`git merge --ff-only`), and pushing. No merge commits (`--no-ff`, the GitHub merge button, a `git pull` without `--rebase`), no pull requests unless the operator asks for one, no squash by default.

## Skills management (`npx skills`)

Skills are installed and version-pinned by the [`skills` CLI](https://github.com/vercel-labs/skills). `skills-lock.json` records each skill's source repo and content hash; real files live in `.agents/skills/`, symlinked into `.claude/skills/`. The `orchestrate` driver comes from wellgent/skills through the same mechanism.

- `npx skills add|remove|update|list` - manage skills (after `remove`, confirm the entry is also gone from `skills-lock.json`).
- `add`/`update` may write real dirs into `.claude/` (or a stray `agent/`) instead of the `.agents/`+symlink layout - normalize after installing.
- `npx skills experimental_install` - restore skills from `skills-lock.json` (e.g. after a clone).
- `setup-matt-pocock-skills` is a config scaffolder (issue tracker, triage labels, domain docs), not the installer.
