#!/usr/bin/env bash
# Vercel ignored build step (ignoreCommand in vercel.json): exit 0 skips the build, exit 1 builds.
# It runs only for git pushes: Vercel builds main (production) and skips every other branch.
# A PR's preview is a Vercel CLI deployment from scripts/preview, which this step never sees.
set -euo pipefail

if [ "${VERCEL_ENV:-}" = production ]; then
  echo "building production"
  exit 1
fi
echo "skipped: Vercel builds main; a PR labelled preview gets its preview from scripts/preview"
exit 0
