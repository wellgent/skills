---
name: verify
description: How to launch and drive this app at runtime - dev servers, agent sign-in, and browser driving. Use when verifying a change end-to-end in the running app, or when asked to run, start, or screenshot the app.
---

# Verifying <project> at runtime

Protocol first: read `protocol.md` beside this file - dev-server discipline, the browser preflight, the review loop, the universal gotchas. It is managed by `setup-verify` and replaced on every run; never edit it here.
This skill declares what is unique to this repo.

## Ports

<The role map - every port a session must know, including any it must never touch:
- <off-loop port> - work outside the loop, manual or agent-driven. Loop sessions keep off it.
- <gate port> - gate verification.
- <takes port> - implementer takes.
- <production port, when the host co-runs the production service> - never touch it, never kill anything on it.>

## Launch

Use `scripts/dev-server.sh start <gate port>` for a fresh, session-owned server; stop it at session end.

<What start actually runs and anything launch-specific: backend sync steps, the dev command, per-port build-dir isolation, interactive-dev notes.>

## Sign-in for agents

<How an agent signs in without a human: the dev-only backdoor (test accounts, logged OTPs or magic links, seeded sessions) and its exact steps.
Whatever the mechanism, it must be dev-deployment-only - production keeps the real flow, and the backdoor never ships or runs there.>

## Driving gotchas

<Project-specific driving gotchas, appended as sessions earn them: selectors that need `type` over fill, modals that trap Escape, forms that only enable on dirty+valid, waits that hang on persistent sockets.>

## Environment gotchas

<Checkout-specific hazards, appended as sessions earn them.>

## Checks that work well

<The project's proven verification moves: SSR greps with an authed request, two-page reactivity assertions, unauthenticated-redirect curls.>
