# The iteration

An iteration is one `wayfinder` map on the driving brain's tracker (`tracker` in `flow.json`) whose destination is a shipped outcome.
It is opened only from fog: a grilling per [shape](shape.md) that leaves more than one spec's worth of open decisions.
The map carries execution, so its Notes state that override.
It stays open after its destination is reached and absorbs bugs and small fixes until the client closes it.

## Open

1. Restate the destination in one or two lines and check it against the card and the brain's pages for the project.
2. Create the map per `wayfinder` with labels `wayfinder:map` and `lead:iteration`.
   Its Notes carry the card path, the skills the brain's `AGENTS.md` tells sessions to consult, and the facts the client gave with the input.
   An input issue (label `lead:input`) is linked from the Notes and closed once the map exists.
3. Set `projects["<owner>/<repo>"].iteration` in `flow.json` to the map's issue number; commit and push.
   Rows of the iteration's specs and tickets go to `ledger/<repo>/<iteration>.jsonl` from here on.
4. Post the readiness report of this session as a comment on the map.
5. Settle the destination with the client in the first request when it is not already sharp.

## Where state lives

Nothing about the iteration is kept in this session alone.

- The map body: destination, decisions so far, fog. Its comments: the readiness report, the links to its requests, the FYIs, the client's acceptance.
- The request issues (`lead:round`) linked from the map or its specs: what waits on the client.
- The map's open child tickets: the open Shape decisions.
- The project tracker: each spec's issue with its brief or spec, UX notes, design record, findings and Release report; tickets and batches with their Build run, gate, findings and FYI; finding and bug tickets.
- The ledger file `ledger/<repo>/<iteration>.jsonl`: which stage every target has reached.
- herdr: the sessions running now. The crontab: the tick. `flow status <owner>/<repo>` reads them all.

## Resume

A fresh or compacted session reads, in order:

1. The card and the map body.
2. `flow status <owner>/<repo>`: the targets in flight, the live sessions, the open requests.
3. The open request issues: an unanswered one is still open; one with an answer is closed per [requests](rounds.md) first.
4. The map's open child tickets.
5. The last ledger row per target: `jq -s 'map(select(.spec)) | group_by(.spec) | map(last | {spec, kind, stage, outcome, verdict})' ledger/<repo>/<iteration>.jsonl`.
6. Each open target issue's newest comments, for an artifact reported after that row.
7. `herdr agent list` for live `flow-` sessions, and `crontab -l` for the tick.

Then continue each target at the step after its last row, per [spec](spec.md) or [landing](landing.md).
A target whose last row is a spawned step with no live session and no artifact is a died run: spawn the step again.
A run-end line received with no ledger row gets its row now.

## Close

The client closes the iteration; reaching the destination does not.
When the destination is reached, say so in a request and keep the iteration open for bugs and small fixes until the client answers with the close.

1. Record the client's acceptance as one line in a comment on the map.
2. `flow ledger lead <owner>/<repo> <this session's id>`; commit and push the ledger.
3. Clear `projects["<owner>/<repo>"].iteration` in `flow.json`, update the card and the brain's pages for the project as the brain's `AGENTS.md` directs, commit and push.
4. Close the map.
5. `flow tick disarm` when nothing else is in flight.

No Audit and no Retro run at the close: the client starts either as its own flow, and the next session start report carries the advise line if a trigger holds.

## Redrawn destination

When the client moves the destination while the map is open, close the iteration on what shipped through the Close steps.
File the new destination as a `lead:input` issue carrying the open human-work issues, the known open points and the constraints.
The next lead session starts from that input.
