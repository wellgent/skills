# Verify reference

Scaffold for a target project's `verify` skill - the repo-specific manual for launching, signing in, and driving the app at runtime.
The shared mechanics live in [verify-protocol.md](verify-protocol.md) and are read in place from the installed skill; the scaffolded skill holds only what is unique to the repo, and each verification session appends the gotchas it earns.
Launch-the-app content belongs in this one skill - launch is its first chapter, not a companion skill.

Scaffold two artifacts, resolving every `<placeholder>` from the project.

## 1. The dev-server script: `scripts/dev-server.sh`

Ephemeral, session-owned servers on explicit ports - so an agent's server can die with its session without taking anyone else's down.
Ports come from the contract's port map (`docs/agents/dev-loop.md`): the off-loop port (work outside the loop, manual or agent-driven - loop sessions keep off it), the gate port for verification, the takes port for implementers.

```bash
#!/usr/bin/env bash
# Ephemeral dev-server lifecycle for verification runs (see the verify skill).
# One server per checkout at a time - concurrent dev processes share build state and corrupt it.
set -euo pipefail

CMD="${1:-}"
PORT="${2:-<gate port>}"
PIDFILE="/tmp/<project>-dev-${PORT}.pid"
LOGFILE="/tmp/<project>-dev-${PORT}.log"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

alive() { [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

case "$CMD" in
  start)
    if alive; then
      echo "already running (pid $(cat "$PIDFILE"), port ${PORT}) - stop it first; never reuse a stale server" >&2
      exit 1
    fi
    # Listeners only (-sTCP:LISTEN) - client keep-alive sockets on the port are not a server.
    if lsof -ti "tcp:${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "port ${PORT} has a listener this script does not own - pick another port" >&2
      exit 1
    fi
    cd "$REPO_ROOT"
    <optional backend sync, e.g. `npx convex dev --once`>
    nohup <dev command, e.g. `node_modules/.bin/next dev --turbopack`> -p "$PORT" >"$LOGFILE" 2>&1 &
    echo $! >"$PIDFILE"
    for _ in $(seq 1 60); do
      if curl -s -o /dev/null "http://localhost:${PORT}/"; then
        echo "ready on http://localhost:${PORT} (pid $(cat "$PIDFILE"), log ${LOGFILE})"
        exit 0
      fi
      sleep 1
    done
    echo "server not ready after 60s - see ${LOGFILE}" >&2
    "$0" stop "$PORT"
    exit 1
    ;;
  stop)
    if [[ -f "$PIDFILE" ]]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null || true
      rm -f "$PIDFILE"
    fi
    # Reap straggler listeners, scoped to this port only - never a broad pkill.
    # -sTCP:LISTEN keeps client keep-alive sockets out of the kill list.
    lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
    echo "stopped (port ${PORT})"
    ;;
  status)
    if alive && curl -s -o /dev/null "http://localhost:${PORT}/"; then
      echo "running (pid $(cat "$PIDFILE"), port ${PORT})"
    else
      echo "not running (port ${PORT})"
      exit 1
    fi
    ;;
  *)
    echo "usage: $0 {start|stop|status} [port]   (default: the gate port)" >&2
    exit 2
    ;;
esac
```

## 2. The skill: `.agents/skills/verify/SKILL.md`

The template below is the skeleton; the `<slots>` are where the project's own knowledge lives.
Fill what is knowable at scaffold time and leave the rest as headed sections that verification sessions grow.

```markdown
---
name: verify
description: How to launch and drive this app at runtime - dev servers, agent sign-in, and browser driving. Use when verifying a change end-to-end in the running app, or when asked to run, start, or screenshot the app.
---

# Verifying <project> at runtime

Protocol first: read `../orchestrate/references/verify-protocol.md` - dev-server discipline, the browser preflight, the review loop, the universal gotchas.
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
```
