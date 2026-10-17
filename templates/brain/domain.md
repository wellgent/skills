# Domain docs

This repo is a brain, and the brain is the domain model. There is no `GLOSSARY.md` and no `docs/adr/`; the skills' domain-doc conventions map onto existing brain surfaces.

## Where the vocabulary lives

- **Page-shape vocabulary**: the brain's schema and directory resolvers define what page types exist and how they are written.
- **Domain terms and frameworks**: the subject pages carry the terms and reusable mental models of each effort.

Skills that say "use the project's domain glossary vocabulary" should use the terms already established on the relevant brain pages; search the brain before inventing a term.

## Where decisions live

There is no separate ADR store. A durable decision lands on its subject's brain page: stated as compiled truth, with a dated evidence entry carrying an inline source citation.

Skills that say "record an architectural decision" or "respect ADRs in the area" should read and write the owning subject page instead.
