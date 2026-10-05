# Shared helpers for the flow scripts. Sourced, never run.

die() { echo "flow: $*" >&2; exit "${FLOW_EXIT:-1}"; }

need() {
  local tool
  for tool in "$@"; do
    command -v "$tool" >/dev/null 2>&1 || die "$tool is not on PATH"
  done
}

# Sets TARGET_REPO (<owner>/<repo>), TARGET_NAME (<repo>) and TARGET_ISSUE (may be empty).
parse_target() {
  case $1 in
    */*#*) TARGET_REPO=${1%%#*}; TARGET_ISSUE=${1##*#} ;;
    */*) TARGET_REPO=$1; TARGET_ISSUE= ;;
    *) die "target must be <owner>/<repo> or <owner>/<repo>#<issue>, got: $1" ;;
  esac
  TARGET_NAME=${TARGET_REPO##*/}
  case $TARGET_ISSUE in *[!0-9]*) die "issue must be a number, got: $TARGET_ISSUE" ;; esac
}

# The flow config: $FLOW_CONFIG, or flow.json in the current directory or a parent.
find_config() {
  if [ -n "${FLOW_CONFIG:-}" ]; then
    [ -f "$FLOW_CONFIG" ] || die "FLOW_CONFIG does not exist: $FLOW_CONFIG"
    echo "$FLOW_CONFIG"; return
  fi
  local dir=$PWD
  while :; do
    if [ -f "$dir/flow.json" ]; then echo "$dir/flow.json"; return; fi
    [ "$dir" = / ] && break
    dir=$(dirname "$dir")
  done
  die "no flow.json in $PWD or its parents; run from the driving brain or set FLOW_CONFIG"
}

# The remote main branch of the repo in the current directory.
main_branch() {
  local ref
  ref=$(git symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null) || ref=refs/remotes/origin/main
  echo "${ref#refs/remotes/origin/}"
}

# The directory holding gate results, shared by every worktree of the repo.
gate_dir() {
  local common
  common=$(cd "$(git rev-parse --git-common-dir)" && pwd)
  echo "$common/flow/gate"
}

require_clean_tree() {
  [ -z "$(git status --porcelain)" ] || die "the working tree is not clean; commit or remove the changes first"
}

# The value of a "- **<Label>:** `value`" line in the Gate section of docs/agents/dev-loop.md.
# Prints every backtick span on the line, one per line.
dev_loop_values() {
  local file=docs/agents/dev-loop.md
  [ -f "$file" ] || return 0
  { grep -m1 -F -- "- **$1:**" "$file" || true; } | { grep -o '`[^`]*`' || true; } | sed 's/^`//; s/`$//'
}

# Where flow spawn keeps what it observed about each run, for flow ledger on the same host.
state_dir() { echo "${FLOW_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/flow}"; }
