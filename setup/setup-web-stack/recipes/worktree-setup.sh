#!/usr/bin/env bash
# Give this worktree its own dev environment: dependencies, a local Convex deployment served by
# the worktree's own long-running `convex dev`, the current functions and the seed.
# Once the local backend runs, .env.local holds the worktree's Convex CLI to it alone
# (scripts/dev-server.sh), so nothing run from the worktree reaches a cloud deployment.
# `--cloud` creates an expiring cloud dev deployment with a scoped deploy key instead, for work
# that needs a public URL. Either way the deployment runs no crons (CRONS=off), and the seed
# stores what its crons would. Needs the run host's Convex login to create the deployment.
# A rerun pushes and seeds again; the worktree keeps its deployment.
# The Convex CLI picks a local backend's ports, free when it looks, without binding them, so the
# create, the CRONS set and convex-start, which each start a backend, run under one host-wide lock
# (scripts/host-claims.sh) until the worktree's backend runs: setups at once get distinct ports.
set -euo pipefail

# The Convex CLI exits 1 on every failure and names a Convex API answer as
# `Error fetching <method> <url> <status> <text>`, so its message alone tells a server error, which
# a rerun can clear, from a refusal. The create runs again once, after a pause, on a 5xx alone.
create_local_deployment() {
  local errors attempt status
  errors=$(mktemp)
  for attempt in 1 2; do
    status=0
    { env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment create "$project:local" --select 2>&1 1>&3 | tee "$errors" >&2; } 3>&1 || status=$?
    if [ "$status" = 0 ] || [ "$attempt" = 2 ] || ! grep -Eq 'Error fetching .* 5[0-9]{2} ' "$errors"; then
      break
    fi
    echo "the Convex API answered the create with a server error; creating again" >&2
    sleep 3
  done
  rm -f "${errors:?}"
  return "$status"
}

SEED_FUNCTION="<seed function, e.g. seed:run>"
EXPIRATION="in 5 days"

mode=local
case "${1:-}" in
  "") ;;
  --cloud) mode=cloud ;;
  *) echo "usage: bash scripts/worktree-setup.sh [--cloud]" >&2; exit 2 ;;
esac

cd "$(git rev-parse --show-toplevel)"
# shellcheck source=scripts/host-claims.sh
source scripts/host-claims.sh
name=$(basename "$PWD")
main=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
[ "$main" != "$PWD" ] || { echo "the main checkout keeps its own deployment; run this in a linked worktree" >&2; exit 1; }

pnpm install --frozen-lockfile

if [ ! -f .convex/local/default/config.json ] && ! grep -q '^CONVEX_DEPLOYMENT=' .env.local 2>/dev/null; then
  # The main checkout's CONVEX_DEPLOYMENT comment names the Convex team and project. The create
  # takes them in its reference, so only a created deployment is ever written to .env.local.
  project=$(sed -nE 's/^CONVEX_DEPLOYMENT=.*# team: ([^,]+), project: ([^ ]+).*/\1:\2/p' "$main/.env.local" 2>/dev/null || true)
  [ -n "$project" ] || { echo "$main/.env.local names no Convex team and project" >&2; exit 1; }
  if [ "$mode" = local ]; then
    backend_lock
    create_local_deployment
  else
    env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment create "$project:dev/$name" --type dev --select --expiration "$EXPIRATION"
    env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment token create "$name" --save-env
  fi
fi

# Convex reads CRONS when it pushes the functions, so it is set before the first push: on a new
# local deployment while .env.local still names it, before convex-start holds the CLI.
if [ -f .convex/local/default/config.json ]; then
  backend_lock
  if grep -q '^CONVEX_DEPLOYMENT=local:' .env.local; then
    pnpm exec convex env set CRONS off
  fi
  scripts/dev-server.sh convex-start
  backend_unlock
else
  # A cloud deployment is the worktree's own only when its scoped deploy key names it.
  deployment=$(sed -nE 's/^CONVEX_DEPLOYMENT=([^ #]+).*/\1/p' .env.local)
  key=$(sed -nE 's/^CONVEX_DEPLOY_KEY=(dev:[^|]+)\|.*/\1/p' .env.local)
  if [ -z "$key" ] || [ "$key" != "$deployment" ]; then
    echo ".env.local names no deployment of this worktree's own; remove its CONVEX_DEPLOYMENT line and rerun" >&2
    exit 1
  fi
  pnpm exec convex env set CRONS off
  pnpm exec convex dev --once
fi
pnpm exec convex run "$SEED_FUNCTION"
