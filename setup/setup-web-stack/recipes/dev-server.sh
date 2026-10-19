#!/usr/bin/env bash
# Ephemeral dev-server lifecycle: start, stop and status of one `next dev` on an explicit port,
# the checkout's long-running `convex dev` on a local Convex deployment (convex-start,
# convex-stop), teardown before a worktree goes, and clear-stale-types, which the typecheck
# runs first.
# One server per checkout at a time - concurrent `next dev` processes share .next and corrupt it.
# .next is also mode-contaminated across build/dev: `next dev` over a production build's .next
# 500s at runtime, and `next start` over a dev .next crashes - so `start` clears .next first.
# A checkout whose .env.local names a local deployment (CONVEX_DEPLOYMENT=local:...) is served by
# one long-running `convex dev`, which owns the local backend and pushes on every change;
# `convex dev --once` refuses beside it. A checkout on a cloud deployment pushes once per start.
set -euo pipefail

PROJECT="<project name>"
DEFAULT_PORT="<lowest dev-server port, e.g. 6110>"
CMD="${1:-}"
PORT="${2:-$DEFAULT_PORT}"
PIDFILE="/tmp/${PROJECT:?}-dev-${PORT}.pid"
LOGFILE="/tmp/${PROJECT:?}-dev-${PORT}.log"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONVEX_PIDFILE="$REPO_ROOT/.convex/convex-dev.pid"
CONVEX_LOGFILE="$REPO_ROOT/.convex/convex-dev.log"
CONVEX_READY_TIMEOUT=180

alive() { [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

# Prints the pid of a running `next dev` of this checkout, on any port, read from the
# lockfile `next dev` writes in .next/dev; fails when none runs. The server holds the
# lockfile open while it runs, and the file stays behind when it exits, so the pid
# counts only while it holds this lockfile: a later process given the same pid does not.
checkout_dev_pid() {
  local lock="$REPO_ROOT/.next/dev/lock" pid
  pid=$(jq -r '.pid // empty' "$lock" 2>/dev/null) || return 1
  [[ $pid =~ ^[0-9]+$ ]] && lsof -a -p "$pid" -t -- "$lock" >/dev/null 2>&1 && echo "$pid"
}

local_deployment() { grep -q '^CONVEX_DEPLOYMENT=local:' "$REPO_ROOT/.env.local" 2>/dev/null; }

local_url() { sed -nE 's/^NEXT_PUBLIC_CONVEX_URL=([^ #]+).*/\1/p' "$REPO_ROOT/.env.local"; }

# Prints the pid of this checkout's running `convex dev`; fails when none runs.
convex_dev_pid() {
  local pid
  pid=$(cat "$CONVEX_PIDFILE" 2>/dev/null) || return 1
  [[ $pid =~ ^[0-9]+$ ]] && ps -o command= -p "$pid" 2>/dev/null | grep -q 'convex/bin/main.js dev' && echo "$pid"
}

# Pids of local backends that serve this checkout's .convex state, with or without a convex dev.
checkout_backend_pids() { pgrep -f -- "--local-storage $REPO_ROOT/.convex/" || true; }

convex_stop() {
  local pid
  if pid=$(convex_dev_pid); then
    # convex dev stops its local backend on SIGINT, and leaves it running on SIGTERM.
    kill -INT "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
    kill -TERM "$pid" 2>/dev/null || true
  fi
  rm -f "$CONVEX_PIDFILE"
  # shellcheck disable=SC2046 # one pid per word
  [ -z "$(checkout_backend_pids)" ] || kill -TERM $(checkout_backend_pids) 2>/dev/null || true
  for _ in $(seq 1 20); do [ -z "$(checkout_backend_pids)" ] && return 0; sleep 0.5; done
  echo "a local backend of this checkout still runs (pid $(checkout_backend_pids | tr '\n' ' '))" >&2
  return 1
}

# Starts the checkout's long-running convex dev when none runs, and waits for its first push.
# Exit 1 when the push fails (the functions do not deploy), 2 when the local backend never
# answers.
convex_start() {
  local pid url
  if pid=$(convex_dev_pid); then
    echo "convex dev already serves this checkout (pid $pid, log $CONVEX_LOGFILE)"
    return 0
  fi
  convex_stop >/dev/null
  mkdir -p "$REPO_ROOT/.convex"
  cd "$REPO_ROOT"
  nohup node_modules/.bin/convex dev --typecheck disable --tail-logs disable >"$CONVEX_LOGFILE" 2>&1 &
  echo $! >"$CONVEX_PIDFILE"
  url=$(local_url)
  for _ in $(seq 1 "$CONVEX_READY_TIMEOUT"); do
    if grep -q 'Convex functions ready!' "$CONVEX_LOGFILE"; then
      echo "convex dev serves $url (pid $(cat "$CONVEX_PIDFILE"), log $CONVEX_LOGFILE)"
      return 0
    fi
    kill -0 "$(cat "$CONVEX_PIDFILE")" 2>/dev/null || break
    sleep 1
  done
  if curl -sf -o /dev/null "$url/instance_name"; then
    echo "convex dev did not push the functions - see $CONVEX_LOGFILE" >&2
    convex_stop >/dev/null || true
    return 1
  fi
  echo "the local Convex backend did not start at $url - see $CONVEX_LOGFILE" >&2
  convex_stop >/dev/null || true
  return 2
}

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
    # .next belongs to the checkout, so a server on another port still owns it.
    if pid=$(checkout_dev_pid); then
      echo "a next dev of this checkout is running (pid ${pid}) - stop it first; one server per checkout" >&2
      exit 1
    fi
    cd "$REPO_ROOT"
    # Clear any stale .next - a production `next build` output poisons `next dev` (and vice versa).
    rm -rf .next
    if local_deployment; then
      convex_start
    else
      pnpm exec convex dev --once
    fi
    nohup node_modules/.bin/next dev --turbopack -p "$PORT" >"$LOGFILE" 2>&1 &
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
  convex-start)
    local_deployment || { echo "convex-start serves a local deployment; .env.local names none" >&2; exit 1; }
    convex_start
    ;;
  convex-stop)
    convex_stop
    echo "convex dev stopped"
    ;;
  teardown)
    # Before the worktree goes: the checkout's next dev, on whatever port, and its convex dev.
    if [[ "$(git -C "$REPO_ROOT" rev-parse --git-dir)" == "$(git -C "$REPO_ROOT" rev-parse --git-common-dir)" ]]; then
      echo "teardown is for a linked worktree; this is the main checkout" >&2
      exit 1
    fi
    if checkout_dev_pid >/dev/null; then
      port=$(jq -r '.appUrl // empty' "$REPO_ROOT/.next/dev/lock" | sed -nE 's#.*:([0-9]+)/?$#\1#p')
      "$0" stop "$port"
    fi
    convex_stop
    echo "torn down: no next dev or convex dev of this checkout runs"
    ;;
  status)
    if alive && curl -s -o /dev/null "http://localhost:${PORT}/"; then
      echo "running (pid $(cat "$PIDFILE"), port ${PORT})"
    else
      echo "not running (port ${PORT})"
      exit 1
    fi
    ;;
  clear-stale-types)
    # The typecheck reads .next/dev/types, which only a running `next dev` keeps current:
    # with none running they name the routes of an earlier tree, so they go.
    if ! checkout_dev_pid >/dev/null; then
      rm -rf "$REPO_ROOT/.next/dev/types"
    fi
    ;;
  *)
    echo "usage: $0 {start|stop|status} [port]   (default port $DEFAULT_PORT)" >&2
    echo "       $0 {convex-start|convex-stop|teardown|clear-stale-types}" >&2
    exit 2
    ;;
esac
