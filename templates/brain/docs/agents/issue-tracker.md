# Issue tracker: GitHub ({{tracker}})

Planning issues for this brain live as GitHub issues on `{{tracker}}`. Use the `gh` CLI for all operations. The tracker is the working surface for `wayfinder` maps and for run requests to `/operate`; it holds in-flight planning state, not compiled truth. Brain pages remain canonical for decisions and project state (see "Handoff rules" below).

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

A run request is one issue labelled `run`, created from the "Run request" issue template: the project as `owner/repo`, the goal, a done check that passes or fails, the proof, what is known, constraints. Its title is `Run: <repo name> - <goal>`, the goal in lowercase. `/operate <issue>` hands it to pstack and stays the run's operator; the run comments its stops and its note on the issue, and the operator answers the stops it can and assigns the requester for a call that is theirs and once it has checked the note. Open `run` issues are the runs written or in flight, and one assigned to you waits for you. Closing the issue is the acceptance.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, titled `Map: <name>` so maps stand out in browser tabs, holding the Destination / Notes / Decisions-so-far / Not yet specified / Out of scope body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). The title starts with the type as a word, `Research: `, `Prototype: `, `Grilling: ` or `Task: `, then a lowercase summary. Once claimed, the ticket is assigned to the driving dev.
- **Run child**: a run the map produces is its `run` issue as a sub-issue of the map, one issue per run. A run whose scope is clear is created directly as a child, with the blocking edges of the tickets that wait on it. A run charted before its scope is clear starts as a placeholder ticket, `Task: run request - <goal>`, that those tickets are blocked by; the session that settles the scope converts the same issue: the run template's body, the `Run: ` title, `run` in place of `wayfinder:task`, the requester assigned, and every edge kept. A placeholder that splits into several runs converts into one, and each other run is a new child with the same blockers. The session names in a comment the hosts that hold the project.
- **Assignee by label**: on a `wayfinder:*` ticket the assignee is a session's claim; on a `run` child it means the requester's move, as in "Run requests" above.
- **Blocking**: GitHub's **native issue dependencies**, the canonical UI-visible representation. Add an edge with `gh api --method POST repos/{{tracker}}/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/{{tracker}}/issues/<n> --jq .id`, not the `#number` or `node_id`). GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only, the live gate). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open `wayfinder:*` children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far. A `run` child resolves at its acceptance: its pointer gists what shipped, and the session graduates the fog and checks the tickets the run unblocked. Every `/wayfinder` session on a map starts by recording each closed `run` child missing from Decisions-so-far, so a run accepted without a lead still reaches the map.
- **Starting a run**: the requester picks the host. `/operate <run>` there runs it on its own. `/wayfinder <map> <run>` leads it: the session starts `/operate <run>` in a herdr session on its own host or the one the requester names, answers the stops the map and the brain settle, brings the requester the rest, and records the run on the map at acceptance. It accepts the run only when the invocation delegates acceptance, and a change to layout, look and feel or functionality stays the requester's review. An agent starts an operator only on a host the requester names for that run.
- **Research-ticket findings** land as an immutable run record at {{research_records}}, linked from the resolution comment, on `main`.
- **No branch outlives its work.** Every branch other than `main` is ephemeral: a research or prototype branch is deleted when its ticket closes, and a run's branches when the run is done. What a branch held either lands on `main` or lives with its ticket.

## Handoff rules

This repo is a brain, so planning state and compiled truth have different homes. GitHub issues hold the ephemeral working state; brain pages hold what outlives the effort.

- **Research tickets read subject pages for context.** Before external sources, query the brain (`gbrain search`, `gbrain query`) for the subject pages under {{subject_dirs}}, per `skills/conventions/brain-first.md`. Prior research records supply leads (sources, questions), never inherited verdicts: the ticket re-tests their conclusions against primary sources.
- **Durable decisions propagate to brain pages.** When a ticket resolution constitutes a durable decision, write it onto the subject's brain page with an inline citation per `schema.md` (cite the resolving issue, for example `[Source: {{tracker}} issue #<n>, YYYY-MM-DD]`), through `skills/brain-ops/SKILL.md`. The map's Decisions-so-far stays an index; the brain page holds the compiled truth.
- **Map completion files to the brain.** A finished map's destination artifact (spec, decision, plan) files per root `RESOLVER.md`, typically on the owning subject page, or on a new page via `skills/brain-taxonomist/SKILL.md`.
- **Prototype tickets produce throwaway artifacts.** Run the `prototype` skill and let the effort decide the shape. A dev project gets the skill's own shapes: a single-file HTML state-machine demo, or UI variants on one route. A business or day-to-day effort gets a rough concrete artifact to react to: an outline, a draft doc, a deck skeleton. Link it from the ticket, keep it out of `main`, and land only the validated decision in the brain. A kept artifact lives where it is used (a claude.ai artifact linked from the ticket, a product's files in that product's repo), never on a branch.
- **Map Notes point at brain skills.** Every map's `## Notes` block names `skills/brain-ops/SKILL.md` and `skills/query/SKILL.md` as the skills each session consults.
{{local}}
