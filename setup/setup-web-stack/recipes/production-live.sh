#!/usr/bin/env bash
# Prints the git commit the production domain serves, read from the Vercel deployment it is
# aliased to. scripts/land merges only once this is main's tip, so two production builds never
# overlap and an older one cannot finish last; a production step that needs a landing live waits
# on it the same way.
# Exit 0 printed, 1 unreadable. Needs the host's Vercel CLI login with access to the project.
set -euo pipefail

PRODUCTION_DOMAIN="<production domain, e.g. example.com>"
VERCEL_ORG_ID="<Vercel team id, from .vercel/project.json orgId>"
VERCEL_PROJECT_ID="<Vercel project id, from .vercel/project.json projectId>"
export VERCEL_ORG_ID VERCEL_PROJECT_ID

sha=$(vercel api "/v13/deployments/$PRODUCTION_DOMAIN" 2>/dev/null | jq -r '.meta.githubCommitSha // empty') || true
[[ $sha =~ ^[0-9a-f]{40}$ ]] || { echo "production-live: no git commit for the deployment $PRODUCTION_DOMAIN serves" >&2; exit 1; }
echo "$sha"
