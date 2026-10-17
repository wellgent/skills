# Convex branch

For a project with a `convex/` directory.
It gives every worktree its own dev deployment by scaffold, and turns the production-write rules into permissions.
Rationale and the config snippets are in the Convex section of [catalog.md](./catalog.md).
Every step converges on a state, so a re-run changes only what is behind.

1. **Worktree setup.** Copy [`recipes/worktree-setup.sh`](recipes/worktree-setup.sh) to `scripts/worktree-setup.sh`, fill its seed function, and name it on the "Set up" line of `docs/agents/dev-loop.md`.
   The script is the one thing besides the operator that uses the host's Convex login: creating a dev deployment and minting its key is refused with a deploy key in scope.
2. **Seed.** An idempotent internal function that creates the test identities `docs/agents/dev-loop.md` lists under "Seeded test identities".
3. **Default environment variables.** Set the Convex project's defaults for dev and preview deployments (the sign-in keys), so a fresh deployment can sign in.
   `pnpm exec convex env default set <NAME> --type dev|preview --project <team>:<project>` sets one with the host's login; generate the sign-in keys fresh, never copy production's.
   A default holds one value for every deployment, so a site URL default cannot follow per-branch preview URLs: sign-in paths that send a link need it set per deployment.
   This writes to the Convex project: the operator does it, or the owner where the operator has no access.
4. **Vercel builds** (projects deployed through Vercel). Copy [`recipes/vercel-build.sh`](recipes/vercel-build.sh) to `scripts/vercel-build.sh` and point `buildCommand` in `vercel.json` at it.
   The production deploy key goes in Vercel's Production environment and the preview deploy key in its Preview environment, both as `CONVEX_DEPLOY_KEY`.
   A preview deploy key is generated only in the Convex dashboard (Project Settings, Preview Deploy Keys), so this is the owner's step where the operator has no dashboard access.
5. **Prototype copy.** Once the owner has approved the seed allowlist (the tables, keyed to the reviewer's own user, that a prototype may copy from production; recorded in `PRODUCT.md`): copy [`recipes/prototype-copy.sh`](recipes/prototype-copy.sh) to `scripts/prototype-copy.sh` and scaffold its read and write functions.
   The write takes every table in one call, so ids that rows share across tables are remapped together.
   A function cannot tell a preview deployment from the others, so the write checks a marker variable set only in the project's preview defaults.
   Before that approval, skip this step and say so in the report.
6. **Lint, migrations, file manager.** Wire `@convex-dev/eslint-plugin` through oxlint, install `@convex-dev/migrations` as a component, and set `{"aiFiles": {"enabled": false}}` in `convex.json`.
7. **CI.** The production build in `check` reads the deployment URL: `NEXT_PUBLIC_CONVEX_URL` as a repository secret, named in [`check.yml`](./check.yml).
8. **Prove it.** Run the worktree setup in a scratch worktree, then run `pnpm exec convex run --prod <the seed function>` there.
   Done when the CLI reports that it ignores `--prod` and the command lands on the worktree's own deployment, and the seeded identities can sign in there.
