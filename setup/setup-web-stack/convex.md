# Convex branch

For a project with a `convex/` directory.
It gives every worktree its own local Convex deployment by scaffold, keeps crons to production, and turns the production-write rules into permissions.
Rationale and the config snippets are in the Convex section of [catalog.md](./catalog.md).
Every step converges on a state, so a re-run changes only what is behind.

1. **Worktree setup.** Copy [`recipes/worktree-setup.sh`](recipes/worktree-setup.sh) to `scripts/worktree-setup.sh`, fill its seed function, and name it on the "Set up" line of `docs/agents/dev-loop.md`.
   It creates a local deployment (`convex deployment create local --select`), with `--cloud` an expiring cloud dev deployment and its scoped key for work that needs a public URL.
   The script is the one thing besides the operator that uses the host's Convex login.
2. **Dev server and teardown.** Copy [`recipes/dev-server.sh`](recipes/dev-server.sh) to `scripts/dev-server.sh` with the project name and port range filled, and [`recipes/worktree-teardown.sh`](recipes/worktree-teardown.sh) to `scripts/worktree-teardown.sh`, named on the "Start", "Stop" and "Tear down" lines.
   A local deployment is served by one long-running `convex dev` per worktree (`convex-start`), since `convex dev --once` refuses beside a local backend; the teardown stops it and the worktree's `next dev` and removes the tree.
3. **Crons in production only.** `convex/crons.ts` registers no cron when the deployment's `CRONS` variable is `off`, declared in `convex.config.ts` as `v.optional(v.literal("off"))`.
   Convex reads it when functions are pushed, so the worktree setup sets it before the first push.
   Set it on the shared dev deployment and as the project's default for dev deployments (`convex env default set CRONS off --type dev`); production leaves it unset.
4. **Seed.** An idempotent internal function that creates the test identities `docs/agents/dev-loop.md` lists under "Seeded test identities", and stores what the project's crons would produce on a deployment that runs none.
5. **Default environment variables.** Set the Convex project's defaults for dev deployments (the sign-in keys and `CRONS`), so a fresh deployment, local ones included, can sign in.
   `pnpm exec convex env default set <NAME> --type dev --project <team>:<project>` sets one with the host's login; generate the sign-in keys fresh, never copy production's.
   This writes to the Convex project: the operator does it, or the owner where the operator has no access.
6. **Vercel builds** (projects deployed through Vercel). Copy [`recipes/vercel-build.sh`](recipes/vercel-build.sh) to `scripts/vercel-build.sh` and point `buildCommand` in `vercel.json` at it.
   The production deploy key goes in Vercel's Production environment as `CONVEX_DEPLOY_KEY`; previews build against the shared dev deployment through a Preview-scoped `NEXT_PUBLIC_CONVEX_URL`, with no Convex preview deployment.
7. **Lint, migrations, file manager.** Wire `@convex-dev/eslint-plugin` through oxlint, install `@convex-dev/migrations` as a component, and set `{"aiFiles": {"enabled": false}}` in `convex.json`.
8. **Prove it.** Run the worktree setup in a scratch worktree.
   Done when the seed lands on the worktree's own local deployment, the seeded identities can sign in there, the deployment registers no cron, and `scripts/check` passes from the worktree; then run the teardown.
