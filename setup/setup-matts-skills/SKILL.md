---
name: setup-matts-skills
description: Set up Matt Pocock's engineering workflow in a target project - the curated selection from mattpocock/skills via npx skills, the AGENTS.md convention, and the orchestrate driver from this repo on top. This skill is the one place the curated selection is declared.
argument-hint: "<path to target project>"
disable-model-invocation: true
---

# Setup Matt's Skills

Set up a target project to run the spec-driven engineering workflow: the curated selection of Matt Pocock's skills below, the project-skill conventions, and the `orchestrate` driver skill from this repo. Run from a checkout of this repo; the argument is the path to the target project (ask if missing). Idempotent - re-running refreshes the project against the pinned sources.

## The curated set

This list is the stance: the one place the curated `mattpocock/skills` selection is declared. Consumers' private registries and sweeps read it from here; changing the selection is an edit to this list, propagated by the ordinary sweep.

- `ask-matt`
- `code-review`
- `codebase-design`
- `diagnosing-bugs`
- `domain-modeling`
- `grill-me`
- `grill-with-docs`
- `grilling`
- `handoff`
- `implement`
- `improve-codebase-architecture`
- `prototype`
- `research`
- `resolving-merge-conflicts`
- `setup-matt-pocock-skills`
- `tdd`
- `to-spec`
- `to-tickets`
- `triage`
- `wait-what`
- `wayfinder`
- `wizard`
- `writing-for-agents`

## The target convention

Everything installed into the project follows one layout:

- Real skill directories in `<project>/.agents/skills/<name>/`
- Relative symlinks `<project>/.claude/skills/<name>` → `../../.agents/skills/<name>` (Claude Code only scans `.claude/skills/`; Codex auto-discovers `.agents/skills/`)
- `AGENTS.md` is the real instructions file at the project root, with `CLAUDE.md` a symlink to it

## Process

### 1. Explore the target

Before changing anything, look at what is already there:

- `git remote -v` - is it a GitHub repo? (the engineering skills default to GitHub Issues)
- `.agents/skills/` and `.claude/skills/` - what is installed, and are the symlinks correct?
- `skills-lock.json` - what has `npx skills` already installed and from where?
- `AGENTS.md` / `CLAUDE.md` - which exists, which is real, which is a symlink?
- `docs/agents/` - has `/setup-matt-pocock-skills` already been run?

Summarise the gap between this state and the convention above, then proceed.

### 2. Install the curated set

Install exactly the curated set above from `mattpocock/skills`, with `npx skills` run inside the target project, so `skills-lock.json` lands at the project root:

- `npx skills add mattpocock/skills --list` to preview what the repo currently offers
- Check `npx skills add --help` for the current selection flags, then install the curated set (skip skills already present in `skills-lock.json` at the same source)

After installing, verify the layout matches the convention: real directories under `.agents/skills/`, relative symlinks under `.claude/skills/`. Create any missing symlinks yourself:

```bash
ln -s ../../.agents/skills/<name> <project>/.claude/skills/<name>
```

### 3. Align the instructions file

First the file layout - `AGENTS.md` is the real file, `CLAUDE.md` symlinks to it:

- Only `CLAUDE.md` exists as a real file: rename it to `AGENTS.md`, then `ln -s AGENTS.md CLAUDE.md`
- Only `AGENTS.md` exists: add the `CLAUDE.md` symlink
- Both exist as real files: show the user the difference and ask how to merge - never pick for them
- Neither exists: create a minimal `AGENTS.md` describing the project (what it is, how to build/test) and add the symlink

Then the content: merge the two sections from [agents-md-reference.md](./agents-md-reference.md) into the target's `AGENTS.md` - the "Development workflow (Matt's skills)" router and the "Skills management (`npx skills`)" notes. If a section already exists, update it in place rather than appending a duplicate. Leave the project's own sections untouched, and don't rewrite prose the user wrote without flagging it.

### 4. Install the driver and verify-protocol skills

The dev-loop driver is `orchestrate` from this repo, and the shared runtime-verification mechanics are `verify-protocol`; both install and pin exactly like the curated set:

```bash
npx skills add wellgent/skills -s orchestrate -s verify-protocol
```

Both follow the standard layout - real directory in `.agents/skills/`, symlink in `.claude/skills/` (create the symlink if the installer did not).
The driver is harness-generic: the take executor (native subagents vs an external runner such as `codex exec`) is declared in the project's dev-loop contract, not by choosing a different skill.
Updates propagate by explicit `add`/`remove` per delta, never `npx skills update` (open CLI bug #542).

### 5. Scaffold the dev-loop declarations

The loop's protocol ships with the installed skill (`<project>/.agents/skills/orchestrate/references/dev-loop-protocol.md`) and is read in place - never copied into the project. What gets scaffolded is the slim declarations contract: apply the installed `references/dev-loop-declarations.md` - create `docs/agents/dev-loop.md` from its template (port semantics, runtime commands, gate proofs, deviations, resolving the placeholders from the repo), create `.agents/launch.json` (three configurations, off-loop first) with the committed `.claude/launch.json` symlink, merge its tracker-mechanics section into `docs/agents/issue-tracker.md`, create the lifecycle labels, and verify the prerequisites it lists (including the project `verify` skill, scaffolded from the installed `verify-protocol` skill's `verify-reference.md`). Where the target already carries a contract, leave it - the skill defers to it.

For the machine-unique port map prerequisite, claim a free block in whatever port registry the target's machines keep before writing the contract. Takes run on the driving harness's native subagents by default; only when takes will be routed through an external runner by explicit request does the machine need that runner's harness authenticated.

### 6. Hand off the per-repo configuration

The engineering skills need per-repo config (issue tracker, triage labels, domain docs). That is `/setup-matt-pocock-skills`'s job and it is interactive, so do not run it from here. Tell the user to open an agent inside the target project and run it there - unless `docs/agents/` already exists, in which case it has been done. Any dev-loop merges step 5 deferred for missing `docs/agents/` files land right after.

## Report

End with what changed in the target: skills installed (and skipped as already present), instructions-file state, the driver skill installed, dev-loop contract state (created, already present, or deferred merges) with any prerequisite gaps, and whether `/setup-matt-pocock-skills` still needs to run.
