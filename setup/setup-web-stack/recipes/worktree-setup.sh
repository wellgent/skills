#!/usr/bin/env bash
# Give this worktree its own dev environment: dependencies, an expiring Convex dev
# deployment, a deploy key scoped to that deployment, the current functions and the seed.
# Needs the run host's Convex login for the two deployment commands; everything a session
# runs here afterwards uses the scoped key in .env.local.
set -euo pipefail

SEED_FUNCTION="<seed function, e.g. seed:run>"
EXPIRATION="in 7 days"

cd "$(git rev-parse --show-toplevel)"
name=$(basename "$PWD")
main=$(git worktree list --porcelain | sed -n '1s/^worktree //p')

pnpm install --frozen-lockfile

if ! grep -q '^CONVEX_DEPLOY_KEY=' .env.local 2>/dev/null; then
  # The main checkout's env file names the Convex project and carries the app's other variables.
  [ "$main" = "$PWD" ] || cp "$main/.env.local" .env.local
  env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment create "dev/$name" --type dev --select --expiration "$EXPIRATION"
  env -u CONVEX_DEPLOY_KEY pnpm exec convex deployment token create "$name" --save-env
fi

pnpm exec convex dev --once
pnpm exec convex run "$SEED_FUNCTION"
