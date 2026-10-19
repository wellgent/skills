# Domain docs

This repo is a brain, and the brain is the domain model. There is no `GLOSSARY.md` and no `docs/adr/`; the skills' domain-doc conventions map onto existing brain surfaces.

## Where the vocabulary lives

- **Page-shape vocabulary**: `schema.md` and the directory `README.md` resolvers define what page types exist and how they are written.
- **Domain terms and frameworks**: subject pages under {{subject_dirs}} carry the terms and reusable mental models of each effort.

Skills that say "use the project's domain glossary vocabulary" should use the terms already established on the relevant brain pages; search the brain before inventing a term.

## Where decisions live

There is no separate ADR store. A durable decision lands on its subject's brain page: stated as compiled truth above `<!-- timeline -->`, with a dated evidence entry below it, carrying an inline source citation per `schema.md`. Write decisions through `skills/brain-ops/SKILL.md`.

Skills that say "record an architectural decision" or "respect ADRs in the area" should read and write the owning subject page instead.

{{local}}
