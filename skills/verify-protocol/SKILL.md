---
name: verify-protocol
description: The shared runtime-verification mechanics every project's local verify skill reads in place - dev-server discipline, browser preflight, the review loop, universal gotchas - plus the scaffold for that project-local verify skill and its dev-server script. Read when a project's verify skill points here, or when scaffolding one.
---

# Verify protocol

Two files, read in place from the installed skill - never copied into a project:

- [verify-protocol.md](verify-protocol.md) - the mechanics that read identically for every project: dev-server discipline, the browser health preflight, the review loop, universal gotchas, and the living-skill rule. A project's local `verify` skill reads it first and declares only what is unique to the repo.
- [verify-reference.md](verify-reference.md) - the scaffold for that project-local skill: `scripts/dev-server.sh` (ephemeral, port-scoped servers) and `.agents/skills/verify/SKILL.md` (ports, launch, agent sign-in, and the gotcha sections sessions grow).

Install beside `orchestrate` as an ordinary pin: `npx skills add wellgent/skills -s verify-protocol`.
The project-local `verify` skill is the one mandated project-local skill; scaffold it from the reference with `setup-matts-skills`, or by hand, and let each verification session append the gotchas it earns there.
A line belongs in the protocol only when it reads identically for every project; anything project-specific lives in the local skill.
