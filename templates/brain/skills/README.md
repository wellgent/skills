# Brain skills

This directory holds the brain's core behavior skills and their support files.
Every file here is this brain's own concrete copy: agents load it from here, and nothing installs or links it from elsewhere at runtime.

## Relation to the shared core

The shared core is the placeholder-bearing reference copy, in wellgent/skills `templates/brain/`, of every file all brains carry.

- A file the shared core also holds keeps the core's text, with each placeholder filled by this brain's value and brain-specific lines only where the core marks a local extension.
- A change to the shared core is copied in here with this brain's values.
- A change here that departs from the core is a deviation, settled one of three ways: promote it to the core, turn it into a placeholder, or revert it.
- `setup-brain` in wellgent/skills cross-checks this brain against the core and reports every deviation.

## Core skills

- `signal-detector` - detect durable facts, decisions, risks, and follow-ups.
- `brain-ops` - operate within brain-source boundaries.
- `query` - answer questions from durable context with provenance.
- `capture` - save one-off thoughts, snippets, and inbox notes with source-durability verification.
- `brain-taxonomist` - choose new page paths from the active schema pack.
- `repo-architecture` - keep repo layout and naming consistent.
- `brain-transport` - how agents reach and write the brain; it lives with the brain-infra skills at `ops/brain-infra/skills/brain-transport/`.

## Core support files

- `conventions/` - brain and source routing, brain-first lookup with the external research standard, durable writes, model routing, quality, schema evolution, search modes, salience and recency, bulk safety, and the Minion and subagent rules.
- `_output-rules.md` - durable markdown output conventions.

Routing lives in each skill's `triggers:` frontmatter and the brain's own `skills/RESOLVER.md`.

{{local}}
