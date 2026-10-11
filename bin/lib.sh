# Shared helpers for the flow scripts. Sourced, never run.

die() { echo "flow: $*" >&2; exit "${FLOW_EXIT:-1}"; }

need() {
  local tool
  for tool in "$@"; do
    command -v "$tool" >/dev/null 2>&1 || die "$tool is not on PATH"
  done
}

now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

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

# The flow config: $FLOW_CONFIG, or flow.json in the current directory or a parent, or the config
# flow spawn last used for the repository the current directory belongs to (see remember_config),
# so flow gate and flow land find the brain from a project worktree.
find_config() {
  if [ -n "${FLOW_CONFIG:-}" ]; then
    [ -f "$FLOW_CONFIG" ] || die "FLOW_CONFIG does not exist: $FLOW_CONFIG"
    echo "$FLOW_CONFIG"; return
  fi
  local dir=$PWD key
  while :; do
    if [ -f "$dir/flow.json" ]; then echo "$dir/flow.json"; return; fi
    [ "$dir" = / ] && break
    dir=$(dirname "$dir")
  done
  if key=$(repo_key "$PWD") && [ -f "$(state_dir)/configs/$key" ] && [ -f "$(cat "$(state_dir)/configs/$key")" ]; then
    cat "$(state_dir)/configs/$key"; return
  fi
  die "no flow.json in $PWD or its parents and no config remembered for this repository; run from the driving brain or set FLOW_CONFIG"
}

# repo_key <dir>: one key for a repository and all its worktrees, from its common git directory.
repo_key() {
  local common
  common=$(git -C "$1" rev-parse --git-common-dir 2>/dev/null) || return 1
  common=$(cd "$1" && cd "$common" && pwd -P)
  echo "$common" | tr '/' '_'
}

# remember_config <checkout> <config>: lets find_config reach the config from that repository.
remember_config() {
  local key
  key=$(repo_key "$1") || return 0
  mkdir -p "$(state_dir)/configs"
  echo "$2" >"$(state_dir)/configs/$key"
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

# The file holding the flags accepted for a target, beside the gate results.
accepted_file() {
  local common
  common=$(cd "$(git rev-parse --git-common-dir)" && pwd)
  echo "$common/flow/accepted/$(echo "$1" | tr '/#' '__').json"
}

require_clean_tree() {
  [ -z "$(git status --porcelain)" ] || die "the working tree is not clean; commit or remove the changes first"
}

# The value of a "- **<Label>:** `value`" line of docs/agents/dev-loop.md.
# Prints every backtick span on the line, one per line.
dev_loop_values() {
  local file=docs/agents/dev-loop.md
  [ -f "$file" ] || return 0
  { grep -m1 -F -- "- **$1:**" "$file" || true; } | { grep -o '`[^`]*`' || true; } | sed 's/^`//; s/`$//'
}

# The "- " lines of the "## <Heading>" section of docs/agents/dev-loop.md, up to the next heading.
dev_loop_section() {
  local file=docs/agents/dev-loop.md
  [ -f "$file" ] || return 0
  awk -v h="## $1" '$0 == h { on = 1; next } /^## / { on = 0 } on && /^- /' "$file"
}

# matches_any <file> <globs>: does the file match one of the globs, one per line?
# A glob is matched against the full path and the file name; * spans directories.
matches_any() {
  local file=$1 name=${1##*/} glob
  while IFS= read -r glob; do
    [ -n "$glob" ] || continue
    # shellcheck disable=SC2254
    case $file in $glob) return 0 ;; esac
    # shellcheck disable=SC2254
    case $name in $glob) return 0 ;; esac
  done <<<"$2"
  return 1
}

# Where flow spawn keeps what it observed about each run, for flow ledger on the same host.
state_dir() { echo "${FLOW_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/flow}"; }

# The lead's herdr agent: FLOW_LEAD inside a spawned step, the calling pane in the lead's own session.
lead_agent() { echo "${FLOW_LEAD:-${HERDR_PANE_ID:-}}"; }

# tell_lead <agent> <line>: one line into the lead's session, the way run-end reports arrive.
# The lead rejects input while it is blocked on a prompt of its own, so retry for a while.
tell_lead() {
  local agent=$1 line=$2 attempt out
  for attempt in 1 2 3 4 5 6; do
    if out=$(herdr agent prompt "$agent" "$line" 2>&1); then return 0; fi
    sleep 10
  done
  echo "flow: could not reach the lead $agent: $(echo "$out" | head -3)" >&2
  return 1
}

# detach <log> <command...>: run the command in the background, free of the caller's shell and its
# pipes, so the caller returns at once. The command's output goes to the log.
detach() {
  local log=$1
  shift
  if command -v setsid >/dev/null 2>&1; then
    setsid nohup "$@" </dev/null >"$log" 2>&1 &
  else
    nohup "$@" </dev/null >"$log" 2>&1 &
  fi
  disown 2>/dev/null || true
}
