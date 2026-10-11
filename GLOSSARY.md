# The flow

The language of the development flow described in [`FLOW.md`](FLOW.md): who takes part, what runs, and what is recorded.

## Language

### People and places

**Lead**:
The agent session that works for the client on one project as product owner and tech lead, triages every intake, starts every step and answers every question from it.
The delivery lead runs tickets, specs and maps; the audit lead and the retro lead are the same session started for one occasional flow.
_Avoid_: Driver, orchestrator, coordinator

**Client**:
The person who starts the flow on a project and decides its destination, user-visible behaviour, acceptance, and when an Audit or a Retro runs.
_Avoid_: User, product owner, stakeholder

**Driving brain**:
The repository the lead runs from, holding the project cards, maps, flow config, ledger, request issues and the Audit and Retro reports.
_Avoid_: Home repo, control repo

**Run host**:
A machine holding the flow checkout, the harnesses and the session transcripts.

**Flow config**:
The driving brain's file naming its tracker, the model and effort of each step, and the fallback model for a step stalled at a usage limit.

**Source log**:
The record of every upstream source the flow depends on, with the last version seen and its date, which Readiness reviews in full.

### What runs

**Container**:
The unit work enters as and is tracked by: a ticket, a spec or a map.

**Ticket**:
The container for a one shot or a batch: an issue on the project tracker with no map and no request, answered to the client by one FYI line at land.

**Spec**:
The container for one grilled feature, carried through UX design, System design and Plan on one issue and one integration branch.
_Avoid_: PRD, epic, feature

**Map**:
The container for an iteration: a wayfinder map with a destination and several specs, opened only when a grilling produces fog.

**Iteration**:
One run of the flow on one map toward a destination the client set, open until the client closes it.
_Avoid_: Sprint, cycle, milestone

**Triage**:
The lead's two questions at intake and at every hand-off: can the diff be reviewed at a glance and thrown away cheaply, and does it touch anything hard to reverse. The answers pick the path: one shot, one shot with a design note, grill then build, or map.

**Pool triage**:
The triage run over every open issue of a project at once, sorting each into a batch, a spec, a request or a drop, written up as one triage report.

**One shot**:
A small, reversible change built in one `build` session with no alignment before it; the floor aligns on the diff.

**Design note**:
The lead's short note for a small change that touches a hard-to-reverse edge, naming the contract examples at that edge, checked by the second opinion before Build.

**Batch**:
Related tickets landed together: one branch, one gate, one Review, one QA pass; about ten tickets or 400 changed lines, grouped by surface or module. On the tracker, a parent issue labelled `batch` with the tickets as sub-issues.

**Landing**:
One pass of a change through the floor onto `main`: a one shot, a batch, or a spec.

**Stage**:
One part of the lifecycle with one owning role, one input artifact, one output artifact and a quality bar.
_Avoid_: Phase

**Step**:
One spawned session, started by the lead with `flow spawn`, with its own flow config entry.
_Avoid_: Task, job

**Stage run**:
One execution of one stage on one input.

**Second opinion**:
The same step run by the other model family, merged by the lead; runs on every design record and design note.

**Fix run**:
A Build run on Review or QA findings, which reviews its own diff with `code-review` and the correctness pass before it reports.

**Gate**:
The check the lead runs after Build: the project's check command and journey tests on the branch tip, the protected-change script on the whole diff, and the diff class.
_Avoid_: CI, pipeline

**Diff class**:
What the gate prints from the project's path lists to decide the floor's skips: prose only (no Review, no QA), no surface path (Review, no QA), or surface path (Review and QA).

**Surface path**:
A path in the project's `docs/agents/dev-loop.md` list whose change can reach what a user sees or does, so the landing gets a QA pass.

**Land**:
Fast-forwarding `main` to a commit the gate passed, which appends the health check row.
_Avoid_: Merge

**Conflict exit**:
A session stopping to report that the ticket, its tests or the spec disagree, or that it needs a decision the ticket lacks or touches a hard-to-reverse thing the ticket did not name, in place of deciding itself.

**Journey test**:
One browser test of a client-approved critical journey, run in the gate.

**Lens**:
A named judgment viewpoint a Review or Audit session applies, declared per project with its trigger.

**Health check**:
The scanner numbers of a landed commit, appended as a ledger row at every landing; the trend Readiness, the Audit and the Retro read.

**Audit**:
An occasional flow the client starts with `/lead <owner>/<repo> audit`: the defect review by both model families and the architecture review over the whole codebase, merged into one ranked report, put to the client as a request, with only the client's picks filed.

**Notable problem**:
An Audit finding above the bar: it has a concrete consequence at today's scale (a user or the agent hits it; data, money or authorization at risk) or is structure that makes a named kind of change expensive or risky. Everything else is counted, not itemized.

**Retro**:
An occasional flow the client starts with `/lead <owner>/<repo> retro`: the `retro` step over the ledger since the last Retro row, then the retro lead walking the client through the report and filing what the client accepts.

**Drop**:
Closing an issue as not worth doing, with one comment naming the reason class and the finding id.

### What is recorded

**Spec brief**:
The first body of a spec's issue: the slice of the destination, the client decisions it rests on, what is out, and whether it has a user-visible surface.

**Run-end report**:
The one line every spawned session sends the lead when it ends: step, target, outcome, artifact link, session id.

**Ledger**:
The append-only record of stage runs, gates, health checks and client decisions, in files per project in the driving brain.
_Avoid_: Log, journal

**Request**:
An issue on the driving brain's tracker labelled `lead:round` and assigned to the client, holding only decisions the lead cannot make, closed with the answer and its decision rows. Open requests across every driving brain are everything waiting on the client.
_Avoid_: Round, checkpoint, question

**FYI**:
A comment on a spec issue or a map telling the client a reversible call, an approved production write or a landed ticket; never assigned, no veto window, reversed whenever seen.

**Triage report**:
The pool triage's output: per ticket, batch, spec, decide or drop with a reason, and the counts per class; a comment on the pool's lead-input issue and the ledger's triage row.

**Status view**:
The read-only output of `flow status <owner>/<repo>`: the open containers, each spec's stage and live session, sessions waiting on the client or at a usage limit, open requests with their age, and cost so far.

**Decision basis**:
What a client decision was judged on: text, coded prototype or live data.

**Origin spec**:
The spec whose change introduced a bug.

**Escaped defect**:
A bug found after its origin spec's landing.
_Avoid_: Follow-up fix, regression

**Audit report**:
The one file an Audit leaves beside the ledger: the notable problems ranked with their consequence, counts by lens for the rest, finding ids, and the client's picks.

**Retro report**:
The one file a Retro leaves beside the ledger: the ledger rollup over the window, the escaped defects, the watch items, the candidates with their routing, and the flow text changes put to the client.
