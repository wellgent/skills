#!/usr/bin/env bash
# Remove this linked worktree and everything it runs: its `next dev`, its long-running
# `convex dev` with the local backend, any other process still running from the tree (a test
# run, a `convex dev` started another way, their children), and the tree itself with the local
# deployment's state in .convex/. The branch stays. Run it from inside the worktree, after its
# work is committed and pushed: git refuses to remove a tree with uncommitted or untracked files.
set -euo pipefail

tree="$(git rev-parse --show-toplevel)"
main=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
[ "$main" != "$tree" ] || { echo "the main checkout stays; run this in a linked worktree" >&2; exit 1; }

"$tree/scripts/dev-server.sh" teardown

# Out of the tree, so the subshells below never count as its processes.
cd "$main"

# Every process whose working directory is inside the tree or whose command line names a path
# inside it, sparing this shell, its ancestors, its descendants and the other members of the
# caller's pipeline (same parent, same process group), such as a `| tail` started in the tree.
strays() {
  local procs cwds
  procs=$(ps -axo pid=,ppid=,pgid=,command=)
  cwds=$(lsof -a -d cwd -F pn 2>/dev/null || true)
  SELF=$$ TREE="$tree" CWDS="$cwds" awk '
    function inside(path) { return path == tree || index(path, tree "/") == 1 }
    BEGIN { self = ENVIRON["SELF"] + 0; tree = ENVIRON["TREE"]; cwds = ENVIRON["CWDS"] }
    {
      pid = $1; parent[pid] = $2; group[pid] = $3; kids[$2] = kids[$2] " " pid
      cmd = $0; sub(/^ *[0-9]+ +[0-9]+ +[0-9]+ +/, "", cmd)
      if (index(cmd " ", tree "/") || index(cmd " ", tree " ")) hit[pid] = 1
    }
    END {
      n = split(cwds, lines, "\n")
      for (i = 1; i <= n; i++) {
        if (substr(lines[i], 1, 1) == "p") p = substr(lines[i], 2)
        else if (substr(lines[i], 1, 1) == "n" && inside(substr(lines[i], 2))) hit[p] = 1
      }
      for (p = self; p > 1 && !(p in spare); p = parent[p]) spare[p] = 1
      for (p in parent) if (parent[p] == parent[self] && group[p] == group[self]) spare[p] = 1
      queue = self
      while (queue != "") {
        m = split(queue, batch, " "); queue = ""
        for (i = 1; i <= m; i++) {
          k = split(kids[batch[i]], ks, " ")
          for (j = 1; j <= k; j++) { spare[ks[j]] = 1; queue = queue " " ks[j] }
        }
      }
      for (p in hit) if (!(p in spare)) print p
    }' <<<"$procs"
}

pids=$(strays)
if [ -n "$pids" ]; then
  # shellcheck disable=SC2086 # one pid per word
  kill -TERM $pids 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    alive=""
    for pid in $pids; do kill -0 "$pid" 2>/dev/null && alive="$alive $pid"; done
    [ -n "$alive" ] || break
    sleep 0.5
  done
  # shellcheck disable=SC2086
  [ -z "${alive:-}" ] || kill -KILL $alive 2>/dev/null || true
  echo "stopped $(wc -w <<<"$pids" | tr -d ' ') stray process(es) still running from the tree"
fi

git -C "$main" worktree remove "$tree"
echo "removed worktree $tree"
