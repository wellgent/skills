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
    # Report stopped only once the port is observed closed: TERM, wait, then KILL, wait.
    for sig in TERM KILL; do
      lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null | xargs kill "-${sig}" 2>/dev/null || true
      for _ in $(seq 1 10); do
        if ! lsof -ti "tcp:${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
          echo "stopped (port ${PORT})"
          exit 0
        fi
        sleep 1
      done
    done
    echo "port ${PORT} still held by pid $(lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')- not stopped" >&2
    exit 1
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
