# The flow

The development flow on one page: eleven stages, each with one owning role, one input, one output and a quality bar that can be checked, and the artifacts handed between them.
Terms in bold on first use are defined in [`GLOSSARY.md`](GLOSSARY.md).
Each stage skill opens with its header from this page; this page is the source of truth for the headers.

## How it runs

- The **lead** runs an **iteration** for a **client** on one project, from a **driving brain**.
- A **stage** has one owning role, one input artifact, one output artifact and a quality bar. It runs in fresh sessions, so it can be replayed and improved on its own.
- A **step** is one session the lead starts with `flow spawn <step> <spec>`. Its model and effort come from the **flow config**; an empty entry inherits the lead's.
- Every spawned session ends with a **run-end report** to the lead. A session with a question or a **conflict exit** asks the lead the same way and waits for the reply.
- Only the lead session holds production credentials. Every production read or write goes through the lead.
- A skill runs only when a step's stage skill or the project's `AGENTS.md` names it by path or step.
- Stage skills name no stack and no project. Stack rules, lenses and tools are declared in each project's `AGENTS.md`, `docs/agents/dev-loop.md` and `CODING_STANDARDS.md`.

Iteration stages: Readiness, Shape, Audit, Retro.
Per-spec stages: UX design, System design, Plan, Build, Review, QA, Release.

```
Readiness -> Shape -> [ UX design -> System design -> Plan -> Build -> Review -> QA -> Release ] per spec -> Audit -> Retro
                                                               ^ gate    |         |
                                                               +---------+---------+  findings re-enter Build
```

An iteration stays open after its destination is reached and absorbs bugs and small fixes until the client closes it.
Audit and Retro run at the client's close.
Work between iterations runs without the flow.

A single bug ticket outside a spec runs in one `build` session, then the gate, Review and Release, with QA under its skip rule and no System design or Grooming.

## Steps

The flow config holds one entry per spawned step.
Stages the lead runs itself have no entry.

- `ux-design`: UX design.
- `system-design`, `system-design-second`: System design and its second opinion.
- `grooming`: the ticket graph, inside Plan.
- `build`: Build. Everything inside the session runs on its model and effort.
- `review`: Review.
- `qa`: QA.
- `audit`, `audit-second`: the Audit defect review, one per model family.
- `audit-architecture`, `audit-architecture-second`: the Audit architecture review, one per model family.

## Stage headers

### 1. Readiness

- **Role:** lead.
- **Runs:** at iteration start.
- **Input:** the previous Retro report (watch items, pending trials), the closing Audit reports, the **source log**.
- **Output:** readiness report.
- **Quality bar:** the report is green: every source reviewed, regular updates applied, major changes decided by the client, the four targets (flow repo, brain, project, host) current, an Audit no older than `main`.
- **Tools:** the setup skills, the source log, `writing-for-agents` for skill edits; the Audit stage when `main` changed since the closing audit or the project has none.

### 2. Shape

- **Role:** lead as product owner; the client decides at checkpoints.
- **Runs:** through the iteration, on the iteration map.
- **Input:** the client's destination, the readiness report, triaged Audit and exploration findings.
- **Output:** one **spec brief** per slice with no open product decision left.
- **Quality bar:** every user-visible behaviour in the brief has a client decision with its **decision basis**; decisions rest on prototypes or live data, never text alone.
- **Tools:** `wayfinder`, the `grilling` round format, `domain-modeling`, `research` in subagents.

### 3. UX design

- **Role:** designer (step `ux-design`).
- **Runs:** per spec with a user-visible surface; skipped otherwise.
- **Input:** the spec brief, `PRODUCT.md`, `DESIGN.md`, "Running the app" in `docs/agents/dev-loop.md`.
- **Output:** the chosen prototype (branch) and UX notes.
- **Quality bar:** no open P0 or P1 finding verified on the page, the design-system lint green, every option inside the design system; scores recorded, not gated.
- **Tools:** impeccable `doctor`, `shape`, per-option `critique`, `audit`, rendered `detect`; `init` and `document` when the preconditions are missing; the project's prototype host.

### 4. System design

- **Role:** architect (step `system-design`; `system-design-second` on hard-to-reverse calls).
- **Runs:** per spec, after UX design.
- **Input:** the spec brief, UX notes, existing ADRs, the merged architecture audit report for the modules touched.
- **Output:** design record, plus an ADR per hard-to-reverse call.
- **Quality bar:** the lead approves; hard-to-reverse calls carry a second opinion from the other model family; behavioural contracts exist wherever the spec touches authorization, money or data integrity.
- **Tools:** `codebase-design` (design-it-twice on module-shaping calls), `domain-modeling`.

### 5. Plan

- **Role:** lead writes the spec; groomer cuts tickets (step `grooming`).
- **Runs:** per spec.
- **Input:** the spec brief, UX notes, design record.
- **Output:** the spec and its ticket graph.
- **Quality bar:** the lead approves the ticket graph; every contract example and every UX state is covered by a ticket; blocking edges serialize work that cannot run in parallel.
- **Tools:** `to-spec`, `to-tickets`.

### 6. Build

- **Role:** implementers and merger inside one session (step `build`); the lead runs the **gate**.
- **Runs:** per spec, and again for each batch of Review or QA findings.
- **Input:** the spec and ticket graph, or one bug ticket.
- **Output:** the integration branch with every ticket merged, and a gate result.
- **Quality bar:** `flow gate` passes on the branch tip: the check command green and the protected-change script clean on the whole spec diff.
- **Tools:** `implement-spec` unpatched (`tdd`, its own `code-review`); for a single bug `diagnosing-bugs` and `implement`; the `AGENTS.md` must-read list; `flow gate`.

### 7. Review

- **Role:** reviewer (step `review`), the other model family from the builder.
- **Runs:** per spec on the gated diff, then on each fix diff until clean.
- **Input:** the integration-branch diff, the spec, the design record, `CODING_STANDARDS.md`, the project's Review lenses.
- **Output:** Review findings.
- **Quality bar:** no open blocking finding (correctness, spec gap, breach of a documented standard); every contract example has a test with literal expected values.
- **Tools:** the Review stage skill (`code-review` as written plus a correctness pass). It never starts the app.

### 8. QA

- **Role:** QA (step `qa`).
- **Runs:** once per spec, after Review is clean; skipped and logged when the spec has no user-facing change.
- **Input:** the reviewed branch in its own worktree and dev deployment, the behavioural contracts, the list of changed screens, "Running the app".
- **Output:** QA findings.
- **Quality bar:** no open blocking finding; a finding counts only with a failing repro test at the lowest seam that reproduces it.
- **Tools:** the QA stage skill and the project's QA tools from `docs/agents/dev-loop.md`.

### 9. Release

- **Role:** lead.
- **Runs:** per spec; acceptance at the client's close.
- **Input:** a passed gate on the exact commit, Review and QA clean.
- **Output:** `main` fast-forwarded, the production deploy, a Release report.
- **Quality bar:** `flow land` succeeded, the live check passed, and the report says what the client must do to see each change.
- **Tools:** `flow land`, the project's deploy path, production credentials.

### 10. Audit

- **Role:** auditor (steps `audit`, `audit-second`, `audit-architecture`, `audit-architecture-second`).
- **Runs:** at the client's close, reused as the next iteration's start; in full on a project's first run.
- **Input:** `main`, the scanner pass numbers, the project's Audit lenses, `CODING_STANDARDS.md`.
- **Output:** a scanner row in the ledger, one merged defect report, one merged architecture report.
- **Quality bar:** every finding has file, line and failure scenario; the lead has triaged every finding (bug ticket, Shape candidate, cleanup spec, or closed with a reason).
- **Tools:** the scanner pass, the defect review prompt with its six lenses, `/improve-codebase-architecture`.

### 11. Retro

- **Role:** lead, in a fresh session.
- **Runs:** at the client's close and on the two scripted triggers: an **escaped defect** touching authorization, money or data integrity in the open iteration, and a spec whose stage measures fall outside the spread of the previous ten.
- **Input:** the ledger, the tracker, transcripts sampled by ledger outliers.
- **Output:** Retro report; checks and standards applied; skill and flow text changes put to the client.
- **Quality bar:** every candidate is routed (check, standard, re-test trigger, trial ticket, or dropped with a reason); skill and flow text changes only with the client's approval.
- **Tools:** `retro` read as a file, `writing-for-agents`, `flow ledger rollup`.

## Hand-off artifacts

Each entry says where the artifact lives, who writes it and who reads it.
Formats with a template are in [`templates/artifacts/`](templates/artifacts/).

- **Run-end report** (every spawned session): one line into the lead's herdr session, sent with `flow report <outcome> <link to the stage's artifact>`: `run-end: <step> <spec> <outcome> <link> <session id> (<session name>)`. The lead appends the run's ledger row from it with `flow ledger run`. A question or a conflict exit goes the same way with `flow ask`.
- **Readiness report** ([template](templates/artifacts/readiness-report.md)): comment on the iteration map. Writer: lead. Readers: client, Retro.
- **Spec brief** ([template](templates/artifacts/spec-brief.md)): the first body of the spec's issue on the project tracker, opened at the end of Shape. Writer: lead. Readers: designer, architect.
- **UX notes** ([template](templates/artifacts/ux-notes.md)): comment on the spec issue, plus the chosen prototype branch. Writer: designer. Readers: architect, lead, Review.
- **Design record** ([template](templates/artifacts/design-record.md)): comment on the spec issue; ADRs are files in the project repo. Writer: architect. Readers: lead, groomer, implementers, Review, QA.
- **Design branch**: `design/<spec>` in the project repo, holding documents only: ADRs, glossary terms and changes to `PRODUCT.md` and `DESIGN.md`. Writers: designer, architect. Reader: Build, which merges it into the integration branch at its start.
- **Spec**: the spec issue body, replacing the brief. Writer: lead through `to-spec`, its template unchanged, with links to the UX notes and design record. Readers: every later stage.
- **Ticket graph**: sub-issues of the spec with native blocking edges. Writer: groomer through `to-tickets`, its template unchanged; each ticket names the contract examples it implements. Reader: `implement-spec`.
- **Build run**: one comment on the spec issue per Build run, with the integration branch `spec/<spec>-<slug>`, its tip commit and worktree path, and the tickets merged. Writer: the build session. Reader: lead.
- **Gate result**: printed by `flow gate`, recorded as a ledger row and as the pass marker `flow land` reads. It holds the commit, the check command result, the journey tests result, the protected-change flags (weakened tests, check-config changes, suppressions) each with file and line, and the verdict.
- **Review findings** ([template](templates/artifacts/review-findings.md)): one comment on the spec issue per Review run, and one ticket per finding. Writer: reviewer. Readers: lead, implementer.
- **QA findings** ([template](templates/artifacts/qa-findings.md)): one comment on the spec issue, and one ticket per finding. Writer: QA. Readers: lead, implementer. A skipped QA is a ledger row with its reason and no comment.
- **Release report** ([template](templates/artifacts/release-report.md)): comment on the spec issue. Writer: lead. Reader: client. The client's acceptance is one line on the iteration map at close.
- **Audit reports** ([defect](templates/artifacts/audit-defect-report.md), [architecture](templates/artifacts/audit-architecture-report.md)): a scanner row in the ledger and two merged report files in the driving brain beside the iteration's ledger file. Writers: auditors, merged by the lead. Readers: lead, architect (by path from the lead), next Readiness. Findings the lead keeps become tickets on the project tracker.
- **Retro report** ([template](templates/artifacts/retro-report.md)): the iteration map's closing comment. Writer: lead. Readers: client, next Readiness.

Finding tickets: blocking findings sit under the spec, the rest go to the lead's triage.
Every bug ticket carries its **origin spec**.

## The trail per iteration

- In the driving brain: the ledger file under `ledger/<project>/` ([schema](ledger/README.md)), the two Audit report files beside it, and the iteration map with the readiness report and the Retro report as comments.
- On the project tracker: the spec brief and spec, UX notes, design record, Review and QA findings, Release report. Ledger rows link to them.
- On the run host: transcripts, kept 365 days, pointed at by session id.
