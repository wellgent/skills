#!/usr/bin/env bash
# Vercel build command. Production deploys Convex with the production deploy key.
# A preview builds against the Preview-scoped NEXT_PUBLIC_CONVEX_URL, a shared dev
# deployment.
set -euo pipefail

if [ "${VERCEL_ENV:-}" = production ]; then
  pnpm exec convex deploy --cmd 'pnpm run build'
else
  pnpm run build
fi
