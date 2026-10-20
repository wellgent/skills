#!/usr/bin/env bash
# Gives one PR a Vercel preview: labels it `preview`, deploys its head SHA from a clean
# checkout with the Vercel CLI, and comments the preview URL on the PR. Vercel skips every git
# push that is not main (scripts/vercel-ignore.sh), and its ignored build step does not run for
# a CLI deployment, so a preview exists only through this script; scripts/check reruns it for
# a labelled PR's new head.
# The build (scripts/vercel-build.sh) gives the preview its own Convex preview deployment pr-<pr>,
# recreated with the seed for each new head, so an earlier head's preview URL may stop working.
# --non-interactive fixes the CLI's JSON to its agent shape ({status, deployment}), which it
# otherwise picks only when it detects an agent, so the script reads the URL from any shell.
# Needs the host's Vercel CLI login with access to the project.
set -euo pipefail

VERCEL_ORG_ID="<Vercel team id, from .vercel/project.json orgId>"
VERCEL_PROJECT_ID="<Vercel project id, from .vercel/project.json projectId>"
export VERCEL_ORG_ID VERCEL_PROJECT_ID

[ $# -eq 1 ] && [[ $1 =~ ^[0-9]+$ ]] || { echo "usage: scripts/preview <pr number>" >&2; exit 1; }
pr=$1

cd "$(git rev-parse --show-toplevel)"
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
read -r head state < <(gh pr view "$pr" --repo "$repo" --json headRefOid,state --jq '[.headRefOid, .state] | @tsv')
[ "$state" = OPEN ] || { echo "preview: PR $pr is $state, not open" >&2; exit 1; }

gh pr edit "$pr" --repo "$repo" --add-label preview >/dev/null
git fetch -q origin "pull/$pr/head"

tree=$(mktemp -d "${TMPDIR:-/tmp}/preview-$pr.XXXXXX")
cleanup() { git worktree remove --force "${tree:?}" 2>/dev/null || rm -rf "${tree:?}"; }
trap cleanup EXIT
git worktree add -q --detach "$tree" "$head"

echo "preview: deploying PR $pr head $head"
url=$(vercel deploy "$tree" --yes --non-interactive --json --build-env "PREVIEW_NAME=pr-$pr" \
  --meta "pr=$pr" --meta "sha=$head" | jq -r '.deployment.url')
[[ $url == https://* ]] || { echo "preview: the Vercel CLI printed no deployment URL" >&2; exit 1; }
gh pr comment "$pr" --repo "$repo" --body "Preview of $head: $url" >/dev/null
echo "preview: $url"
