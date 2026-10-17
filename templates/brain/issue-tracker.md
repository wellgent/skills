# Issue tracker: GitHub (<owner>/<repo>)

Planning issues for this brain live as GitHub issues on `<owner>/<repo>`. Use the `gh` CLI for all operations. The tracker is the working surface for `wayfinder` maps and for run requests to `/operate`; it holds in-flight planning state, not compiled truth. Brain pages remain canonical for decisions, project state and executable operational tasks (see "Handoff rules" below).

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Triage operations

For ad-hoc issues arriving outside a wayfinder map. Label strings live in `docs/agents/triage-labels.md`.

- **Discover**: `gh issue list --state open --json number,title,labels --jq '[.[] | select((.labels | length) == 0 or ([.labels[].name] | index("needs-triage")))]'`, unlabeled first, then `needs-triage`, oldest first.
- **Categorise and set state**: `gh issue edit <n> --add-label "effort,needs-triage"`, then move the state label as the issue resolves.
- **Close**: `gh issue close <n> --comment "..."` for `wontfix`.

An issue that turns out to be work on a project becomes a run request; one that turns out to be a large or fuzzy effort goes to `/wayfinder` and becomes a map.

## Run requests

A run request is one issue labelled `run`, created from the "Run request" issue template: the project as `owner/repo`, the goal, a done check that passes or fails, the proof, what is known, constraints. `/operate <issue>` hands it to pstack and stays the run's operator; the run comments its stops and its note on the issue, and the operator answers the stops it can and assigns the requester for a call that is theirs and once it has checked the note. Open `run` issues assigned to you are what waits for you. Closing the issue is the acceptance.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Destination / Notes / Decisions-so-far / Not yet specified / Out of scope body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies**, the canonical UI-visible representation. Add an edge with `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, not the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only, the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
- **A route that reaches work on a project** ends in run requests, one per run, linked from the map.
- **Research-ticket findings** land as an immutable run record under the brain's research directory, linked from the resolution comment.

## Handoff rules

This repo is a brain, so planning state and compiled truth have different homes. GitHub issues hold the ephemeral working state; brain pages hold what outlives the effort.

- **Research tickets are brain-first.** Before external sources, query the brain's pages and search.
- **Durable decisions propagate to brain pages.** When a ticket resolution constitutes a durable decision, write it onto the subject's brain page with an inline citation naming the resolving issue. The map's Decisions-so-far stays an index; the brain page holds the compiled truth.
- **Map completion files to the brain.** A finished map's destination artifact (spec, decision, plan) files on the owning brain page.
- **Prototype tickets produce throwaway artifacts.** Run the `prototype` skill and let the effort decide the shape. Link it from the ticket, keep it out of `main`, and land only the validated decision in the brain.
