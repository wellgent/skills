#!/usr/bin/env bash
# Vercel build command. Production deploys Convex with the production deploy key.
# A preview, which only scripts/preview starts, builds with the Preview environment's preview
# deploy key: it gets a fresh Convex preview deployment named PREVIEW_NAME (pr-<number>) with
# this tree's functions and the seed, and the app built against it. A redeploy of the same PR
# deletes and recreates that preview deployment. The project's preview defaults carry its env
# (CRONS=off, ALLOW_TEST_OTP, JWKS, JWT_PRIVATE_KEY); SITE_URL is set to this Vercel deployment's
# URL, so a sign-in link points back to the preview.
set -euo pipefail

SEED_FUNCTION="<seed function, e.g. seed:run>"

if [ "${VERCEL_ENV:-}" = production ]; then
  pnpm exec convex deploy --cmd 'pnpm run build'
  exit 0
fi

[[ ${PREVIEW_NAME:-} =~ ^pr-[0-9]+$ ]] \
  || { echo "vercel-build: a preview needs PREVIEW_NAME=pr-<number> (scripts/preview passes it)" >&2; exit 1; }
[ -n "${VERCEL_URL:-}" ] || { echo "vercel-build: VERCEL_URL is not set" >&2; exit 1; }

pnpm exec convex deploy --cmd 'pnpm run build' --preview-create "$PREVIEW_NAME" --preview-run "$SEED_FUNCTION"
pnpm exec convex env set SITE_URL "https://$VERCEL_URL" --preview-name "$PREVIEW_NAME"
