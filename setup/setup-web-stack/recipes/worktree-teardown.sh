#!/usr/bin/env bash
# Remove this linked worktree and everything it runs: its `next dev`, its long-running
# `convex dev` with the local backend, and the tree itself with the local deployment's state in
# .convex/. The branch stays. Run it from inside the worktree, after its work is committed and
# pushed: git refuses to remove a tree with uncommitted or untracked files.
set -euo pipefail

tree="$(git rev-parse --show-toplevel)"
main=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
[ "$main" != "$tree" ] || { echo "the main checkout stays; run this in a linked worktree" >&2; exit 1; }

"$tree/scripts/dev-server.sh" teardown
git -C "$main" worktree remove "$tree"
echo "removed worktree $tree"
