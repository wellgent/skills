# Verify reference

Scaffold for a target project's `verify` skill - the repo-specific manual for launching, signing in, and driving the app at runtime.
Agents observe what they actually built through it: browser review during development, and the dev-loop gate (`orchestrate`) calls it for any ticket with runtime surface.
It is a living skill: each verification session appends the gotchas it earns, so the manual sharpens with use.

Scaffold two artifacts, resolving every `<placeholder>` from the project.

## 1. The dev-server script: `scripts/dev-server.sh`

Ephemeral, session-owned servers on explicit ports - so an agent's server can die with its session without taking anyone else's down.
Ports come from the contract's port map (`docs/agents/dev-loop.md`): the off-loop port (work outside the loop, manual or agent-driven - loop sessions keep off it), the gate port for verification, the takes port for implementers.

```bash
#!/usr/bin/env bash
# Ephemeral dev-server lifecycle for verification runs (see the run/verify skills).
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
    if lsof -ti "tcp:${PORT}" >/dev/null 2>&1; then
      echo "port ${PORT} is taken by a process this script does not own - pick another port" >&2
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
    # Reap stragglers, scoped to this port only - never a broad pkill.
    lsof -ti "tcp:${PORT}" 2>/dev/null | xargs kill 2>/dev/null || true
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
description: How to launch and drive this app for runtime verification - dev servers, agent sign-in, and browser driving. Use when verifying a change end-to-end in the running app.
---

# Verifying <project> at runtime

## Launch

Use `scripts/dev-server.sh start <gate port>` for a fresh, session-owned server.
Always `scripts/dev-server.sh stop <gate port>` at the end of the session - teardown is part of the loop, not optional.

## Browser health preflight

Default tool: **`agent-browser`**.
Before a verification session, prove the daemon spawns:

    agent-browser open about:blank && agent-browser session info --json && agent-browser close

Healthy output has `"browserLaunched":true` and `"success":true`.
If the daemon fails with `Resource temporarily unavailable` (EAGAIN), the likely cause is per-user process-limit exhaustion: diagnose with `ps aux | wc -l` vs `ulimit -u`, recover by reaping strays (`agent-browser close --all`, leftover dev servers, headless Chrome) rather than reinstalling.

## Sign-in for agents

<How an agent signs in without a human: the dev-only backdoor (test accounts, logged OTPs or magic links, seeded sessions) and its exact steps.
Whatever the mechanism, it must be dev-deployment-only - production keeps the real flow, and the backdoor never ships or runs there.>

## Driving the browser

The known-good review loop, against your session's own port:

    agent-browser open http://localhost:<gate port> && agent-browser wait --load networkidle
    agent-browser set viewport 375 812 && agent-browser screenshot --full mobile.png
    agent-browser set viewport 1280 800 && agent-browser screenshot --full desktop.png
    agent-browser close

Pass **absolute paths** to `agent-browser screenshot` - relative paths resolve against the daemon's working directory, not the caller's.

<Project-specific driving gotchas, appended as sessions earn them: selectors that need `type` over fill, modals that trap Escape, forms that only enable on dirty+valid, waits that hang on persistent sockets.>

## Environment gotchas

<Appended as sessions earn them.
Universal seed: a production build clobbers a running dev server's build dir - stop the server before `next build`, and restart clean if it 500s.
Saved browser auth state goes stale; re-run sign-in at the start of each session rather than trusting yesterday's.>

## Checks that work well

<The project's proven verification moves: SSR greps with an authed request, two-page reactivity assertions, unauthenticated-redirect curls.>
```
