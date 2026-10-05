# The iteration

An iteration is one `wayfinder` map on the driving brain's tracker (`tracker` in `flow.json`) whose destination is a shipped outcome.
The map carries execution, so its Notes state that override.
It stays open after its destination is reached and absorbs bugs and small fixes until the client closes it.

## Open

1. Restate the input's destination in one or two lines and check it against the card and the brain's pages for the project.
2. Create the map per `wayfinder` with labels `wayfinder:map` and `lead:iteration`.
   Its Notes carry the card path, the skills the brain's `AGENTS.md` tells sessions to consult, and the facts the client gave with the input.
   An input issue (label `lead:input`) is linked from the Notes and closed once the map exists.
3. Set `projects["<owner>/<repo>"].iteration` in `flow.json` to the map's issue number; commit and push.
4. Run [Readiness](readiness.md).
5. Settle the destination with the client in the first round when it is not already sharp.

## Where state lives

Nothing about the iteration is kept in this session alone.

- The map body: destination, decisions so far, fog. Its comments: the readiness report, every round, the client's acceptance, the Retro report.
- The map's open child tickets: the open Shape decisions.
- The project tracker: each spec's issue with its brief or spec, UX notes, design record, findings and Release report; finding and bug tickets.
- The ledger file `ledger/<repo>/<iteration>.jsonl`: which stage every spec has reached.
- herdr: the sessions running now. The crontab: the tick.

## Resume

A fresh or compacted session reads, in order:

1. The card and the map body.
2. The map's comments from the last round on: an unanswered round is the open round.
3. The map's open child tickets.
4. The last ledger row per spec: `jq -s 'map(select(.spec)) | group_by(.spec) | map(last | {spec, kind, stage, outcome, verdict})' ledger/<repo>/<iteration>.jsonl`.
5. Each open spec issue's newest comments, for an artifact reported after that row.
6. `herdr agent list` for live `flow-` sessions, and `crontab -l` for the tick.

Then continue each spec at the step after its last row.
A spec whose last row is a spawned step with no live session and no artifact is a died run: spawn the step again.
A run-end line received with no ledger row gets its row now.

## Close

The client closes the iteration; reaching the destination does not.
When the destination is reached, say so in a round and keep the iteration open for bugs and small fixes until the client answers with the close.

1. Record the client's acceptance as one line in a comment on the map.
2. **Audit.**
   Run "The lead's part" of `~/repos/wellgent-skills/stages/audit/SKILL.md`: the scanner pass, the four audit steps and the two merged reports beside the ledger file.
   Triage every finding: a bug becomes a bug ticket with its origin spec, a structural candidate becomes a Shape candidate for the next iteration, a small cleanup becomes a single-invariant ticket in one cleanup spec for the next iteration's start, and anything else is closed with a reason in the merged report.
3. **Retro.** Append this session's row with `flow ledger lead <owner>/<repo> <this session's id>`, then start the Retro in a fresh session per [retro](retro.md). Wait for its report on the map and take the tickets it hands you through the single-bug path.
4. `flow tick disarm`.
5. Clear `projects["<owner>/<repo>"].iteration` in `flow.json`, update the card and the brain's pages for the project as the brain's `AGENTS.md` directs, commit and push.
6. Close the map.

## Redrawn destination

When the client moves the destination while the map is open, close the iteration on what shipped through the Close steps.
File the new destination as a `lead:input` issue carrying the open human-work issues, the known open points and the constraints.
The next lead session starts from that input.
