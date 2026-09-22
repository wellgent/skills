---
name: setup-verify
description: "Give a target project its verify skill - the repo-specific manual for launching, signing in, and driving the app at runtime - on top of the shared verify protocol: scaffold the skill and the ephemeral dev-server script once, and on every later run replace the managed protocol file and report drift in the script."
argument-hint: "<path to target project>"
disable-model-invocation: true
---

# Setup verify

Give a target project its `verify` skill: the one mandated project-local skill, the manual any agent session reads to launch the app, sign in as an agent, and drive it at runtime. Manual work on the off-loop port, an implementer take proving its change, the dev-loop gate, and a plain "run the app and screenshot it" request all go through it.

One of this repo's setup skills, independent of the others. Run from a checkout of this repo; the argument is the path to the target project (ask if missing). Idempotent - re-running is the sweep.

## What the project ends up with

- `.agents/skills/verify/SKILL.md` - the project's own skill, scaffolded once from [templates/verify-skill.md](templates/verify-skill.md) and never overwritten after: ports, launch, agent sign-in, and the gotcha sections verification sessions grow. Symlinked from `.claude/skills/verify`.
- `.agents/skills/verify/protocol.md` - the shared mechanics, a verbatim copy of [protocol.md](protocol.md): dev-server discipline, the browser health preflight, the review loop, universal gotchas, the living-skill rule. Managed: replaced wholesale on every run, never edited in the project.
- `scripts/dev-server.sh` - ephemeral, session-owned servers on explicit ports, scaffolded once from [templates/dev-server.sh](templates/dev-server.sh) with the placeholders resolved.

Launch-the-app content lives in `verify` - launch is its first chapter, never a companion `run` skill.
A line belongs in the protocol only when it reads identically for every project; anything project-specific belongs in the project's `SKILL.md`.

## Process

### 1. Read the project

Resolve every placeholder the templates carry before writing: the project name, the dev command (and any backend sync step that must run first, such as `npx convex dev --once`), and the port roles. Ports come from `.agents/launch.json` (off-loop, gate, takes); with no launch file yet, claim them per the operator's port registry or ask, and write the launch file as the dev-loop declarations describe. Note whether the host co-runs a production service whose port must never be touched, and how an agent signs in without a human (a dev-only backdoor; production keeps the real flow).

### 2. Scaffold once

When `.agents/skills/verify/SKILL.md` is absent: write it from the template with the Ports and Launch sections filled and the rest left as headed sections, create the `.claude/skills/verify` relative symlink, and write `scripts/dev-server.sh` from its template with the placeholders resolved, executable. Leave the project's `AGENTS.md` alone unless it lacks a pointer to the skill; then add one line under its development-workflow section.

When the skill already exists: do not touch `SKILL.md`. It is the project's living manual.

### 3. Replace the managed protocol

Copy [protocol.md](protocol.md) to `.agents/skills/verify/protocol.md` verbatim, on every run. This is how protocol updates reach projects: no merge, no pin, the file is the whole shared layer.

### 4. Report script drift

Diff the project's `scripts/dev-server.sh` against the template's shape - the stop block that confirms the port closed, the listener-only sweep, the start refusal on a taken port. Report what diverges and why it matters; converge it with the user's agreement, keeping the project's resolved placeholders and any local additions.

## Report

End with: what was scaffolded versus refreshed, the resolved ports and launch command, the protocol copy's source commit, and any dev-server drift left in place.
