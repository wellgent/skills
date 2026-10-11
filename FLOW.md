# The flow

The development flow on one page: how work enters, the alignment it gets before build, the floor it passes after build, and the eleven stages with one owning role, one input, one output and a quality bar each, with the artifacts handed between them.
Terms in bold on first use are defined in [`GLOSSARY.md`](GLOSSARY.md).
Each stage skill opens with its header from this page; this page is the source of truth for the headers.

## How it runs

- The **lead** works for a **client** on one project, from a **driving brain**, in one always-on session.
- Work enters as a **container**: a **ticket**, a **spec** or a **map**. Every container ends in one or more **landings**, and every landing passes the same floor.
- A **stage** has one owning role, one input artifact, one output artifact and a quality bar. It runs in fresh sessions, so it can be replayed and improved on its own.
- A **step** is one session the lead starts with `flow spawn <step> <target>`. Its model and effort come from the **flow config**; an empty entry inherits the lead's.
- Every spawned session ends with a **run-end report** to the lead. A session with a question or a **conflict exit** asks the lead the same way and waits for the reply.
- Only the lead session holds production credentials. Every production read or write goes through the lead.
- A skill runs only when a step's stage skill or the project's `AGENTS.md` names it by path or step.
- Stage skills name no stack and no project. Stack rules, lenses, tools and path lists are declared in each project's `AGENTS.md`, `docs/agents/dev-loop.md` and `CODING_STANDARDS.md`.

The flow has two halves.
Before build, alignment scaled to the cost of being wrong: nothing, a design note, a grilled brief with a design record, or a map.
After build, a floor that never drops, whatever the path.

```
ticket   triage -> [design note + second opinion] -> Build -> floor -> Release
spec     Shape -> [UX design] -> System design + second opinion -> Plan -> Build -> floor -> Release
map      Shape -> spec, spec, spec ...
floor    gate -> Review until clean -> QA on a surface path -> ledger row
```

### The triage

The lead answers two questions at intake and again at every hand-off:

1. Can the diff be reviewed at a glance and thrown away cheaply if wrong?
2. Does it touch anything hard to reverse: stored-data shape or a migration, an external contract (MCP tools, agent skills, a public API), money, authorization, a production delete?

The answers pick one of four paths:

- **One shot** (small, reversible): one `build` session, then the floor. Alignment happens after, on the diff.
- **One shot with a design note** (small, hard to reverse): the lead writes a **design note** naming the contract examples at the hard-to-reverse edge, the **second opinion** checks it, then the one-shot path.
- **Grill, then build** (a larger diff): Shape with the client until the brief has no open decision, UX design when the brief names a surface with real alternatives, System design with a second opinion, Plan, Build, then the floor.
- **Map** (fog): a grilling that produces fog becomes a map with several specs. Never the entry point.

A build session escalates by conflict exit only when it needs a decision its ticket lacks or touches a hard-to-reverse thing its ticket did not name.
Size alone never escalates mid-build.
The lead de-escalates when a grilled brief turns out small.

A request to work through the open issues enters as a **pool triage**: the lead sorts every open issue by the two questions into batches, specs, one request for the decisions it cannot make, and **drops**, writes one **triage report**, then runs the batches in its own order and opens the specs.

### The floor

Runs once per landing, on every path:

- `flow gate`: the check command, the journey tests, the protected-change script, and the **diff class** it prints.
- Review by the other model family (`code-review` plus the correctness pass) until clean. A **fix run** reviews its own diff the same way before it reports.
- QA, one pass, when the diff touches a **surface path**.
- A ledger row for every stage run, and an **origin spec** on every bug ticket.
- Standards, through the `AGENTS.md` must-read list and `CODING_STANDARDS.md`.

The only skips are mechanical.
The gate prints the diff class from the path lists in the project's `docs/agents/dev-loop.md`:

- **Prose only** (docs, ADRs, comments, copy strings; no code or test file): no Review, no QA; the lead lands on the gate.
- **No surface path**: Review, no QA.
- **Surface path**: Review and QA.

The lead waives nothing.
Its judgment goes into sizing the landing: related tickets land as one **batch** (one branch, one gate, one Review, one QA pass), about ten tickets or 400 changed lines, grouped by surface or module.
A ticket that hits a decision leaves the batch by conflict exit, and the batch lands without it.

### Containers

- **Ticket**: a **one shot** or a batch, on the project tracker. No map and no request; one **FYI** line to the client at land with the ticket list and the link to see it.
- **Spec**: one grilled feature. Its requests, design record and findings live on its issue. No map.
- **Map**: an **iteration** with a destination and several specs, opened only from fog.

The ledger rows of every container feed the next Retro.

### The lead session

- Readiness runs at every lead session start.
- A **request** for the client is one issue on the driving brain's tracker, labelled `lead:round`, assigned to the client, linked from its container and closed when answered. It holds only decisions the lead cannot make: user-visible behaviour with real alternatives, money, an irreversible production write. The issue is always the record; nothing is asked in the pane alone, and anything the client says in the pane that decides or directs gets its comment and its decision row before the lead continues.
- Text is an allowed **decision basis** when the client can picture the choice from the question; a prototype or live data is required when the options are visual or at interaction level.
- An FYI is a comment on the spec issue, or on the map for iteration-level matters: a reversible call, an approved production write, a landed ticket. It is never assigned and has no veto window; the client reverses it whenever seen, and the reversal is a decision row.
- With a request open the lead works everything the request does not block, then ends its turn and waits. A request has no timeout and no default; the lead may offer a one-word `go` that takes every recommendation.
- `flow spawn` and `flow gate` return at once and deliver their result to the lead's pane the way run-end reports arrive; `flow ledger` appends and pushes.
- The tick, every 30 minutes, is the safety net: it nudges the lead session, reads the open requests for an answer and reports stalled sessions. A spawned step stalled at a usage limit waits at most 30 minutes, then the lead respawns it on the flow config's fallback model at the same effort; the lead session itself switches to the fallback when stalled.
- `flow status <owner>/<repo>` is the read-only **status view**. The lead prints it at the top of every request and as the reply to any status question; the client runs it in any shell on a run host.

### Occasional flows

Nothing starts an Audit or a Retro except the client.

- A **health check** row of scanner numbers is appended by `flow land` at every landing: no model, no tickets. It is the trend that Readiness, the Audit and the Retro read.
- **Audit**: `/lead <owner>/<repo> audit` opens an **audit lead** session. It pins a commit, spawns the defect review by both model families and the architecture review by the primary family, merges one ranked **Audit report** of every **notable problem** with counts by lens for the rest, puts it to the client as a request, and files only what the client picks.
- **Retro**: `/lead <owner>/<repo> retro` opens a **retro lead** session. It spawns the `retro` step over the ledger since the last Retro row, walks the client through the **Retro report**, and files what the client accepts.
- The delivery lead advises one of them in a single line of its session start report, with the number behind it: the health check trending the wrong way over the window, an **escaped defect** in authorization, money or data integrity, a project with no Audit, or many landings since the last Retro. No reminder after that line.
- Neither flow runs inside or at the close of a delivery iteration, and neither blocks delivery. Every occasional-flow session appends its own ledger row before it ends.

## Steps

The flow config holds one entry per spawned step, and a `fallback` entry for a step respawned after a usage limit.
Stages the lead runs itself have no entry.

- `ux-design`: UX design.
- `system-design`, `system-design-second`: System design and its second opinion.
- `grooming`: the ticket graph, inside Plan.
- `build`: Build. Everything inside the session runs on its model and effort.
- `review`: Review.
- `qa`: QA.
- `audit`, `audit-second`: the Audit defect review, one per model family.
- `audit-architecture`: the Audit architecture review, by the primary family.
- `retro`: the Retro over the ledger.

## Stage headers

### 1. Readiness

- **Role:** lead.
- **Runs:** at every lead session start.
- **Input:** the **source log**, the latest Audit report and Retro report when they exist, the health check rows, usage on both harnesses, host load.
- **Output:** readiness report, the session start report.
- **Quality bar:** the report is green: every source reviewed, regular updates applied, major changes decided by the client, the four targets (flow repo, brain, project, host) current, usage headroom on both harnesses for the planned work, host load within the planned parallelism; one advise line for an Audit or a Retro when a trigger holds.
- **Tools:** the setup skills, the source log, `flow ready`, `writing-for-agents` for skill edits.

### 2. Shape

- **Role:** lead as product owner; the client decides through request issues.
- **Runs:** at the intake of a ticket (the triage), on a spec's issue, or on a map.
- **Input:** the client's destination or request, the readiness report, the latest Audit report, the open issues of a pool.
- **Output:** the triage path for a ticket; one **spec brief** per feature with no open product decision left; a map from fog.
- **Quality bar:** every user-visible behaviour in a brief has a client decision with its decision basis; a request holds only what the lead cannot decide; work independent of an open request never waits for it.
- **Tools:** `wayfinder` for a map, the `grilling` round format, `domain-modeling`, `research` in subagents.

### 3. UX design

- **Role:** designer (step `ux-design`).
- **Runs:** per spec whose brief names a surface with real alternatives; skipped and logged otherwise.
- **Input:** the spec brief, `PRODUCT.md`, `DESIGN.md`, "Running the app" in `docs/agents/dev-loop.md`.
- **Output:** the chosen prototype (branch) and UX notes.
- **Quality bar:** no open P0 or P1 finding verified on the page, the design-system lint green, every option inside the design system; scores recorded, not gated.
- **Tools:** impeccable `doctor`, `shape`, per-option `critique`, `audit`, rendered `detect`; `init` and `document` when the preconditions are missing; the project's prototype host.

### 4. System design

- **Role:** architect (step `system-design`) for a design record; the lead for a design note; `system-design-second` on every record and note.
- **Runs:** per spec, after UX design; per one shot with a design note, before Build.
- **Input:** the spec brief or the ticket, UX notes, existing ADRs, the latest Audit report's architecture problems for the modules touched.
- **Output:** a design record plus an ADR per hard-to-reverse call, or a design note; the second opinion merged into it.
- **Quality bar:** the lead approves; the second opinion is merged; behavioural contracts exist wherever the change touches authorization, money or data integrity; contract examples are written as literal values and cover the three cases: one example per combination of the stored rows an operation decides from (or the reason a combination cannot occur), for a read bounded at N the value of N, what a caller gets past N and every schema, skill or doc that promises the whole list, and behaviour only a browser shows (navigation, history, scroll, focus) as observable cases with a browser test as its seam.
- **Tools:** `codebase-design` (design-it-twice on module-shaping calls), `domain-modeling`.

### 5. Plan

- **Role:** lead writes the spec; groomer cuts tickets (step `grooming`).
- **Runs:** per spec.
- **Input:** the spec brief, UX notes, design record.
- **Output:** the spec and its ticket graph.
- **Quality bar:** the lead approves the ticket graph; every contract example and every UX state is covered by a ticket; blocking edges serialize work that cannot run in parallel.
- **Tools:** `to-spec`, `to-tickets`.

### 6. Build

- **Role:** implementers inside one session (step `build`); the lead runs the **gate**.
- **Runs:** per landing (a one shot, a batch or a spec), and as a fix run for each batch of Review or QA findings.
- **Input:** one ticket, a batch, or the spec and its ticket graph; the design note when one exists; the design branch for a spec.
- **Output:** the branch tip with every ticket merged, a Build run comment, and a gate result with its diff class.
- **Quality bar:** `flow gate` passes on the branch tip: the check command and the journey tests green, the protected-change script clean on the whole diff; a fix run has run `code-review` plus the correctness pass on its own diff and fixed what it confirms; a session that changes files has the check green before it reports, a session that changes none runs no check; a decision the ticket lacks or a hard-to-reverse thing it did not name is a conflict exit; an answer that departs from a contract example, an invariant or an ADR sentence names that sentence and its new wording, and the fix run edits it.
- **Tools:** `implement-spec` unpatched for a spec (`tdd`, its own `code-review`); `implement` for a one shot or a batch, with `diagnosing-bugs` for a bug; the `AGENTS.md` must-read list; `flow gate`.

### 7. Review

- **Role:** reviewer (step `review`), the other model family from the builder.
- **Runs:** per landing whose diff class is not prose only: on the gated diff, then on each fix diff until clean.
- **Input:** the branch diff, the ticket or the spec, the design note or record, `CODING_STANDARDS.md`, the project's Review lenses.
- **Output:** Review findings.
- **Quality bar:** no open blocking finding (correctness, spec gap, breach of a documented standard); every contract example has a test with literal expected values; every finding confirmed at its line.
- **Tools:** the Review stage skill (`code-review` as written, a correctness pass and the project lenses, each in a fresh subagent). It never starts the app.

### 8. QA

- **Role:** QA (step `qa`).
- **Runs:** once per landing whose diff class is surface path, after Review is clean; skipped and logged otherwise.
- **Input:** the reviewed branch in its own worktree and dev deployment, the behavioural contracts, the list of changed screens, "Running the app".
- **Output:** QA findings.
- **Quality bar:** no open blocking finding; a finding counts only with a failing repro test at the lowest seam that reproduces it, and blocks Land only when this landing caused it.
- **Tools:** the QA stage skill and the project's QA tools from `docs/agents/dev-loop.md`.

### 9. Release

- **Role:** lead.
- **Runs:** per landing.
- **Input:** a passed gate on the exact commit, Review clean or skipped by diff class, QA clean or skipped by diff class.
- **Output:** `main` fast-forwarded, the health check row, the production deploy, a Release report for a spec or an FYI line for a ticket.
- **Quality bar:** `flow land` succeeded, the live check passed, the report says what the client must do to see each change and quotes the behaviour from the contract examples; a production write names the ADR or record line that governs it, and that line's steps (dry run, snapshot) ran before the write.
- **Tools:** `flow land`, the project's deploy path, production credentials.

### 10. Audit

- **Role:** audit lead (the lead session started with `audit`); auditors (steps `audit`, `audit-second`, `audit-architecture`).
- **Runs:** as its own flow when the client starts it; never inside or at the close of a delivery iteration.
- **Input:** `main` at the pinned commit, the health check rows, the project's Audit lenses, `CODING_STANDARDS.md`.
- **Output:** one Audit report beside the ledger and a request to the client; for what the client picks, one issue per batch with its findings listed, one spec issue per spec, and a bug ticket with its origin spec for a finding caused by a released spec.
- **Quality bar:** every area read in full, defects by both model families and architecture by the primary family; every notable problem carries a finding id, file, line and its consequence at today's scale or the named change it makes expensive; everything below the bar is counted by lens, not itemized; a glossary, ADR or doc line the code contradicts is a finding quoting both lines; a bound a closed spec accepted is reported only with its failure scenario at the bound; a finding a released spec already fixed is closed naming that spec; nothing is filed that the client did not pick.
- **Tools:** the scanner pass, the defect review with its six lenses, `/improve-codebase-architecture`, `flow ledger`.

### 11. Retro

- **Role:** retro lead (the lead session started with `retro`); the `retro` step.
- **Runs:** as its own flow when the client starts it; never inside or at the close of a delivery iteration.
- **Input:** the ledger since the last Retro row, the health check rows, the tracker, transcripts sampled by ledger outliers.
- **Output:** a Retro report beside the ledger; checks and standards filed as one-shot tickets on the project tracker; flow text changes pushed; a request to the client for what it decides.
- **Quality bar:** every candidate is routed (check, standard, watch item, flow text change, or dropped with a reason); a flow or skill text change is pushed only with the client's acceptance.
- **Tools:** `retro` read as a file, `writing-for-agents`, `flow ledger rollup`.

## Hand-off artifacts

Each entry says where the artifact lives, who writes it and who reads it.
Formats with a template are in [`templates/artifacts/`](templates/artifacts/).

- **Run-end report** (every spawned session): one line into the lead's herdr session, sent with `flow report <outcome> <link to the stage's artifact>`: `run-end: <step> <target> <outcome> <link> <session id> (<session name>)`. The lead appends the run's ledger row from it with `flow ledger run`. A question or a conflict exit goes the same way with `flow ask`.
- **Readiness report** ([template](templates/artifacts/readiness-report.md)): the lead's session start report, printed in its pane and appended as a ledger row; a comment on the map when the session works one. Writer: lead. Readers: client, Retro.
- **Request** ([template](templates/artifacts/request.md)): an issue on the driving brain's tracker, labelled `lead:round`, assigned to the client, linked from its container. Writer: whoever raises it (the lead, the audit lead, the retro lead). Reader: client. The answer, its decision basis and its decision rows go on the issue before it closes.
- **Triage report** ([template](templates/artifacts/triage-report.md)): comment on the pool's lead-input issue, per ticket batch, spec, decide or drop with a reason and the counts per class, sent to the client as one FYI; the ledger's triage row. Writer: lead. Reader: client.
- **Spec brief** ([template](templates/artifacts/spec-brief.md)): the first body of the spec's issue on the project tracker, opened at the end of Shape. Writer: lead. Readers: designer, architect.
- **Design note** ([template](templates/artifacts/design-note.md)): comment on the ticket, with the second opinion merged in. Writer: lead. Readers: second opinion, Build, Review.
- **UX notes** ([template](templates/artifacts/ux-notes.md)): comment on the spec issue, plus the chosen prototype branch. Writer: designer. Readers: architect, lead, Review.
- **Design record** ([template](templates/artifacts/design-record.md)): comment on the spec issue, with the second opinion merged in; ADRs are files in the project repo. Writer: architect. Readers: lead, groomer, implementers, Review, QA.
- **Second opinion note** ([template](templates/artifacts/second-opinion-note.md)): the `--note` text of `flow spawn system-design-second`, naming the Audit report path and the record or note link. Writer: lead. Reader: the second opinion.
- **Design branch**: `design/<spec>` in the project repo, holding documents only: ADRs, glossary terms and changes to `PRODUCT.md` and `DESIGN.md`. Writers: designer, architect. Reader: Build, which merges it into the integration branch at its start.
- **Spec**: the spec issue body, replacing the brief. Writer: lead through `to-spec`, its template unchanged, with links to the UX notes and design record. Readers: every later stage.
- **Ticket graph**: sub-issues of the spec with native blocking edges. Writer: groomer through `to-tickets`, its template unchanged; each ticket names the contract examples it implements. Reader: `implement-spec`.
- **Batch**: a parent issue labelled `batch` on the project tracker with its tickets as sub-issues; the target of `flow spawn`, the gate and the ledger, carrying the Review and QA comments. Writer: lead. Readers: Build, Review, QA.
- **Build run**: one comment on the target issue per Build run, with the branch (`spec/<spec>-<slug>` for a spec), its tip commit and worktree path, and the tickets merged. Writer: the build session. Reader: lead.
- **Gate result**: printed by `flow gate`, recorded as a ledger row and as the pass marker `flow land` reads. It holds the commit, the diff class, the check command result, the journey tests result, the protected-change flags (weakened tests, check-config changes, suppressions) each with file and line, and the verdict.
- **Review findings** ([template](templates/artifacts/review-findings.md)): one comment on the target issue per Review run, and one ticket per finding. Writer: reviewer. Readers: lead, implementer.
- **QA findings** ([template](templates/artifacts/qa-findings.md)): one comment on the target issue, one ticket per finding, and the repro tests on the branch `qa/<target>`, one commit each. Writer: QA. Readers: lead, implementer. A skipped QA is a ledger row with its reason and no comment.
- **Health check row**: the scanner numbers of the landed commit, appended to the ledger by `flow land`. Readers: Readiness, Audit, Retro.
- **Release report** ([template](templates/artifacts/release-report.md)): comment on the spec issue. Writer: lead. Reader: client. A ticket gets one FYI line in its place. The client's acceptance is one line on the map at close.
- **FYI**: a comment on the spec issue or the map, never assigned. Writer: lead. Reader: client.
- **Audit report** ([template](templates/artifacts/audit-report.md)): one file in the driving brain beside the ledger, merged by the audit lead from the auditors' step reports ([defect](templates/artifacts/audit-defect-report.md), [architecture](templates/artifacts/audit-architecture-report.md)), each written to a file on the run host and linked from its run-end report. Readers: client (through the request), Readiness, System design.
- **Retro report** ([template](templates/artifacts/retro-report.md)): one file in the driving brain beside the ledger. Writer: the `retro` step. Readers: retro lead, client, Readiness.

Finding tickets: blocking findings sit under the target, the rest go to the lead's triage.
Every bug ticket carries its origin spec.

## The trail

- In the driving brain: the ledger files under `ledger/<project>/` ([schema](ledger/README.md)), the Audit and Retro report files beside them, the maps with their readiness reports, and the request issues on its tracker.
- On the project tracker: tickets and batches, the spec brief and spec, design notes, UX notes, design records, Review and QA findings, Release reports and FYIs. Ledger rows link to them.
- On the run host: transcripts, kept 365 days, pointed at by session id.
