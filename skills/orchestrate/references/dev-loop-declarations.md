# Dev-loop declarations reference

What the `orchestrate` driver skill needs scaffolded in a target project.
The protocol itself is never scaffolded: it ships with this skill at [dev-loop-protocol.md](dev-loop-protocol.md) and is read in place, so skill updates carry protocol updates with no per-project reconcile.
The project carries only what is project-specific: the contract below, the tracker mechanics, the labels, and the prerequisites.
Resolve every `<placeholder>` from the target repo while scaffolding; a placeholder you cannot resolve is a gap to flag, not something to leave in the file.

## 1. The contract: `docs/agents/dev-loop.md`

Create from this template if missing.
If the target already has one, leave it - it is the repo's decided contract, and the skill defers to it.
On conflict with the protocol, the contract wins: a deviation is a decision, stated under Deviations, never silent drift.

```markdown
# Dev loop: project declarations

The dev-loop protocol lives with the installed driver skill: `.agents/skills/orchestrate/references/dev-loop-protocol.md`.
This file declares what is project-specific; on conflict with the protocol, this file wins.
Tracker mechanics live in [issue-tracker.md](issue-tracker.md); label strings in [triage-labels.md](triage-labels.md).

## Ports

- Human (interactive): <port> - agents never touch it.
- Gate (verification): <port>.
- Takes (implementers): <port>.
<any further port rules, e.g. a neighboring production port on the same machine that agents must never touch>

## Runtime

- Check command: <command> - the single quality gate (typecheck + lint + tests); the proof command in take prompts and the gate's baseline fact re-run.
- Dev-server script: <path> - start/stop/status on an explicit port; servers are ephemeral and session-owned.
- Worktree scaffold: <what a fresh take worktree needs before it can run - untracked env files to copy from the main checkout, the dependency install command>.
- Browser-tooling health check: <command>.
- Verify skill: `.agents/skills/verify/` - repo-specific runtime verification; the gate calls it for any ticket with runtime surface.

## Gate proofs

The check command is the baseline fact re-run; these repo-specific proofs cover what it structurally cannot see.
Both the gate and take prompts consume this section.

Deploy-shaped proofs, keyed off what the diff touches - the gate runs what production runs:

- <diff shape → proof command, one line per deploy-only failure class this stack has; e.g. schema changes → a real deploy push against a data-bearing deployment, destructive data changes → the migration pattern plus a production data-shape preflight, UI-heavy diffs → the production build command>

Advisory review input per surface (never pass/fail):

- <surface → skill or analyzer; e.g. React surfaces → a changed-scope analyzer run + the repo's React-guidelines skill, UI diffs → the design/accessibility review skill, user-facing copy → the writing review skill>

## Deviations

<deliberate protocol overrides, each stated with its reason - or "None.">
```

## 2. Tracker mechanics: merge into `docs/agents/issue-tracker.md`

`/setup-matt-pocock-skills` writes `docs/agents/issue-tracker.md`; this section extends it.
If that file does not exist yet, defer this merge and flag it.
Merge the following section (GitHub flavor - translate the commands for other trackers):

```markdown
## Dev loop operations

Used by the `orchestrate` driver skill.
Semantics live in the installed skill's `references/dev-loop-protocol.md`; declarations in [dev-loop.md](dev-loop.md); this section is the `gh` mechanics.

- **Spec issue**: an issue labelled `spec`. Sub-issue attach: `gh api` on the sub-issues endpoint. Blocking edge: `gh api --method POST repos/<owner>/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<blocker-db-id>` (database id via `gh api repos/<owner>/<repo>/issues/<n> --jq .id`).
- **Claim**: `gh issue edit <n> --add-assignee @me` plus the label flip (`--remove-label ready-for-agent --add-label in-progress`). Unclaim reverses both.
- **Ungroomed specs**: `gh issue list --label spec --label ready-for-agent --state open --json number,title` then keep those with no sub-issues (`gh api repos/<owner>/<repo>/issues/<n>/sub_issues` empty) and no open blockers (`issue_dependencies_summary.blocked_by == 0`).
- **Actionable tickets**: `gh issue list --label ready-for-agent --state open` (excluding `spec`-labelled issues), then drop any with an assignee or `issue_dependencies_summary.blocked_by > 0`; oldest first.
- **Recovery sweep**: `gh issue list --state open --assignee "*" --json number,title,labels,assignees` at session start; apply the protocol's crash-safety table.
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

## 4. Prerequisites the loop assumes

Verify each in the target and flag gaps - the loop runs degraded without them:

- **A check command** - the repo's single quality-gate command (typecheck + lint + tests), named in its instructions file and declared in the contract.
- **A `/verify` skill** - repo-specific runtime verification (how to launch, sign in, and drive the app); the gate calls it for any ticket with runtime surface. Scaffold it from [verify-reference.md](verify-reference.md).
- **An ephemeral dev-server script** - start/stop/status on an explicit port, so takes and gates own their servers and the human's interactive port stays untouched; declared in the contract and scaffolded by the same verify reference.
- **GitHub sub-issues and issue dependencies** enabled on the repo - the hierarchy and blocking edges are native, not body conventions.
- **The `codex` CLI installed and authenticated** on the machine only when takes will be routed through the codex runner by explicit invocation - and `jq` for reading its event streams.
- **Provider credentials on the machine, verified at scaffold time** - whatever auth the stack's tickets will need: `npx convex whoami`, `vercel whoami`, `gh auth status` (with the scopes the tracker mechanics use), DNS/registrar access when the spec includes domains. A gap found here is a line in the setup report; a gap found mid-board stalls every remaining ticket behind a `needs-human`.
- **A machine-unique port map** - the contract's human/gate/takes (and production) ports must not collide with any other project or service on the same machine. Where a machine-level port registry exists, claim a free block there before writing the contract.
