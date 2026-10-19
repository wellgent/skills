# Schema Evolution Convention

Use this before proposing changes to an active schema pack.

The goal is a schema that is small enough for agents to reason about and expressive enough for the brain's actual corpus.

## Decision tree

If a cluster of pages shares domain meaning:

- **Fewer than 20 pages:** do not add a pack type. Use the nearest existing type and frontmatter/link fields.
- **20-100 pages:** consider an alias, a narrower prefix, or a specific subtype only if behavior differs.
- **100+ pages:** consider a first-class type with its own prefix, primitive, and rules.

## Add an alias when

- the content is still fundamentally the parent type
- enrichment, linking, and extraction rules are the same
- the alias mostly improves search or vocabulary

Example: a brain may treat `founder` as an alias of `person` when founder-specific behavior is not needed.

## Add a new type when

- the corpus is large enough to justify it
- the path prefix is stable
- the type needs different extraction, routing, enrichment, or link behavior
- the owner wants it to be first-class in the brain's mental model

## Add or adjust a prefix when

- the type already exists
- the content is correctly typed but lives under a new active home
- path inference should recognize that home

## Do not add a type just to

- silence a one-off orphan warning
- preserve an import's temporary directory
- avoid filing judgment
- make a single edge case fit
- mutate upstream/base packs directly

Fork or extend a local pack instead of editing upstream base/recommended packs.

## Validation

Before and after schema-pack changes:

```bash
gbrain schema validate <pack-name>
gbrain schema lint <pack-name>
gbrain schema active --repo <brain-repo>
```

When the installed version supports DB-aware lint/review commands, use them for live-brain checks before committing bulk changes.

## Approval boundary

Schema changes are durable repo/brain-design decisions. Do not auto-apply them from a filing skill or advisor finding. Surface the reason, expected corpus impact, and validation result, then get owner direction.

## Related

- `skills/brain-taxonomist/SKILL.md` for filing against the active schema pack.
- `skills/repo-architecture/SKILL.md` for local repo path decisions.
- Root `schema.md` and `ops/schema-packs/` for the target brain's source-of-truth schema material.
