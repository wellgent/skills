# The flow

The language of the development flow described in [`FLOW.md`](FLOW.md): who takes part, what runs, and what is recorded.

## Language

### People and places

**Lead**:
The agent session that runs an iteration as product owner and tech lead, starts every step and answers every question from it.
_Avoid_: Driver, orchestrator, coordinator

**Client**:
The person who starts the flow on a project and decides its destination, user-visible behaviour and acceptance.
_Avoid_: User, product owner, stakeholder

**Driving brain**:
The repository the lead runs from, holding the project cards, iteration maps, flow config, ledger and Audit reports.
_Avoid_: Home repo, control repo

**Run host**:
A machine holding the flow checkout, the harnesses and the session transcripts.

**Flow config**:
The driving brain's file naming its tracker and the model and effort of each step.

**Source log**:
The record of every upstream source the flow depends on, with the last version seen and its date, which Readiness reviews in full.

### What runs

**Iteration**:
One run of the flow on one project toward a destination the client set, open until the client closes it.
_Avoid_: Sprint, cycle, milestone

**Stage**:
One part of the lifecycle with one owning role, one input artifact, one output artifact and a quality bar.
_Avoid_: Phase

**Step**:
One spawned session, started by the lead with `flow spawn`, with its own flow config entry.
_Avoid_: Task, job

**Stage run**:
One execution of one stage on one input.

**Spec**:
One slice of the destination, carried through the per-spec stages on one integration branch and one issue.
_Avoid_: PRD, epic, feature

**Second opinion**:
The same step run by the other model family, merged by the lead.

**Gate**:
The check the lead runs between Build and Review: the project's check command on the branch tip plus the protected-change script on the whole spec diff.
_Avoid_: CI, pipeline

**Land**:
Fast-forwarding `main` to a commit the gate passed.
_Avoid_: Merge

**Conflict exit**:
A session stopping to report that the ticket, its tests or the spec disagree, in place of making them agree.

**Journey test**:
One browser test of a client-approved critical journey, run in the gate.

**Lens**:
A named judgment viewpoint a Review or Audit session applies, declared per project with its trigger.

### What is recorded

**Spec brief**:
The first body of a spec's issue: the slice of the destination, the client decisions it rests on, what is out, and whether it has a user-visible surface.

**Run-end report**:
The one line every spawned session sends the lead when it ends: step, spec, outcome, artifact link, session id.

**Ledger**:
The append-only record of stage runs and client decisions, one file per iteration in the driving brain.
_Avoid_: Log, journal

**Decision basis**:
What a client decision was judged on: text, coded prototype or live data.

**Origin spec**:
The spec whose change introduced a bug.

**Escaped defect**:
A bug found after its origin spec's Review and QA closed.
_Avoid_: Follow-up fix, regression
