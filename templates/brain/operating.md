## Planning workflow

Big or fuzzy efforts are charted with `wayfinder` as a map of decision tickets on this tracker and worked one ticket per session; `grilling`, `domain-modeling`, `research` and `prototype` resolve the tickets, `wizard` scripts the steps only a person can do, `ask-matt` routes between them, and `writing-for-agents` is the reference for authoring skills and this file.

- The tracker is GitHub Issues on `<owner>/<repo>`: operations, the label axes and the handoff rules are in `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`.
- Domain-doc conventions map to brain surfaces per `docs/agents/domain.md`: vocabulary from the brain's schema and subject pages; decisions on subject pages, not ADRs.
- The eight skills and `operate` are pinned by commit in `skills-lock.json` and converged by `setup-brain` in wellgent/skills; changes go through explicit `npx skills add|remove`, never `skills update`.

## Operating projects

Product work on a project runs through pstack, started from this brain with `/operate <issue>`.

- A **run request** is one issue on this tracker labelled `run`, in the shape of the "Run request" issue template: the repo as `<owner>/<repo>`, the goal, a done check that passes or fails, the proof, what is known, constraints. It names no host; the run starts on whichever host `/operate` runs on.
- `/operate <issue>` starts the run as its own herdr session in the project checkout and ends its turn. The run merges what its verifier passes, posts its note on the request and assigns the requester when it is done or when it needs an answer. Open issues labelled `run` and assigned to you are the notes and questions waiting for you.
- A wayfinder map whose route reaches work on a project ends in run requests, one per run, linked from the map; the map stays the record of what to do, the request the record of one run.
- `/operate cost <session id>` prices a finished run from its transcript on this host.
