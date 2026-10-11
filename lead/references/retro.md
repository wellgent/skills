# The Retro

Header: `FLOW.md`, stage 11. The `retro` step's part is `stages/retro/SKILL.md`.
You are the **retro lead**: this session was started with `/lead <owner>/<repo> retro`, by the client.
A Retro reads the ledger since the last Retro, finds what to change in the checks, the standards and the flow itself, and lands what the client accepts; it never blocks delivery, which may run beside it.
Readiness has run and its advise line is `none`.

## 1. Spawn the step

```bash
flow spawn retro <owner>/<repo> --note "report: <driving brain>/ledger/<repo>/retro-<YYYY-MM-DD>.md"
flow tick arm
```

The path is absolute; the step writes the report there and leaves committing it to you.
At its run-end report append the row with `flow ledger run '<the line>'`.

## 2. Check the report

The report meets the stage's quality bar when every rollup section is in, every escaped defect and watch item has its line, and every candidate has one route and its evidence.
Fill a gap yourself from the ledger, the tracker and the transcripts, or respawn the step with `--note` naming the gap.
Re-route a candidate you judge differently, and say why in its line.

## 3. Walk the client through it

In this pane, go through the report with the client: what the window shows against the one before, what is notable, and what you would act on, candidate by candidate.
The client may re-route any candidate or drop it.
Anything the client says that decides or directs is recorded per [requests](rounds.md) before you continue.

## 4. Act on each route

- **Check** and **standard**: one one-shot ticket each on the project tracker, labelled `ready-for-agent`, holding the candidate, its evidence and the check or the rule as it should read. A delivery lead session lands them through the floor.
- **Flow text change**: one request per [requests](rounds.md) for all of them, one question per change with its proposed diff and why, basis text; this session opens it itself. Wait for the answer as the waiting rule says.
  - Accepted in the flow repo (`FLOW.md`, a stage or lead skill, a template): read `writing-for-agents`, edit, commit and push in `~/repos/wellgent-skills`.
  - Accepted in the project (`AGENTS.md`, `docs/agents/dev-loop.md`): a one-shot ticket holding the accepted diff, landed through the floor like a check.
  - Declined: its decision row is the record.
- **Watch item**: stays in the report, where the next Readiness and the next Retro read it.
- **Dropped**: stays in the report with its reason.

Write each candidate's "Outcome" in the report: the ticket, the pushed commit, or the request that declined it.

## 5. End

1. Commit and push the report in the driving brain.
2. `flow tick disarm`, then `flow ledger lead <owner>/<repo> <this session's id> --stage retro`; commit and push the ledger. This row is the Retro row the next window starts from.
3. Tell the client the report's path and the filed tickets, then end.
