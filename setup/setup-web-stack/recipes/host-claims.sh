# Host-wide claims that keep this project's checkouts on one host apart, sourced by
# scripts/dev-server.sh and scripts/worktree-setup.sh. A claim is a directory under
# ${XDG_STATE_HOME:-$HOME/.local/state}/<project name>, taken with mkdir, naming its owner's pid and
# checkout. A claim whose pid is gone is free again.
# - ports/<port>: the Next port of a checkout's `next dev`, held by that server's pid.
# - convex-backend: held while a checkout starts a local Convex backend, from the CLI's port
#   choice until the backend answers, since the CLI picks free ports without binding them.
# A script releases on exit every claim it still holds under its own pid.

PROJECT="<project name>"
CLAIMS_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/${PROJECT:?}"
CLAIM_CHECKOUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOCK="$CLAIMS_DIR/convex-backend"

# Prints the pid of the claim's live owner; fails when the claim is free.
claim_owner() {
  local pid
  pid=$(cat "$1/pid" 2>/dev/null) && [[ $pid =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null && echo "$pid"
}

release_claim() { rm -f "${1:?}/pid" "${1:?}/pid.next" "${1:?}/checkout"; rmdir "${1:?}" 2>/dev/null || true; }

# Takes the claim for this script's pid; fails while a live owner holds it.
claim() {
  local dir=$1 stale
  mkdir -p "$(dirname "$dir")"
  if [ -d "$dir" ] && ! claim_owner "$dir" >/dev/null; then
    stale=$(cat "$dir/pid" 2>/dev/null || true)
    # A claim with no pid yet is free only once its taker has had a minute to write one.
    if { [ -n "$stale" ] || [ -n "$(find "$dir" -maxdepth 0 -mmin +1)" ]; } \
      && [ "$(cat "$dir/pid" 2>/dev/null || true)" = "$stale" ]; then
      release_claim "$dir"
    fi
  fi
  mkdir "$dir" 2>/dev/null || return 1
  echo $$ >"$dir/pid"
  echo "$CLAIM_CHECKOUT" >"$dir/checkout"
}

# Hands a claim this script holds to another process, which then holds it while it runs.
hand_claim() {
  echo "$2" >"$1/pid.next"
  mv "$1/pid.next" "$1/pid"
}

claimed_by_checkout() { [ "$(cat "$1/checkout" 2>/dev/null)" = "$CLAIM_CHECKOUT" ]; }

# Takes the backend lock, waiting while another checkout holds it. Under a script that already
# holds it, which CONVEX_BACKEND_LOCK_HELD names, it takes nothing.
backend_lock() {
  if [ -n "${CONVEX_BACKEND_LOCK_HELD:-}" ] && [ "$(claim_owner "$BACKEND_LOCK")" = "$CONVEX_BACKEND_LOCK_HELD" ]; then
    return 0
  fi
  local said=""
  until claim "$BACKEND_LOCK"; do
    if [ -z "$said" ]; then
      echo "waiting for $(cat "$BACKEND_LOCK/checkout" 2>/dev/null) to start its local Convex backend" >&2
      said=1
    fi
    sleep 1
  done
  export CONVEX_BACKEND_LOCK_HELD=$$
}

holds_backend_lock() { [ "$(cat "$BACKEND_LOCK/pid" 2>/dev/null)" = $$ ]; }

backend_unlock() {
  if holds_backend_lock; then
    release_claim "$BACKEND_LOCK"
    unset CONVEX_BACKEND_LOCK_HELD
  fi
}

release_own_claims() {
  local dir
  for dir in "$BACKEND_LOCK" "$CLAIMS_DIR"/ports/*; do
    if [ "$(cat "$dir/pid" 2>/dev/null)" = $$ ]; then release_claim "$dir"; fi
  done
}
trap release_own_claims EXIT
