# Client rounds

A **round** is how every client-owned decision reaches the client: one batch of numbered questions on the iteration map.
Send a round as soon as unblocking needs it; batch what is ready, and send a blocking question at once.

## Building a round

- Include only decisions from the client's side of the authority lines.
- Resolve every fact first. A question that needs a fact waits for the subagent finding it; the rest of the round goes now.
- Each question opens with the decision in one line, then the options, then your recommendation and its reason in one or two sentences.
- A decision about what the user sees is a design question (below) and is judged on a prototype link or live data, with what to look at.
- Close with FYI: reversible calls you made that the client may veto and production writes you approved, one line each.

```
❓ **Q1** - **<decision>**: <context and options>

➡️ <recommendation and reason>
```

## Design questions

A design question puts the UX design stage's coded options to the client, and the client picks before seeing what you would pick.

1. Label the options neutrally (A, B, C), each with its prototype link and its verified critique findings. No option is marked as preferred.
2. Seal your recommendation before the round is posted: `flow ledger rec <owner>/<repo>#<spec> --round <n> "<recommendation>"`, then commit and push the ledger. `<n>` counts the spec's design rounds from 1.
3. Post the question with no ➡️ line.
4. After the client's pick, reply with the sealed recommendation.
   A verified P0 or P1 finding or a conflict with the spec brief in the picked option is raised in that reply.
   A pick the client changes after it is a new decision.
5. Send the pick to the waiting designer session.

## Delivering a round

1. Post the round as one comment on the iteration map, headed `Round <n>`.
2. Show the same round in this session and end your turn on it, so the harness notifies the client.
3. Keep working everything the round does not block.

## Answers

The client answers in this session or in a reply to the round comment; check both on every tick.

1. Reply on the round with one line per decision, each with its **decision basis**: `text`, `prototype` or `live data`.
   A decision that undoes an earlier one links it.
   A design pick that departs from `PRODUCT.md` or `DESIGN.md` adds the line the designer reports: "this pick overrides <rule>; `<file>` now says <new rule>".
2. Append one row per decision: `flow ledger decision <owner>/<repo>#<spec> --basis <basis> --link <reply link> "<gist>"`, with `--reverses` for a reversal and `--options <n> --pick <as-offered|mixed|redo> --round <n>` for a design pick.
   A decision that belongs to no spec takes `<owner>/<repo>` as its target.
3. Resolve the map ticket each answer settles, and answer every session waiting on it.

## Human work

Work only the client or another person can do (an account, a dashboard change, a test on a real device) becomes one issue on the project tracker labelled `needs-human`.
It carries everything needed to do the work without this session: why, what exists, access and boundaries, what to have ready, checkbox steps naming who does each, rollback, and a done-when line.
It opens with how to start: a lead session and the words "let's do <issue>", so the person drives it with you and you run every step an agent can.
