# The triage

Header: `FLOW.md`, "The triage" and stage 2.
The triage is how every piece of work enters, and how it is re-checked at every hand-off: when a brief is done, when a design note or record is approved, when a Build run reports.
It takes minutes, from the issue and the code, and never waits on the client.

## The two questions

1. Can the diff be reviewed at a glance and thrown away cheaply if wrong?
2. Does it touch anything hard to reverse: stored-data shape or a migration, an external contract (MCP tools, agent skills, a public API), money, authorization, a production delete?

Answer from the code the change touches, not from the issue's size estimate: read the modules it reaches and the path lists in `docs/agents/dev-loop.md`.

## The four paths

| Q1 small | Q2 hard to reverse | Path |
| --- | --- | --- |
| yes | no | One shot |
| yes | yes | One shot with a design note |
| no | either | Grill, then build |
| fog | either | Map |

- **One shot**: a ticket. Go to [landing](landing.md) with the ticket as the target; alignment happens after, on the diff.
- **One shot with a design note**: a ticket. Write the design note and get its second opinion per [spec](spec.md), "The design note", then [landing](landing.md).
- **Grill, then build**: a spec. Shape on the spec's issue per [shape](shape.md) until the brief has no open decision, then UX design, System design and Plan per [spec](spec.md), then [landing](landing.md).
- **Map**: only when Shape produces fog, never at intake. Open the iteration per [iteration](iteration.md).

A grilled brief that turns out small is de-escalated: the brief becomes the ticket's body, and the ticket takes the one-shot path, with a design note when its edge is hard to reverse.

## Escalation

A build session escalates by conflict exit only for a decision its ticket lacks or a hard-to-reverse thing its ticket did not name.
Size alone never escalates mid-build.
On such an exit, re-triage: give the ticket the decision or the design note it lacks and send it back to Build, or move it to the grill-then-build path with the Build run's branch as input.

## Bug tickets

A bug ticket is a ticket: the two questions pick its path, and its Build run runs `diagnosing-bugs` first.
At intake set its **origin spec**: `git blame` on the lines at fault names the spec that landed them, `unknown` when the cause predates the flow.
Write it in the ticket's origin field and, when the origin spec is released, append `flow ledger bug <owner>/<repo>#<bug> --origin <spec> --found <date> [--area authorization|money|data-integrity]`.

## Batches

Related tickets land together: one branch, one gate, one Review, one QA pass.
Size a batch at about ten tickets or 400 changed lines, grouped by surface or module, so one Review run reads it whole and one fix run covers its findings.

1. Open a parent issue on the project tracker labelled `batch`, with the tickets as sub-issues; it is the target of `flow spawn`, the gate and the ledger.
2. Its tickets are `ready-for-agent` while the batch is open and close with it.
3. A ticket that hits a decision leaves the batch by conflict exit: the batch lands without it, and the ticket is re-triaged on its own.

A batch takes [landing](landing.md) like a one shot.
