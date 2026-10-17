# Triage labels

The label axes of `<owner>/<repo>`: the canonical roles the fleet taxonomy uses and the label strings this tracker carries.

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
| `ready-for-human` | `ready-for-human`    | Requires human judgment or action |
| `wontfix`         | `wontfix`            | Will not be actioned |

## Other axes

`wayfinder:*` records the *type* of a ticket on a wayfinder map (`map`, `research`, `prototype`, `grilling`, `task`).
Triage labels record *whether the issue is real and who acts next*.
Both apply to the same issue without conflict: a wayfinder child ticket can carry `wayfinder:task`, `effort` and `ready-for-agent` at once.

`run` marks a run request for `/operate`, assigned to the requester while a call or a checked note waits for them.

Triage is the entry path for ad-hoc issues that arrive outside a map.
Wayfinder children are already scoped by the map, so they need triage only when their state is in question.

## Brain adaptations

- **Redundancy check** is brain-first: search the brain's pages before concluding an issue is already handled.
- **Verification** of a `defect` means reproducing it against the brain's source or tooling, not running a test suite.
- **Rejected enhancements** are recorded on the owning brain page with a citation.
- **Domain terms** come from the brain's schema and subject pages per `docs/agents/domain.md`.
