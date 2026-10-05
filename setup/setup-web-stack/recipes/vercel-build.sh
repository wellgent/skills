#!/usr/bin/env bash
# Vercel build command. Production deploys Convex with the production deploy key.
# A prototype/* branch gets its own seeded Convex preview deployment through the preview
# deploy key. Every other preview builds against the project's default dev deployment.
set -euo pipefail

PROTOTYPE_SEED_FUNCTION="<seed function, e.g. prototype/seed:run>"

if [ "${VERCEL_ENV:-}" = production ]; then
  pnpm exec convex deploy --cmd 'pnpm run build'
elif [[ "${VERCEL_GIT_COMMIT_REF:-}" == prototype/* ]]; then
  pnpm exec convex deploy --cmd 'pnpm run build' --preview-run "$PROTOTYPE_SEED_FUNCTION"
else
  pnpm run build
fi
