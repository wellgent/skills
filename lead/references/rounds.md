# Requests

Header: `FLOW.md`, "The lead session".
A **request** is how every client-owned decision reaches the client: one issue on the driving brain's tracker (`tracker` in `flow.json`), labelled `lead:round`, assigned to the client, linked from the container it belongs to.
The issue is always the record; the pane mirrors it and never replaces it.

## Building a request

- Include only decisions the lead cannot make: user-visible behaviour with real alternatives, money, an irreversible production write, a flow or skill text change, acceptance and the close.
- Resolve every fact first. A question that needs a fact waits for the subagent finding it; the rest of the request goes now.
- Each question opens with the decision in one line, then the options, then your recommendation and its reason in one or two sentences.
- Name the **decision basis** each question is judged on: text when the client can picture the choice from the question; a prototype link or live data, with what to look at, when the options are visual or at interaction level.
- Open with the status view, as `flow status <owner>/<repo>` prints it.

The body is `templates/artifacts/request.md`.

## Design questions

A design question puts the UX design stage's coded options to the client, and the client picks before seeing what you would pick.

1. Label the options neutrally (A, B, C), each with its prototype link and its verified critique findings. No option is marked as preferred.
2. Seal your recommendation before the request is posted: `flow ledger rec <owner>/<repo>#<spec> --round <n> "<recommendation>"`, then commit and push the ledger. `<n>` counts the spec's design rounds from 1.
3. Post the question with `sealed` in place of the ➡️ line.
4. After the client's pick, reply with the sealed recommendation.
   A verified P0 or P1 finding or a conflict with the spec brief in the picked option is raised in that reply.
   A pick the client changes after it is a new decision.
5. Send the pick to the waiting designer session.

## Delivering a request

1. Create the issue with `gh issue create --label lead:round --assignee <client>`, link it from the container (a comment on the map, the spec issue or the ticket), and show the same text in this session.
2. Work everything the request does not block. When nothing independent is left, end your turn and wait.
   A request has no timeout and no default; `go` takes every recommendation.
3. The tick reports a new comment on an open request; check every open request on each tick as well.

## Answers

The client answers on the issue or in the pane.

1. On the issue, post one line per decision with its basis: `text`, `prototype` or `live data`.
   An answer given in the pane gets this comment before you continue; a partial answer keeps the issue open with the remaining questions restated at the top.
   A decision that undoes an earlier one links it.
   A design pick that departs from `PRODUCT.md` or `DESIGN.md` adds the line the designer reports: "this pick overrides <rule>; `<file>` now says <new rule>".
2. Append one row per decision: `flow ledger decision <target> --basis <basis> --link <comment link> "<gist>"`, with `--reverses` for a reversal and `--options <n> --pick <as-offered|mixed|redo> --round <n>` for a design pick.
   A decision that belongs to no spec takes `<owner>/<repo>` as its target.
3. Close the request issue, resolve the map ticket each answer settles, then answer every session waiting on it.

Anything the client says in the pane that decides or directs, outside an open request, gets a request issue opened and closed with that comment and its decision row before you continue.

## FYI

A reversible call you made, a production write you approved, a landed ticket or batch: one comment on the spec issue, on the ticket or batch issue, or on the map for iteration-level matters.
Never assigned, no veto window; the client reverses it whenever seen, and the reversal is a decision row with `--reverses`.

## Human work

Work only the client or another person can do (an account, a dashboard change, a test on a real device) becomes one issue on the project tracker labelled `needs-human`.
It carries everything needed to do the work without this session: why, what exists, access and boundaries, what to have ready, checkbox steps naming who does each, rollback, and a done-when line.
It opens with how to start: a lead session and the words "let's do <issue>", so the person drives it with you and you run every step an agent can.
