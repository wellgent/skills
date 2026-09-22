# Greenfield route

Scaffolding a brand-new web app before equipping it. A greenfield stack is a conversation, not a detection: agree the shape with the user first (framework, styling, anything they already know they want), applying these defaults where they haven't specified otherwise.

## Defaults

- Next.js App Router, TypeScript strict, `src/` directory, `@/*` alias, Tailwind on by default (drop `--tailwind` only when the project genuinely styles another way):

```bash
pnpm create next-app@latest . --typescript --app --src-dir --tailwind --import-alias '@/*' --use-pnpm
```

- `create-next-app` writes `AGENTS.md` and `CLAUDE.md` as files; keep `AGENTS.md`, replace `CLAUDE.md` with the symlink the instructions-file convention prescribes, and let `next dev` maintain its managed rules block in `AGENTS.md`

- pnpm as package manager (commit `pnpm-lock.yaml`); package scripts stay the command interface
- Tailwind CSS v4 for styling: tokens in the global stylesheet, component-level composition over one-off utility sprawl, design decisions recorded in the project's docs
- Cache Components on for greenfield per the standard (the user can decline)

## Then equip it

Return to the skill's process from step 2 (propose from the catalog) with the fresh app as the target. A new Next app on the preached path wants most of the catalog - the quality gate, browser verification, and design/UI entries in particular; deployment entries follow how it will ship.
