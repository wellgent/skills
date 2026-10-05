# Retro

Header: `FLOW.md`, stage 11.
Retro runs in a fresh lead session, so it judges the iteration from its records and not from memory of running it.

## Starting it

From the long-running lead session, at the client's close or on a trigger (exit 2 from `flow ledger bug` or `flow ledger check`):

```bash
pane=$(herdr tab create --cwd <driving brain> --label retro-<repo> --no-focus | jq -r '.. | objects | .pane_id? // empty' | head -1)
herdr agent start retro-<repo> --kind claude --pane "$pane" -- $(jq -r '.harness.claude[]' flow.json) "/lead <owner>/<repo> retro"
```

The Retro session reaches you with `herdr agent prompt` and you answer the same way.

## Running it

You are the fresh session. Read the card, the iteration map and `FLOW.md`, then:

1. `flow ledger fill <owner>/<repo>`, then `flow ledger rollup <owner>/<repo>`.
2. Sample transcripts on the run host by ledger outliers: the specs with the most Build runs, the most Review runs, the highest cost, and the origin spec of every escaped defect. Session ids are in the rows.
3. Read `retro` from the project's pinned skills as a file and run it over the ledger, the tracker and those transcripts.
   On a trigger, scope it to the bug or spec that raised it.
4. Route every candidate to exactly one of:
   - a mechanical violation → a deterministic check in the project's check command;
   - a judgment call → a rule in the project's `CODING_STANDARDS.md`;
   - a stage measure that got worse → a re-test trigger, written as a watch item;
   - a candidate tool, model or effort change → a trial ticket on the driving brain's tracker;
   - dropped, with the reason.
5. File each check and each standards rule as a ticket on the project tracker and hand the list to the long-running lead, which takes them through the single-bug path.
6. Every change to skill or flow text (the flow repo, the project's `AGENTS.md` and `docs/agents/dev-loop.md`) goes to the client in a Retro [round](rounds.md), one item each with the proposed diff and why.
   Apply what the client approves, reading `writing-for-agents` first; commit and push in the owning repo.
7. Post the Retro report from `templates/artifacts/retro-report.md` on the iteration map: the rollup as printed, where each escaped defect was found, the adopt-and-watch outcomes for items adopted at Readiness, the ranked candidates with their routing, and the text changes with the client's answers.
   At the client's close it is the map's closing comment.
8. `flow ledger stage retro <owner>/<repo> done <comment link>`; commit and push the ledger.
9. Tell the long-running lead the report link, then end.
