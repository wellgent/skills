#!/usr/bin/env bash
# flow spawn starts no second session beside a first one herdr never named.
# Replays ~/.local/state/flow/runs/flow-ammmazing-build-1272-184557.start.log: herdr agent start
# timed out, the poll saw no agent in the pane, and a second session started although the first
# was working and reported. A fake herdr on PATH plays herdr's side; run with
#   bash tests/flow-spawn-second-session.sh
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin" "$work/checkout"

cat >"$work/bin/herdr" <<'FAKE'
#!/usr/bin/env bash
# Fake herdr: logs each call, answers agent start with a timeout and never names an agent.
echo "$*" >>"$FAKE_LOG"
case "$1 $2" in
  "workspace list") echo '{"result":{"workspaces":[{"label":"r-flow","workspace_id":"wT"}]}}' ;;
  "tab create")
    n=$(( $(grep -c '^tab create' "$FAKE_LOG") ))
    echo "{\"result\":{\"root_pane\":{\"pane_id\":\"wT:p$n\"},\"tab\":{\"tab_id\":\"wT:t$n\"}}}" ;;
  "tab get") if grep -qx "tab close $3" "$FAKE_LOG"; then echo '{"error":{"code":"not_found"}}'; else echo '{"result":{}}'; fi ;;
  "tab close") echo '{"result":{}}' ;;
  "agent start")
    # The first session goes straight to work and, in the reported case, ends during the wait.
    [ "$FAKE_CASE" != reported ] || touch "$FLOW_STATE/runs/$3.reported"
    echo '{"error":{"code":"timeout","message":"timed out waiting for agent startup"},"id":"cli:agent:start"}'
    exit 1 ;;
  "agent get") echo '{"result":{}}' ;;
  "pane process-info")
    if [ "$FAKE_CASE" = running ]; then
      echo '{"result":{"process_info":{"foreground_processes":[{"argv0":"claude","argv":["claude","-n","x"],"name":"2.1.296"}]}}}'
    else
      echo '{"result":{"process_info":{"foreground_processes":[{"argv0":"-zsh","argv":["-zsh"],"name":"zsh"}]}}}'
    fi ;;
  *) echo '{"result":{}}' ;;
esac
FAKE
chmod +x "$work/bin/herdr"

cat >"$work/flow.json" <<JSON
{"projects": {"o/r": {"checkout": "$work/checkout"}},
 "harness": {}, "steps": {"build": {"model": "claude-test", "effort": "high"}}}
JSON

fail=0
# check <case> <expected agent starts> <expected outcome>
check() {
  local case=$1 starts=$2 outcome=$3 got_starts got_outcome
  export FAKE_CASE=$case FAKE_LOG=$work/$case.log FLOW_STATE=$work/state-$case
  : >"$FAKE_LOG"
  PATH="$work/bin:$PATH" FLOW_CONFIG=$work/flow.json FLOW_SPAWN_POLL_SECONDS=0 \
    "$root/bin/flow" spawn build "o/r#1" --lead wL:p0 --wait >"$work/$case.out" 2>&1 || true
  got_starts=$(grep -c '^agent start' "$FAKE_LOG" || true)
  got_outcome=$(jq -r .start "$FLOW_STATE"/runs/*.json)
  if [ "$got_starts" = "$starts" ] && [ "$got_outcome" = "$outcome" ]; then
    echo "ok   $case: $got_starts agent start, $got_outcome"
  else
    echo "FAIL $case: expected $starts agent start and $outcome, got $got_starts and $got_outcome"
    sed 's/^/     /' "$work/$case.out"
    fail=1
  fi
}

check running 1 started
check reported 1 started
check dead 2 failed
exit $fail
