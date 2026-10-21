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

## Where the pack lives

The pack is `ops/schema-packs/<pack>/pack.json` in the brain repo. A change to it lands in one commit with the matching `schema.md`, `RESOLVER.md`, type notes and templates.
The host engine loads the pack through a link into the published copy, so a pushed change is live once the reconciler fast-forwards.
The daily doctor checks that link and opens a needs-attention issue for each page type the pack does not declare.

## Validation

Validate before pushing. GBrain loads packs by name from its home directory and a thin client holds none of the brain's packs, so point a scratch home at the checkout:

```bash
mkdir -p /tmp/pack-check/.gbrain/schema-packs
ln -sfn "$PWD/ops/schema-packs/<pack>" /tmp/pack-check/.gbrain/schema-packs/<pack>
GBRAIN_HOME=/tmp/pack-check gbrain schema validate <pack>
GBRAIN_HOME=/tmp/pack-check gbrain schema lint <pack>
GBRAIN_HOME=/tmp/pack-check GBRAIN_SCHEMA_PACK=<pack> gbrain lint <changed dirs>
```

Removing or renaming a type retypes its pages in the same change.

## Approval boundary

Schema changes are durable repo/brain-design decisions. Do not auto-apply them from a filing skill or advisor finding. Surface the reason, expected corpus impact, and validation result, then get owner direction.

## Related

- `skills/brain-taxonomist/SKILL.md` for filing against the active schema pack.
- `skills/repo-architecture/SKILL.md` for local repo path decisions.
- Root `schema.md` and `ops/schema-packs/` for the target brain's source-of-truth schema material.
