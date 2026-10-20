#!/usr/bin/env bash
# Signs off the checked-out commit of a PR branch: under one of the host's heavy-run slots it runs
# the frozen install, `pnpm run check` and the journey tests against this worktree's local Convex
# backend, and only on a pass pushes HEAD to origin/<branch> and posts the `check` commit status
# on that exact SHA. The verifier and scripts/land read that status.
# --dry runs the same steps on any checked-out commit, detached or main included, and pushes and
# posts nothing: the smoke test /operate's Ready runs in a fresh worktree.
# Exit: 0 passed and posted, 1 refused or failed, 2 could not run (no gh auth, the backend would
# not start, no slot dir: infrastructure, not code).
# Copied to scripts/check by setup-web-stack. A project without Convex drops the local-deployment
# refusal and the convex-stop and convex-start step.
set -euo pipefail

# The project's dev-server port range; journeys take ports from its top, below any a session picks.
PORT_LOW="<lowest dev-server port, e.g. 6110>"
PORT_HIGH="<highest dev-server port, e.g. 6199>"

cd "$(git rev-parse --show-toplevel)"

dry=""
[ "${1:-}" != --dry ] || dry=1

refuse() { echo "check: refused: $*" >&2; exit 1; }
fail() { echo "check: FAILED at $*" >&2; exit 1; }
cannot() { echo "check: could not run: $*" >&2; exit 2; }

if [ -n "$dry" ]; then
  branch=$(git symbolic-ref --quiet --short HEAD || echo detached)
else
  branch=$(git symbolic-ref --quiet --short HEAD) || refuse "HEAD is detached; a sign-off is for a PR branch head"
  [ "$branch" != main ] || refuse "the branch is main; a sign-off is for a PR branch head"
fi
[ -z "$(git status --porcelain)" ] || refuse "the worktree has uncommitted or untracked files (git status)"
[ -f .convex/local/default/config.json ] \
  || refuse "this worktree has no local Convex deployment; run: bash scripts/worktree-setup.sh"
if lsof -t -- .next/dev/lock >/dev/null 2>&1; then
  refuse "a next dev of this worktree runs; stop it first: scripts/dev-server.sh stop <port>"
fi
gh auth status >/dev/null 2>&1 || cannot "gh is not authenticated"

# Take the slot first; everything after it runs under the slot.
[ -n "${HEAVY_RUN_HELD:-}" ] || exec scripts/slot "$0" "$@"

sha=$(git rev-parse HEAD)
started=$(date +%s)
echo "check: $branch at $sha"

pnpm install --frozen-lockfile || fail "pnpm install --frozen-lockfile"
pnpm run check || fail "pnpm run check"

# A fresh convex dev pushes exactly this commit's functions before the journeys.
scripts/dev-server.sh convex-stop >/dev/null || cannot "the worktree's convex dev would not stop"
set +e
scripts/dev-server.sh convex-start
started_backend=$?
set -e
case $started_backend in
  0) ;;
  2) cannot "the local Convex backend would not start" ;;
  *) fail "convex dev (the functions did not push)" ;;
esac

# The journeys port: one per slot from the top of the range, below any the verify skill picks.
port=$((PORT_HIGH + 1 - $(basename "$HEAVY_RUN_HELD")))
while lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1; do
  port=$((port - 1))
  [ "$port" -ge "$PORT_LOW" ] || cannot "no free journeys port from $PORT_LOW to $PORT_HIGH"
done
JOURNEYS_PORT=$port pnpm run test:journeys || fail "pnpm run test:journeys"

[ "$(git rev-parse HEAD)" = "$sha" ] && [ -z "$(git status --porcelain)" ] \
  || fail "the worktree changed while check ran; run it again on the commit to sign off"

if [ -n "$dry" ]; then
  duration=$(($(date +%s) - started))
  echo "check: dry run passed in $((duration / 60))m$((duration % 60))s on $sha; nothing pushed or posted"
  exit 0
fi

repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner) || cannot "gh could not read the repository"
remote=$(git ls-remote origin "refs/heads/$branch" | cut -f1)
if [ "$remote" != "$sha" ]; then
  git push --force-with-lease origin "HEAD:refs/heads/$branch" || fail "git push"
fi
duration=$(($(date +%s) - started))
gh api "repos/$repo/statuses/$sha" -f state=success -f context=check \
  -f description="$(hostname -s) $((duration / 60))m$((duration % 60))s" >/dev/null \
  || cannot "gh could not post the check status"
echo "check: passed in $((duration / 60))m$((duration % 60))s; posted check on $sha ($repo, $branch)"

# A PR labelled preview gets a preview of its new head.
pr=$(gh pr list --repo "$repo" --head "$branch" --state open --label preview --json number --jq '.[0].number // empty')
if [ -n "$pr" ]; then
  log="${TMPDIR:-/tmp}/preview-$pr.log"
  nohup scripts/preview "$pr" >"$log" 2>&1 &
  echo "check: PR $pr is labelled preview; scripts/preview deploys this head in the background (log $log)"
fi
