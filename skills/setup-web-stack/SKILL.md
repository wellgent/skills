---
name: setup-web-stack
description: Equip a target web project from a curated catalog of community skills, tooling, and known-good configs - two routes, decided by whether the target exists yet: scaffold greenfield from the defaults reference, or read an existing project and install just what fits it.
argument-hint: "<path to target project>"
disable-model-invocation: true
---

# Setup Web Stack

Equip a target project with the web-stack skills and tooling that actually fit it. [catalog.md](./catalog.md) is the directory - community skills, quality tooling, deployment configs, and earned recipes, grouped by concern. Your job is judgment, not coverage: read the project, pick the relevant entries, propose, install.

One of this repo's setup skills, independent of the others. Run from a checkout of this repo; the argument is the path to the target project (ask if missing). Idempotent - re-running revisits the selection against the project's current state.

## Two routes

Decide the route up front from one fact - does the target have a `package.json`?

- **Greenfield** (no `package.json`): follow [greenfield.md](./greenfield.md) - agree the stack with the user, scaffold with the defaults, then continue below from step 2 with the fresh app as the target.
- **Existing**: start at step 1 and let the project's current state drive the selection.

## Process

### 1. Read the project

Understand what it is before proposing anything: framework and dependencies, package manager, scripts, whether it has a UI a user opens in a browser, how it deploys, what `skills-lock.json` already pins, what `AGENTS.md` already says. The project keeps whatever package manager it already uses - package scripts stay the command interface either way.

### 2. Propose from the catalog

Read [catalog.md](./catalog.md) and select what serves this project. A Next.js app on Vercel wants most of it; a static site wants a fraction; nothing in the catalog is mandatory. Present the selection with one line of reasoning each, note what you're deliberately skipping, and confirm with the user before touching anything.

### 3. Install

Community skills, from the target project root:

```bash
npx skills add <repo> --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- `--agent codex` writes real directories into `.agents/skills/`; `--copy` keeps the files in the project instead of symlinking a package cache
- Skip skills already pinned in `skills-lock.json` at the same source
- Normalize afterwards: real dirs under `.agents/skills/`, relative symlinks `.claude/skills/<name>` → `../../.agents/skills/<name>` (create missing ones; move any stray real dirs the CLI wrote into `.claude/` or `agent/`)
- Commit `skills-lock.json` together with the skill folders

Tooling and configs (quality gate devDeps, scripts, `vercel.json`, etc.) go in as the catalog describes, adapted to the project's package manager.

### 4. Record in AGENTS.md

Add or update a `## Web stack` section in the target's `AGENTS.md`: what was adopted and the conventions that follow from it (e.g. "`npm run check` must be green before any commit", "UI changes are verified with `agent-browser`, never naive fetching"). Keep it to what an agent must know before touching a file - a few lines, updated in place on re-run, the project's other sections untouched.

Convention for the instructions file itself: `AGENTS.md` is the real file, `CLAUDE.md` a symlink to it. If only `CLAUDE.md` exists, rename it and add the symlink; if both exist as real files, show the user the difference and ask; if neither exists, create a minimal `AGENTS.md` and the symlink.

### 5. Verify

Verify what you installed, nothing more:

- Skills discoverable: real dirs in `.agents/skills/`, working symlinks in `.claude/skills/`
- If the quality gate went in: its `check` script passes
- Any CLIs a selected entry depends on respond and are authenticated (`agent-browser` + Chromium, `gh`, `vercel`, `ctx7` - per the catalog notes)

Report anything only the user can fix by hand: auth, tokens, deployment-protection secrets.

## Report

End with: what was installed and why, what was skipped and why, tooling and script changes, the AGENTS.md update, verification results, and any manual follow-ups.
