# Runner: codex exec takes

Takes run as fresh `codex exec` sessions; the driver stays in its own harness and gates as usual.
A project selects this runner by naming it in its dev-loop contract's implementer section (`Takes: codex exec`).

## Spawn

Prompt from a temp file, stdout to files; the driver's context takes only the `-o` report and grepped specifics from the event stream:

```bash
P=$(mktemp)
cat >"$P" <<'EOF'
<the take prompt>
EOF
codex exec --yolo --json \
  -c model_reasoning_effort="xhigh" \
  -o <scratch>/take-<N>-1.md - <"$P" \
  > <scratch>/take-<N>-1.jsonl 2> <scratch>/take-<N>-1.err
SID=$(jq -r 'select(.type=="thread.started").thread_id' <scratch>/take-<N>-1.jsonl | head -1)
```

Model comes from the machine's Codex config unless the repo's contract pins one.
Long takes run in the background; collect the `-o` file on exit, and let quiet runs under 30 minutes keep working.

## Bounce

Bounces resume the same session - cheaper than fresh, and the take's context survives (`resume` has no `--yolo` shorthand):

```bash
codex exec resume "$SID" --dangerously-bypass-approvals-and-sandbox --json \
  -o <scratch>/take-<N>-2.md - <"$P2" > <scratch>/take-<N>-2.jsonl 2> <scratch>/take-<N>-2.err
```

## Operational notes

- Auth is host-level and fails only at token-refresh time; `codex login status` can still report logged-in on a revoked refresh token.
  A take dying at token-zero with HTTP 401 `refresh_token_invalidated` needs a human `codex login` - escalate, do not retry.
- A capacity error surfaces as a dead `turn.failed` launch with an empty take report - relaunch with the same prompt.
