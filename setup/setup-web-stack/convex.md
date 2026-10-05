# Convex branch

For a project with a `convex/` directory.
It gives every worktree its own dev deployment by scaffold, and turns the production-write rules into permissions.
Rationale and the config snippets are in the Convex section of [catalog.md](./catalog.md).
Every step converges on a state, so a re-run changes only what is behind.

1. **Worktree setup.** Copy [`recipes/worktree-setup.sh`](recipes/worktree-setup.sh) to `scripts/worktree-setup.sh`, fill its seed function, and name it on the "Set up" line of `docs/agents/dev-loop.md`.
   The script is the one thing outside the lead that uses the host's Convex login: creating a dev deployment and minting its key is refused with a deploy key in scope.
2. **Seed.** An idempotent internal function that creates the test identities `docs/agents/dev-loop.md` lists under "Seeded test identities".
3. **Default environment variables.** Set the Convex project's defaults for dev and preview deployments (the sign-in keys), so a fresh deployment can sign in.
   This writes to the Convex project: the lead does it, or the client where the lead has no access.
4. **Vercel builds** (projects deployed through Vercel). Copy [`recipes/vercel-build.sh`](recipes/vercel-build.sh) to `scripts/vercel-build.sh` and point `buildCommand` in `vercel.json` at it.
   The production deploy key goes in Vercel's Production environment and the preview deploy key in its Preview environment, both as `CONVEX_DEPLOY_KEY`.
5. **Prototype copy.** Once the client has approved the seed allowlist on the project card: copy [`recipes/prototype-copy.sh`](recipes/prototype-copy.sh) to `scripts/prototype-copy.sh` and scaffold its read and write functions.
   Before that approval, skip this step and say so in the report.
6. **Lint, migrations, file manager.** Wire `@convex-dev/eslint-plugin` through oxlint, install `@convex-dev/migrations` as a component, and set `{"aiFiles": {"enabled": false}}` in `convex.json`.
7. **Prove it.** Run the worktree setup in a scratch worktree, then run `npx convex run --prod <any function>` there.
   Done when the command is refused with the worktree's scoped key in scope, and the seeded identities can sign in on the worktree's deployment.
