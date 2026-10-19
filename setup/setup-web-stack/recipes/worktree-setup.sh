#!/usr/bin/env bash
# Give this worktree its own dev environment: dependencies, a local Convex deployment served by
# the worktree's own long-running `convex dev`, the current functions and the seed.
# Once the local backend runs, .env.local holds the worktree's Convex CLI to it alone
# (scripts/dev-server.sh), so nothing run from the worktree reaches a cloud deployment.
# `--cloud` creates an expiring cloud dev deployment with a scoped deploy key instead, for work
# that needs a public URL. Either way the deployment runs no crons (CRONS=off), and the seed
# stores what its crons would. Needs the run host's Convex login to create the deployment.
# A rerun pushes and seeds again; the worktree keeps its deployment.
set -euo pipefail

SEED_FUNCTION="<seed function, e.g. seed:run>"
EXPIRATION="in 5 days"

mode=local
case "${1:-}" in
  "") ;;
  --cloud) mode=cloud ;;
  *) echo "usage: bash scripts/worktree-setup.sh [--cloud]" >&2; exit 2 ;;
esac

cd "$(git rev-parse --show-toplevel)"
name=$(basename "$PWD")
main=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
[ "$main" != "$PWD" ] || { echo "the main checkout keeps its own deployment; run this in a linked worktree" >&2; exit 1; }

pnpm install --frozen-lockfile

if [ ! -f .convex/local/default/config.json ] && ! grep -q '^CONVEX_DEPLOYMENT=' .env.local 2>/dev/null; then
  # The main checkout's CONVEX_DEPLOYMENT line names the Convex team and project.
  grep '^CONVEX_DEPLOYMENT=' "$main/.env.local" >.env.local
  if [ "$mode" = local ]; then
    env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment create local --select
  else
    env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment create "dev/$name" --type dev --select --expiration "$EXPIRATION"
    env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment token create "$name" --save-env
  fi
fi

# Convex reads CRONS when it pushes the functions, so it is set before the first push: on a new
# local deployment while .env.local still names it, before convex-start holds the CLI.
if [ -f .convex/local/default/config.json ]; then
  if grep -q '^CONVEX_DEPLOYMENT=local:' .env.local; then
    pnpm exec convex env set CRONS off
  fi
  scripts/dev-server.sh convex-start
else
  pnpm exec convex env set CRONS off
  pnpm exec convex dev --once
fi
pnpm exec convex run "$SEED_FUNCTION"
