# Search Modes Convention

GBrain search mode is the default retrieval posture for query-related work.

Use the active mode instead of hand-rolling per-skill retrieval knobs.

## Modes

Upstream GBrain defines three named modes:

- `conservative` - lower token budget, smaller result set
- `balanced` - normal default for most brains
- `tokenmax` - broader retrieval, larger context, higher cost

The installed GBrain version owns the exact mode bundle values. Do not duplicate or tune those constants inside skills.

## Agent behavior

- `query`, `brain-ops`, and `signal-detector` should respect the active search mode.
- Per-call overrides are acceptable only when the user intent clearly needs them.
- When tuning retrieval posture, use GBrain's own commands instead of local heuristics.

Useful commands:

```bash
gbrain search modes
gbrain search stats
gbrain search tune
```

Use `--apply` only after approval.

## When to mention mode

Mention search mode when:

- retrieval seems too narrow or too noisy
- cache/search stats are part of a review
- a review is evaluating Retrieval Layer posture
- the user asks why a query did or did not find something

Do not make search mode part of every ordinary answer.

## Anti-patterns

- Redefining upstream mode constants per brain.
- Quietly changing `search.mode` during a user-facing task.
- Adding hidden per-skill token/result overrides that make retrieval behavior hard to audit.
- Treating search tuning as a substitute for missing pages, broken citations, or bad filing.
