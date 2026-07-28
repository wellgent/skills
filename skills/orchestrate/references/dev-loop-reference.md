# Dev-loop reference

What the `orchestrate` driver skill needs scaffolded in a target project.
Three artifacts - the state contract, the tracker mechanics, the labels - plus the prerequisites the contract assumes.
Resolve every `<placeholder>` from the target repo while scaffolding; a placeholder you cannot resolve is a gap to flag, not something to leave in the file.

This reference ships with the skill: the installed copy is the canonical contract shape at the pinned version.
After a skill update, diff the project's contract against it and reconcile deliberately - the project's `docs/agents/dev-loop.md` stays authoritative; deviations are decisions, not drift, once stated there.

## 1. The state contract: `docs/agents/dev-loop.md`

Create from this template if missing.
If the target already has one, leave it - it is the repo's decided contract, and the skill defers to it.

```markdown
# Dev loop: the state contract

This is the contract between the issue tracker and the `orchestrate` driver skill.
The tracker is the loop's only memory: any session must be able to decide what to do - and recover from a died session - from tracker state alone.
Mechanics (the exact `gh` commands) live in [issue-tracker.md](issue-tracker.md); label strings in [triage-labels.md](triage-labels.md).

## Operating model

- Work runs in **orchestrator sessions**: human-launched, one spec at a time.
  The session grooms the spec if ungroomed, delivers its board, and closes the spec - the spec boundary is the handoff seam: the session ends there, or rolls into the next spec when real context headroom remains.
- Roles are fixed.
  The **driver** grooms, gates, lands, pushes, and owns every tracker write.
  The **implementer** is always a spawned fresh session - never the driver's own context.
- There is no scheduled loop.
  The contract is schedulable by construction (nothing below assumes a human), but scheduling waits until the workflow has proven itself in real use.
- Sessions are single-flight: at most one orchestrator session runs at a time.
  The crash-recovery rules below depend on this.

## Invocation

`/orchestrate [spec]` launches a session.
The driver is harness-generic; takes run on the executor named in The implementer contract below - native subagents by default, or an external runner such as `codex exec` per the skill's `runners/` reference.
The no-arg form is canonical: run the session-start procedure and take what it selects - the exact form a future scheduled trigger would invoke.
The argument is a human override that picks among legal choices only: it refuses a blocked or claimed spec, and an open `fix-main` ticket still outranks it.
One spec at a time, never a guaranteed deliverable - a session may fix main, clear a standalone ticket, only groom, or exit mid-board at a ticket boundary.
A closed spec is a continuation seam: when real context headroom remains, the session may re-run selection and roll into the next spec - one spec remains the normal session; continuation is the exception headroom earns, and never starts a spec the session might not finish gating.
Every continuation is declared in its reports (see Session end).

## Hierarchy: specs and tickets

Two tiers, nothing else.

- A **spec issue** (label `spec`) is the parent: the durable what-and-why, published by `/to-spec`.
  Ordering between bodies of work is native blocking edges **between spec issues**.
  A body of work too big for one spec becomes several specs with edges.
- A **ticket** is a native **sub-issue** of its spec, published by grooming (`/to-tickets`), with blocking edges among siblings.
  Parentless tickets are legal for small standalone work.
- No milestones.
  The closed spec issue is the durable done-marker; closing it is what unblocks the next spec.

## Labels and claims

Two independent dimensions:

- The **label** carries lifecycle state: `ready-for-agent`, `in-progress`, `needs-human` (plus the triage states, see [triage-labels.md](triage-labels.md)).
- The **assignee** carries the claim: assigned means a live session owns it right now.
  Every claim is "assign yourself"; every clean handback is "unassign".

Ticket lifecycle:

    ready-for-agent → in-progress → closed        (delivery: take + gate + land, atomic in-session)
    in-progress → ready-for-agent                 (died-session revert)
    any → needs-human                             (escalation: budget spent, or a decision only the human can make)
    needs-human → ready-for-agent | closed        (the human unblocks and hands back, or kills it)

`needs-human` means exactly one thing: the loop is blocked on human input.
The human never implements - they answer, decide, or re-scope, then flip back to `ready-for-agent` or close.

## Spec state is derived, never stored

- Open, unblocked, no sub-issues → **ungroomed**: groomable.
- `in-progress` + assigned → **being groomed** (or a died groom - see recovery).
- Sub-issues exist, spec not `in-progress` → **board live**: drive the tickets.
- All sub-issues closed → **done**: close the spec.

## Grooming protocol

See the driver skills for the full protocol; the state moves are: claim (`in-progress` + assign) → breakdown + quiz → publish sub-issues → unclaim (the atomic "board is live" flip).
Never groom ahead: a spec is only groomable when its blocking specs are closed, so tickets are always written against the codebase they land on.

## Crash safety

Under single-flight, **any assigned item at session start is a died session**.
Recovery is mechanical, per state:

- Ticket `in-progress` + assigned → revert to `ready-for-agent`, unassign.
  Take commits were local to the dead session; nothing to salvage.
- Spec `in-progress` + assigned → **wipe-and-regroom**: close the orphaned sub-issues, revert the spec to `ready-for-agent`, unassign.
  Grooming is cheap; a partial-publish reconciliation protocol is not.

## Session-start procedure

Every orchestrator session runs this before any work:

1. **Workspace preflight** - a dirty tree hard-stops the session with a report of what it found; only work the session can identify may be stashed, committed, or discarded.
   Then `git fetch` and rebase onto `origin/<default-branch>`, health-check the browser-verification tooling (<browser-tooling health command>), and reap stale loop-owned dev servers (`<dev-server script> stop` on the gate and takes ports: <gate port> gate, <takes port> takes - never <interactive port>, the human's interactive port).
   No dev server is started here: servers stay ephemeral, spun up when a gate needs one.
2. **Recovery sweep** - find assigned items, apply the recovery table above.
3. **Tracker preflight** - read CI and deploy status on the default branch's head.
   Either red → find-or-create the `fix-main` ticket (label `fix-main` + `ready-for-agent`, title names the failing check and sha, body carries the evidence); at most one open at a time.
   Green with a stale open `fix-main` → close it with a note.
4. **Select**, in priority order:
   1. the open `fix-main` ticket - fixing main outranks all other work;
   2. the oldest open, unblocked, unassigned `ready-for-agent` ticket;
   3. the first open, unblocked, ungroomed `ready-for-agent` spec;
   4. nothing → say so and stop.

`needs-triage` and `needs-info` items are invisible to the loop; triage is a separate surface.

## Session end

Every session, however it exits:

- **Teardown** - stop loop-owned dev servers and browser sessions.
- **Report** - one spec-level comment per spec driven: the closing comment when the spec closes, a status comment otherwise.
  It summarizes tickets shipped, bounces, escalations, and commits, names the driver session id literally (never "this session") plus, when the session drove more than one spec, this spec's ordinal within it - the anchor for post-factum cost attribution - and ends with the loop's blockers: open `needs-human` items and whether any ready spec remains.
- **Observations** - anything actionable (a tooling defect, a gate blind spot, a skill gap) becomes an issue labelled `needs-triage`; narrative context goes in the report's Observations section.

Mid-board exits happen at ticket boundaries only.
At each boundary the driver checks its own context pressure and stops rather than starting a take it might not gate - the take's commits are local and die with the session.
Anything the next session needs goes as a comment on the relevant ticket; the tracker is the only handoff surface.
Resuming is just invoking the driver skill again.

## Between sessions

The human side of the seam - pull-based, no fixed cadence:

1. Read the last session's report comment - the single catch-up surface.
2. Clear `needs-human` items: answer, re-scope, or kill; each flips back to `ready-for-agent` or closes.
3. Triage `needs-triage`, including observation issues filed by sessions.
4. Refill the spec pipeline via `/to-spec` when few unblocked, ungroomed specs remain.
   Writing specs ahead is fine; only grooming ahead is forbidden.

## The implementer contract

Grooming breakdowns come from a fresh subagent of the driving harness.
Takes: <the take executor - `native subagents` (the default) or `codex exec` per the orchestrate skill's runners/codex.md>.
Whichever executor spawns, the contract holds:

- Fresh session at token-zero; the prompt carries the complete spec and grounding pointers.
- The session is continuable - the groom quiz loop and delivery bounces resume the same session.
- A terse report comes back; the driver never reads raw logs wholesale.
- Commits stay local and unpushed; every tracker write and every push belongs to the driver.

## Two reviews, by design

- The implementer **self-reviews** inside the take (`/implement` ends with `/code-review`).
  Cheap pre-flight; shares the author's blind spots by construction.
  The review runs inline in the take's own context - both axes sequentially, overriding the code-review skill's parallel sub-agents; a take never spawns sub-agents and never blocks waiting on agent messages or notifications.
- The driver **gates** in the delivery loop: the four axes (spec fidelity, repo standards, design direction, elegance) judged on the diff with fresh eyes, plus the fact re-run - the driver re-runs checks and `/verify` itself, never trusting the report.
  The gate verdict is non-delegable.
  Push only on green: a push to the default branch deploys in most setups.

## Gate proofs

The check command is the baseline fact re-run; these repo-specific proofs cover what it structurally cannot see.
Both the gate and take prompts consume this section.

Deploy-shaped proofs, keyed off what the diff touches - the gate runs what production runs:

- <diff shape → proof command, one line per deploy-only failure class this stack has; e.g. schema changes → a real deploy push against a data-bearing deployment, destructive data changes → the migration pattern plus a production data-shape preflight, UI-heavy diffs → the production build command>

Advisory review input per surface (never pass/fail):

- <surface → skill or analyzer; e.g. React surfaces → a changed-scope analyzer run + the repo's React-guidelines skill, UI diffs → the design/accessibility review skill, user-facing copy → the writing review skill>

## Skill map

- `/to-spec` - conversation → spec issue (upstream, unchanged).
- `/orchestrate` - the driver loop: session-start procedure, then one spec end to end - grooms via a fresh subagent following `/to-tickets`, delivers via fresh takes on the contract's executor following `/implement`, gates itself.
- Source of truth for the driver skill is wellgent/skills, pinned in `skills-lock.json`.
```

## 2. Tracker mechanics: merge into `docs/agents/issue-tracker.md`

`/setup-matt-pocock-skills` writes `docs/agents/issue-tracker.md`; this section extends it.
If that file does not exist yet, defer this merge to after step 6 and flag it in the report.
Merge the following section (GitHub flavor - translate the commands for other trackers):

```markdown
## Dev loop operations

Used by the `orchestrate` driver skill.
Semantics live in [dev-loop.md](dev-loop.md); this section is the `gh` mechanics.

- **Spec issue**: an issue labelled `spec`. Sub-issue attach: `gh api` on the sub-issues endpoint. Blocking edge: `gh api --method POST repos/<owner>/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<blocker-db-id>` (database id via `gh api repos/<owner>/<repo>/issues/<n> --jq .id`).
- **Claim**: `gh issue edit <n> --add-assignee @me` plus the label flip (`--remove-label ready-for-agent --add-label in-progress`). Unclaim reverses both.
- **Ungroomed specs**: `gh issue list --label spec --label ready-for-agent --state open --json number,title` then keep those with no sub-issues (`gh api repos/<owner>/<repo>/issues/<n>/sub_issues` empty) and no open blockers (`issue_dependencies_summary.blocked_by == 0`).
- **Actionable tickets**: `gh issue list --label ready-for-agent --state open` (excluding `spec`-labelled issues), then drop any with an assignee or `issue_dependencies_summary.blocked_by > 0`; oldest first.
- **Recovery sweep**: `gh issue list --state open --assignee "*" --json number,title,labels,assignees` at session start; apply the dev-loop recovery table.
- **Preflight**: `gh api repos/<owner>/<repo>/commits/<head-sha>/status` for combined CI + deploy state; red → find-or-create the single open `fix-main` ticket.
- **Escalation**: flip to `needs-human` (`--remove-label in-progress --add-label needs-human`), unassign, leave the record in comments.
```

## 3. Labels

The loop consumes the triage labels from `/setup-matt-pocock-skills` (`ready-for-agent`, `needs-triage`, `needs-info`) plus three lifecycle labels.
Create any that are missing:

```bash
gh label create spec --description "Spec issue - parent of its tickets (sub-issues)" --color 1D76DB
gh label create in-progress --description "An agent session is actively working this issue" --color FBCA04
gh label create fix-main --description "Main is red (CI or deploy) - outranks all other work" --color B60205
gh label create needs-human --description "Blocked on human input - human unblocks, agents implement" --color D93F0B
```

Then record them in `docs/agents/triage-labels.md` (same deferral rule as the tracker merge if the file is missing): map the `ready-for-human` role to `needs-human`, and add a "Dev loop labels" section listing `spec`, `in-progress`, and `fix-main` with pointers to `dev-loop.md`.

## 4. Prerequisites the contract assumes

Verify each in the target and flag gaps in the report - the loop runs degraded without them:

- **A check command** - the repo's single quality-gate command (typecheck + lint + tests), named in its instructions file; it is the proof command in take prompts and the gate's fact re-run.
- **A `/verify` skill** - repo-specific runtime verification (how to launch, sign in, and drive the app); the gate calls it for any ticket with runtime surface.
- **An ephemeral dev-server script** - start/stop/status on an explicit port, so takes and gates own their servers and the human's interactive port stays untouched; named in the contract's session-start section and scaffolded by the same verify reference.
- **GitHub sub-issues and issue dependencies** enabled on the repo - the hierarchy and blocking edges are native, not body conventions.
- **The `codex` CLI installed and authenticated** on the machine when the contract names the `codex exec` executor - and `jq` for reading its event streams.
- **Provider credentials on the machine, verified at scaffold time** - whatever auth the stack's tickets will need: `npx convex whoami`, `vercel whoami`, `gh auth status` (with the scopes the tracker mechanics use), DNS/registrar access when the spec includes domains. A gap found here is a line in the setup report; a gap found mid-board stalls every remaining ticket behind a `needs-human` (it has).
- **A machine-unique port map** - the contract's human/gate/takes (and production) ports must not collide with any other project or service on the same machine. Where a machine-level port registry exists, claim a free block there before writing the contract.
