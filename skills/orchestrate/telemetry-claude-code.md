# Telemetry mechanics: Claude Code as the driving harness

Claude Code shows no live cumulative counter in-session; the transcript on disk is the measured source.

## Driver + inline subagents

The driver transcript lives at `~/.claude/projects/<project-slug>/<session-id>.jsonl`, where `<session-id>` is the UUID in the session's scratchpad path.
Driver tokens have no ticket boundaries, so snapshots are cumulative by design: when one session ships several tickets, later analysis diffs consecutive snapshots sharing a session id to attribute per-ticket driver cost.
Inline subagent turns carry `isSidechain: true`, so one query splits driver from inline subagents:

```bash
jq -s '[.[] | select(.type=="assistant" and .message.usage != null)]
  | group_by(.isSidechain)
  | map({side: (if .[0].isSidechain then "subagents" else "driver" end),
     turns: length,
     input: map(.message.usage.input_tokens) | add,
     cache_read: map(.message.usage.cache_read_input_tokens // 0) | add,
     cache_creation: map(.message.usage.cache_creation_input_tokens // 0) | add,
     output: map(.message.usage.output_tokens) | add})' \
  ~/.claude/projects/<project-slug>/<session-id>.jsonl
```

## Background subagents

Background subagents never appear in the driver transcript: their totals arrive in their completion notifications and their transcripts sit under `~/.claude/projects/<project-slug>/<session-id>/subagents/agent-<id>.jsonl` - record the notification numbers, or sum those files with the same query when a notification is missing.
