# Salience And Recency Convention

`gbrain query` can distinguish two different retrieval boosts:

- **Salience** - what matters most in this brain.
- **Recency** - what is freshest.

They are separate axes. Use either, both, or neither.

## Canonical truth

Use no salience/recency boost when the user asks for stable truth:

- "who is..."
- "what is..."
- "explain..."
- historical/background questions
- entity lookup
- graph/backlink traversal

If the installed CLI auto-detects these values, default behavior is usually fine.

## Current state

Use salience and usually recency when the user asks for current state:

- "catch me up"
- "what's going on with..."
- "prep me for..."
- "status update"
- "what matters about..."

Use strong recency when the user says "today", "right now", "this morning", or another tight time bound.

## Freshness without importance

Use recency without salience when freshness is the main signal:

- "what's new this week"
- "recent updates"
- "latest notes"

## Explicit beats heuristic

When you know the user's intent, pass explicit query options supported by the installed GBrain version. Otherwise let GBrain's heuristic resolve the values and use explain output when debugging retrieval.

Useful check:

```bash
gbrain query "question" --explain
```

## Review relevance

This convention belongs mostly to Retrieval Layer and Knowledge Quality reviews. It should not block Agent Access unless client access hides or strips query options in a way that makes retrieval behavior impossible to inspect.

## Anti-patterns

- Boosting recency for historical/canonical questions.
- Treating high-salience material as automatically true.
- Ignoring explicit temporal language.
- Blaming search mode when the issue is missing source content or stale sync.
