---
name: setup-web-stack
description: "Equip a target web project from a curated catalog of community skills, tooling, and known-good configs - two routes, decided by whether the target exists yet: scaffold greenfield from the defaults reference, or read an existing project and install just what fits it."
argument-hint: "<path to target project>"
disable-model-invocation: true
---

# Setup Web Stack

Equip a target project with the web-stack skills and tooling that actually fit it. [catalog.md](./catalog.md) is the directory - community skills, quality tooling, deployment configs, and earned recipes, grouped by concern. Your job is judgment, not coverage: read the project, pick the relevant entries, propose, install.

The stack setup for a web product: [`setup-project`](../setup-project/SKILL.md) brings a project onto the flow and calls this skill for everything stack-specific. Run from a checkout of this repo; the argument is the path to the target project (ask if missing). Idempotent - re-running revisits the selection against the project's current state.

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
npx skills add "<source>#$(flow sources pin <source>)" --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- The pin is the commit the source log names for that source; the CLI records it as `ref` in `skills-lock.json`. A source the log lacks gets a section there first
- `--agent codex` writes real directories into `.agents/skills/`; `--copy` keeps the files in the project instead of symlinking a package cache
- Skip skills already locked at that `ref`; re-pin with `npx skills remove <name> -y` and a fresh `add`, never `npx skills update`
- Normalize afterwards: real dirs under `.agents/skills/`, relative symlinks `.claude/skills/<name>` → `../../.agents/skills/<name>` (create missing ones; move any stray real dirs the CLI wrote into `.claude/` or `agent/`)
- Commit `skills-lock.json` together with the skill folders

Tooling and configs (quality gate devDeps, scripts, `vercel.json`, etc.) go in as the catalog describes, adapted to the project's package manager.

A project with a `convex/` directory also takes the [Convex branch](./convex.md).

### 4. Journey tests

For each critical journey the client approved (the "Critical journeys" section of `docs/agents/dev-loop.md`): one plain Playwright test under `e2e/journeys/`, with its own `playwright.config.ts` there that starts the app per "Running the app" and signs in as a seeded test identity.
The `test:journeys` script runs them, and the "Journey tests" gate line names it.
With no approved journeys, scaffold nothing.

### 5. Record in the project docs

The stack's facts go where the flow reads them, per the Methodology section of [`standards/web-products.md`](../../standards/web-products.md) ("What this stack puts in those files"):

- `AGENTS.md`: the check command in "Rules for every session", and one must-read entry per pinned skill or file an implementer reads, each with its trigger.
- `docs/agents/dev-loop.md`: the gate lines, worktrees, running the app, Review lenses, QA tools with their named checks, Audit lenses, the scanner pass commands, the design-system commands, and each deviation from the doctrine with its reason.

Every skill pinned in step 3 is named on one of those lines; one that no line names is removed.

### 6. Verify

Verify what you installed, nothing more:

- Skills discoverable: real dirs in `.agents/skills/`, working symlinks in `.claude/skills/`
- If the quality gate went in: its `check` script passes
- Any CLIs a selected entry depends on respond and are authenticated (`agent-browser` + Chromium, `gh`, `vercel`, `ctx7` - per the catalog notes)

Report anything only the user can fix by hand: auth, tokens, deployment-protection secrets.

## Report

End with: what was installed and why, what was skipped and why, tooling and script changes, the lines written to the project docs, verification results, and any manual follow-ups.
