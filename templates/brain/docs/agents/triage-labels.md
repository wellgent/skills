# Triage labels

The label axes of `{{tracker}}`: the canonical roles the fleet taxonomy uses and the label strings this tracker carries.

Every triaged issue carries exactly one category label and one state label.

## Category

| Canonical role | Label in our tracker | Meaning |
| -------------- | -------------------- | ------- |
| `bug`          | `defect`             | Something in the brain or its tooling is wrong |
| `enhancement`  | `change`             | New capability or improvement |
| -              | `effort`             | Investigation or operational work |

`effort` has no upstream counterpart.
It is the common case here: a brain issue is usually a question to answer or an operation to run, not a code defect or a feature request.
When a skill asks for a category and neither `defect` nor `change` fits, apply `effort`.

## State

| Canonical role    | Label in our tracker | Meaning |
| ----------------- | -------------------- | ------- |
| `needs-triage`    | `needs-triage`       | Maintainer needs to evaluate this issue |
| `needs-info`      | `needs-info`         | Waiting on the reporter for more information |
| `ready-for-agent` | `ready-for-agent`    | Fully specified, ready for an AFK agent |
| `ready-for-human` | `needs-human`        | A call or task that stays with the owner, after a run or someday |
| `wontfix`         | `wontfix`            | Will not be actioned |

## Other axes

`wayfinder:*` records the *type* of a ticket on a wayfinder map (`map`, `research`, `prototype`, `grilling`, `task`).
A map and its tickets carry their `wayfinder:` label and no other: they are decisions, not implementation work, so they get no category or state label.
On a wayfinder ticket the assignee says whose move it is: a session's claim, or the owner's when the ticket waits on them.

`run` marks a run request for `/operate`, assigned to the requester while a call or a checked note waits for them.

`needs-attention` marks an item a maintenance routine could not settle, assigned to {{owner}} with options and a recommended one; `workflow:<name>` names the workflow that raised it (`health`, `review`, `relevance`, `core`, `summary`).
{{owner}} replies with an option number, and the workflow's next run applies it and closes the issue (`ops/brain-infra/skills/brain-routines/`).

`eval-candidate` marks an issue about a lookup that missed; the weekly retrieval eval verifies it as a candidate, comments the outcome and removes the label (`ops/brain-infra/skills/brain-health/eval/EVAL.md`).

Triage is the entry path for ad-hoc issues that arrive outside a map; maps and their tickets are never triaged.

## Brain adaptations

- **Redundancy check** is brain-first: `gbrain search` and `gbrain query` against subject pages, plus `log.md` on disk, before concluding an issue is already handled.
- **Verification** of a `defect` means reproducing it against the markdown source or the `gbrain` CLI, not running a test suite.
- **Rejected enhancements** are recorded on the owning brain page with a citation per `schema.md`.
- **Domain terms** come from `schema.md` and subject pages per `docs/agents/domain.md`.

{{local}}
