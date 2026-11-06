#!/usr/bin/env bash
# Ephemeral dev-server lifecycle: start, stop and status of one `next dev` on an explicit port,
# serve-build of a fresh production build through `next start` on one,
# the checkout's long-running `convex dev` on a local Convex deployment (convex-start,
# convex-stop), teardown before a worktree goes, site-url, which prints the local deployment's
# HTTP actions origin, and clear-stale-types, which the typecheck runs first.
# One server per checkout at a time - servers share .next, which a second one clears or corrupts.
# One server per port on the host: `start` and `serve-build` claim their port
# (scripts/host-claims.sh) and refuse one another checkout holds, and `stop` stops only this
# checkout's server. The pid and log files are named by the checkout and the port.
# .next is also mode-contaminated across build/dev: `next dev` over a production build's .next
# 500s at runtime, and `next start` over a dev .next crashes - so both clear .next first.
# A linked worktree with a local deployment (.convex/local/default/config.json) is served by one
# long-running `convex dev`, which owns the local backend and pushes on every change;
# `convex dev --once` refuses beside it. A checkout on a cloud deployment pushes once per start.
# The main checkout stays on the shared cloud dev deployment, whatever .convex/local it holds.
# On a local deployment .env.local holds the Convex CLI to that backend alone: the self-hosted
# variables name its URL and admin key, and CONVEX_OVERRIDE_ACCESS_TOKEN replaces the host's
# Convex login with a token that authenticates nowhere, so `--prod`, `deploy` and every other
# command from the checkout reach only the local backend. Only this script's `convex dev`, which
# needs the login to run the backend, gets CONVEX_DEPLOYMENT and the login on its command line.
set -euo pipefail

CMD="${1:-}"
DEFAULT_PORT="<lowest dev-server port, e.g. 6110>"
PORT="${2:-$DEFAULT_PORT}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Every server this script starts runs on the project's own node, the devEngines.runtime pin pnpm
# installs into node_modules; Convex's local backend runs "use node" actions on the `node` on PATH.
PATH="$REPO_ROOT/node_modules/.bin:$PATH"
# shellcheck source=scripts/host-claims.sh
source "$REPO_ROOT/scripts/host-claims.sh"
PIDFILE="/tmp/${PROJECT:?}-dev-$(basename "$REPO_ROOT")-${PORT}.pid"
LOGFILE="/tmp/${PROJECT:?}-dev-$(basename "$REPO_ROOT")-${PORT}.log"
PORT_CLAIM="$CLAIMS_DIR/ports/$PORT"
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

# Prints "port pid" for each running server of this checkout that start or serve-build
# started, on any port, read from its pid files. A pid counts only while it names a next
# process, so a later process given the same pid does not.
checkout_servers() {
  local prefix file port pid
  prefix="/tmp/${PROJECT:?}-dev-$(basename "$REPO_ROOT")-"
  for file in "$prefix"*.pid; do
    port=${file#"$prefix"}
    port=${port%.pid}
    [[ $port =~ ^[0-9]+$ ]] || continue
    pid=$(cat "$file" 2>/dev/null) || continue
    [[ $pid =~ ^[0-9]+$ ]] && ps -o command= -p "$pid" 2>/dev/null | grep -q next && echo "$port $pid"
  done
  return 0
}

# Prints the pids of the listeners on PORT that hold this checkout's .next/dev/lock, or that are
# the server pid given, which `next start` is since it writes no lockfile.
checkout_listeners() {
  local pid
  for pid in $(lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null); do
    if [ "$pid" = "${1:-}" ] || lsof -a -p "$pid" -t -- "$REPO_ROOT/.next/dev/lock" >/dev/null 2>&1; then
      echo "$pid"
    fi
  done
}

LOCAL_CONFIG="$REPO_ROOT/.convex/local/default/config.json"
# Stands in for the host's Convex login in a local checkout's .env.local; Convex refuses it.
NO_LOGIN_TOKEN="checkout-holds-no-convex-login"

# Only the main checkout's git dir is also the common one.
main_checkout() {
  local git_dir
  git_dir=$(git -C "$REPO_ROOT" rev-parse --git-dir 2>/dev/null) || return 1
  [ "$git_dir" = "$(git -C "$REPO_ROOT" rev-parse --git-common-dir)" ]
}

local_deployment() { [[ -f "$LOCAL_CONFIG" ]] && ! main_checkout; }

local_url() { sed -nE 's/^NEXT_PUBLIC_CONVEX_URL=([^ #]+).*/\1/p' "$REPO_ROOT/.env.local"; }

# Prints the first port from the given one on that no process listens on and that is not the
# second argument.
free_port() {
  local port=$1
  while [ "$port" = "${2:-}" ] || lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1; do
    port=$((port + 1))
  done
  echo "$port"
}

# Prints the pid of this checkout's running `convex dev`; fails when none runs.
# For its first moments the process runs as the node_modules/.bin/convex shell wrapper before
# it execs node, so either command line counts, and its working directory, set before the
# launch, tells this checkout's process from another's.
convex_dev_pid() {
  local pid
  pid=$(cat "$CONVEX_PIDFILE" 2>/dev/null) || return 1
  [[ $pid =~ ^[0-9]+$ ]] || return 1
  ps -o command= -p "$pid" 2>/dev/null | grep -qE 'node_modules/\.bin/convex dev|convex/bin/main\.js dev' || return 1
  [ "$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')" = "$(cd "$REPO_ROOT" && pwd -P)" ] && echo "$pid"
}

# Rewrites .env.local so the Convex CLI reaches only the local backend: drops CONVEX_DEPLOYMENT,
# which `convex dev` writes at its start, and names the backend's URLs, its admin key and the
# token that replaces the login. The URLs come from the config, which the CLI saves before it
# starts the backend: the CLI rewrites no .env.local value another line repeats, so on new ports it
# leaves NEXT_PUBLIC_CONVEX_URL on the old one, where another checkout's backend may answer.
# Given "none", the backend did not start, and .env.local names no backend URL.
hold_cli_env() {
  local env="$REPO_ROOT/.env.local" tmp cloud site key
  read -r cloud site key < <(jq -r '"\(.ports.cloud) \(.ports.site) \(.adminKey)"' "$LOCAL_CONFIG")
  tmp=$(mktemp "$REPO_ROOT/.convex/env-local.XXXXXX")
  grep -v -E '^(# Deployment used by `npx convex dev`|# The Convex CLI of this checkout|CONVEX_DEPLOYMENT=|NEXT_PUBLIC_CONVEX_URL=|NEXT_PUBLIC_CONVEX_SITE_URL=|CONVEX_SELF_HOSTED_URL=|CONVEX_SELF_HOSTED_ADMIN_KEY=|CONVEX_OVERRIDE_ACCESS_TOKEN=)' \
    "$env" 2>/dev/null | sed '/^$/d' >"$tmp" || true
  {
    if [ "${1:-}" != none ]; then
      echo "NEXT_PUBLIC_CONVEX_URL=http://127.0.0.1:$cloud"
      echo "NEXT_PUBLIC_CONVEX_SITE_URL=http://127.0.0.1:$site"
    fi
    echo "# The Convex CLI of this checkout reaches only its local backend (scripts/dev-server.sh)."
    if [ "${1:-}" != none ]; then
      echo "CONVEX_SELF_HOSTED_URL=http://127.0.0.1:$cloud"
    fi
    echo "CONVEX_SELF_HOSTED_ADMIN_KEY=$key"
    echo "CONVEX_OVERRIDE_ACCESS_TOKEN=$NO_LOGIN_TOKEN"
  } >>"$tmp"
  mv "$tmp" "$env"
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

# Whether the local backend answers as this checkout's deployment on the port its config names.
backend_answers() {
  local port name
  read -r port name < <(jq -r '"\(.ports.cloud) \(.deploymentName)"' "$LOCAL_CONFIG" 2>/dev/null) || return 1
  [ "$(curl -sf "http://127.0.0.1:$port/instance_name" 2>/dev/null)" = "$name" ]
}

# Waits for the first push of the checkout's convex dev with the given pid, whose output is the
# log, and holds .env.local to the local backend in every outcome, since convex dev writes
# CONVEX_DEPLOYMENT there before it pushes. A backend lock this script holds goes once the
# backend answers.
# Exit 1 when the push fails (the functions do not deploy), 2 when the local backend never
# answers as this checkout's deployment.
await_first_push() {
  local pid=$1
  for _ in $(seq 1 "$CONVEX_READY_TIMEOUT"); do
    if grep -q 'Convex functions ready!' "$CONVEX_LOGFILE"; then
      hold_cli_env
      return 0
    fi
    kill -0 "$pid" 2>/dev/null || break
    if holds_backend_lock && backend_answers; then backend_unlock; fi
    sleep 1
  done
  if backend_answers; then
    hold_cli_env
    echo "convex dev did not push the functions - see $CONVEX_LOGFILE" >&2
    convex_stop >/dev/null || true
    return 1
  fi
  hold_cli_env none
  echo "the local Convex backend did not start - see $CONVEX_LOGFILE" >&2
  convex_stop >/dev/null || true
  return 2
}

# Starts the checkout's long-running convex dev when none runs, and waits for its first push.
convex_start() {
  local pid
  if pid=$(convex_dev_pid); then
    await_first_push "$pid" || return
    echo "convex dev already serves this checkout (pid $pid, log $CONVEX_LOGFILE)"
    return 0
  fi
  convex_stop >/dev/null
  mkdir -p "$REPO_ROOT/.convex"
  cd "$REPO_ROOT"
  # The backend binds its ports only once it runs, so no other checkout starts a backend until
  # this one answers.
  backend_lock
  # The ports are picked here: the config's while free, else the next free ones. The CLI keeps the
  # config's ports only while both are free, and otherwise can pick one port for both.
  local name cloud site
  read -r name cloud site < <(jq -r '"\(.deploymentName) \(.ports.cloud // 3210) \(.ports.site // 3211)"' "$LOCAL_CONFIG")
  cloud=$(free_port "$cloud")
  site=$(free_port "$site" "$cloud")
  # The wait reads the ready line of this convex dev only, so the last run's log goes first.
  # The child's own redirect empties it only after the child has expanded the variables below,
  # which can come after the wait's first read.
  : >"$CONVEX_LOGFILE"
  # The empty variables keep .env.local's values out, since the CLI's dotenv load never
  # replaces a variable the process already has.
  CONVEX_DEPLOYMENT="local:$name" \
    CONVEX_SELF_HOSTED_URL="" CONVEX_SELF_HOSTED_ADMIN_KEY="" CONVEX_OVERRIDE_ACCESS_TOKEN="" \
    nohup node_modules/.bin/convex dev --typecheck disable --tail-logs disable \
    --local-cloud-port "$cloud" --local-site-port "$site" >"$CONVEX_LOGFILE" 2>&1 &
  pid=$!
  echo "$pid" >"$CONVEX_PIDFILE"
  await_first_push "$pid" || return
  backend_unlock
  echo "convex dev serves $(local_url) (pid $pid, log $CONVEX_LOGFILE)"
}

case "$CMD" in
  start | serve-build)
    if alive; then
      echo "already running (pid $(cat "$PIDFILE"), port ${PORT}) - stop it first; never reuse a stale server" >&2
      exit 1
    fi
    if ! claim "$PORT_CLAIM"; then
      echo "port ${PORT} is claimed by $(cat "$PORT_CLAIM/checkout" 2>/dev/null) (pid $(cat "$PORT_CLAIM/pid" 2>/dev/null)) - pick another port" >&2
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
    if read -r other pid < <(checkout_servers); then
      echo "a server of this checkout is running (pid ${pid}, port ${other}) - stop it first; one server per checkout" >&2
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
    if [ "$CMD" = serve-build ]; then
      if ! node_modules/.bin/next build >"$LOGFILE" 2>&1; then
        echo "next build failed - see ${LOGFILE}" >&2
        exit 1
      fi
      nohup node_modules/.bin/next start -p "$PORT" >>"$LOGFILE" 2>&1 &
    else
      nohup node_modules/.bin/next dev --turbopack -p "$PORT" >"$LOGFILE" 2>&1 &
    fi
    pid=$!
    echo "$pid" >"$PIDFILE"
    hand_claim "$PORT_CLAIM" "$pid"
    # Ready once this checkout's server listens: an answer from any other listener is not.
    for _ in $(seq 1 60); do
      if [ -n "$(checkout_listeners "$pid")" ] && curl -s -o /dev/null "http://localhost:${PORT}/"; then
        echo "ready on http://localhost:${PORT} (pid $pid, log ${LOGFILE})"
        exit 0
      fi
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    echo "server not ready - see ${LOGFILE}" >&2
    "$0" stop "$PORT"
    exit 1
    ;;
  stop)
    server=""
    if [[ -f "$PIDFILE" ]]; then
      server=$(cat "$PIDFILE")
      kill "$server" 2>/dev/null || true
      rm -f "$PIDFILE"
    fi
    # Reap this checkout's straggler listeners on this port only; another checkout's server
    # stays. Report stopped only once none listens: TERM, wait, then KILL, wait.
    for sig in TERM KILL; do
      checkout_listeners "$server" | xargs kill "-${sig}" 2>/dev/null || true
      for _ in $(seq 1 10); do
        if [ -z "$(checkout_listeners "$server")" ]; then
          if claimed_by_checkout "$PORT_CLAIM"; then release_claim "$PORT_CLAIM"; fi
          echo "stopped (port ${PORT})"
          exit 0
        fi
        sleep 1
      done
    done
    echo "port ${PORT} still held by pid $(checkout_listeners "$server" | tr '\n' ' ')- not stopped" >&2
    exit 1
    ;;
  convex-start)
    if main_checkout; then
      echo "convex-start serves a linked worktree's local deployment; the main checkout stays on the shared cloud dev deployment" >&2
      if [ -e "$REPO_ROOT/.convex/local" ]; then
        echo "its .convex/local is stray state from an earlier local convex dev: recover the checkout as docs/agents/dev-loop.md \"Main checkout\" says" >&2
      fi
      exit 1
    fi
    local_deployment || { echo "convex-start serves a local deployment; .env.local names none" >&2; exit 1; }
    convex_start
    ;;
  convex-stop)
    convex_stop
    echo "convex dev stopped"
    ;;
  teardown)
    # Before the worktree goes: the checkout's servers, on whatever port, and its convex dev.
    if main_checkout; then
      echo "teardown is for a linked worktree; this is the main checkout" >&2
      exit 1
    fi
    checkout_servers | while read -r port _; do "$0" stop "$port"; done
    if checkout_dev_pid >/dev/null; then
      port=$(jq -r '.appUrl // empty' "$REPO_ROOT/.next/dev/lock" | sed -nE 's#.*:([0-9]+)/?$#\1#p')
      "$0" stop "$port"
    fi
    convex_stop
    # The checkout's per-run files go with it. Only port-numbered names match, so a checkout whose
    # name another's starts with keeps that other's files.
    prefix="/tmp/${PROJECT:?}-dev-$(basename "$REPO_ROOT")-"
    for file in "$prefix"*; do
      [[ ${file#"$prefix"} =~ ^[0-9]+\.(pid|log|log\.mark)$ ]] && rm -f -- "$file"
    done
    # So do its Playwright output directories, /tmp/<project>-<suite>-<checkout> from
    # e2e/support/output-dir.ts. A suite name holds no hyphen, so another checkout's stay.
    name=$(basename "$REPO_ROOT")
    for dir in "/tmp/${PROJECT}-"*"-$name"; do
      suite=${dir#"/tmp/${PROJECT}-"}
      suite=${suite%"-$name"}
      [[ -d $dir && $suite =~ ^[a-z0-9]+$ ]] && rm -rf -- "$dir"
    done
    echo "torn down: no server or convex dev of this checkout runs"
    ;;
  free)
    # Free for a new server: no listener and no claim of another server.
    ! lsof -ti "tcp:${PORT}" -sTCP:LISTEN >/dev/null 2>&1 && ! claim_owner "$PORT_CLAIM" >/dev/null
    ;;
  status)
    if alive && curl -s -o /dev/null "http://localhost:${PORT}/"; then
      echo "running (pid $(cat "$PIDFILE"), port ${PORT})"
    else
      echo "not running (port ${PORT})"
      exit 1
    fi
    ;;
  site-url)
    # The local deployment's HTTP actions origin, read here so no session opens the config file,
    # whose admin key would land in its transcript.
    [ -f "$LOCAL_CONFIG" ] || { echo "no local deployment in this checkout" >&2; exit 1; }
    jq -er '"http://127.0.0.1:\(.ports.site)"' "$LOCAL_CONFIG"
    ;;
  clear-stale-types)
    # The typecheck reads .next/dev/types, which only a running `next dev` keeps current:
    # with none running they name the routes of an earlier tree, so they go.
    if ! checkout_dev_pid >/dev/null; then
      rm -rf "$REPO_ROOT/.next/dev/types"
    fi
    ;;
  *)
    echo "usage: $0 {start|serve-build|stop|status|free} [port]   (default port $DEFAULT_PORT)" >&2
    echo "       $0 {convex-start|convex-stop|teardown|site-url|clear-stale-types}" >&2
    exit 2
    ;;
esac
