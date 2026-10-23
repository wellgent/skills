# Convex branch

For a project with a `convex/` directory.
It gives every worktree its own local Convex deployment by scaffold, keeps crons to production, and turns the production-write rules into permissions.
Rationale and the config snippets are in the Convex section of [catalog.md](./catalog.md).
Every step converges on a state, so a re-run changes only what is behind.

1. **Worktree setup.** Copy [`recipes/worktree-setup.sh`](recipes/worktree-setup.sh) to `scripts/worktree-setup.sh`, fill its seed function, and name it on the "Set up" line of `docs/agents/dev-loop.md`.
   It creates a local deployment (`convex deployment create <team>:<project>:local --select`, with the team and project the main checkout's `CONVEX_DEPLOYMENT` comment names), with `--cloud` an expiring cloud dev deployment and its scoped key for work that needs a public URL.
   It never copies the main checkout's `CONVEX_DEPLOYMENT` line, so only a created deployment is ever written to the worktree's `.env.local`, and a rerun after a failed create cannot reach the shared dev deployment.
   A create the Convex API answers with a 5xx runs again once.
   The script is the one thing besides the operator that uses the host's Convex login.
2. **Dev server, host claims and teardown.** Copy [`recipes/host-claims.sh`](recipes/host-claims.sh) to `scripts/host-claims.sh` with the project name filled, [`recipes/dev-server.sh`](recipes/dev-server.sh) to `scripts/dev-server.sh` with the lowest dev-server port filled, and [`recipes/worktree-teardown.sh`](recipes/worktree-teardown.sh) to `scripts/worktree-teardown.sh`, named on the "Start", "Stop" and "Tear down" lines.
   A local deployment is served by one long-running `convex dev` per worktree (`convex-start`), since `convex dev --once` refuses beside a local backend.
   `convex-start` waits for the first push of the `convex dev` that serves the worktree, a running one included, and counts one still in its `node_modules/.bin/convex` shell wrapper as running.
   `host-claims.sh` keeps parallel worktrees on one host apart: `start` and `serve-build` claim their port and refuse one another worktree holds, and the local backend's create and first start run under one host-wide lock, since the Convex CLI picks a backend's ports without binding them.
   The pid and log files are named by the checkout and the port, a server is ready only once this checkout's listener answers, and `stop` stops only this checkout's server.
   `serve-build <port>` serves a fresh production build through `next start` on a claimed port.
   The teardown stops the worktree's servers and `convex dev`, then every other process still running from the tree, and removes the tree.
   Once the backend runs, the dev server holds the worktree's Convex CLI to it alone (`CONVEX_SELF_HOSTED_URL`, `CONVEX_SELF_HOSTED_ADMIN_KEY` and a rejected `CONVEX_OVERRIDE_ACCESS_TOKEN` in `.env.local`), so nothing run from the worktree reaches production.
3. **Crons in production only.** `convex/crons.ts` registers no cron when the deployment's `CRONS` variable is `off`, declared in `convex.config.ts` as `v.optional(v.literal("off"))`.
   Convex reads it when functions are pushed, so the worktree setup sets it before the first push.
   Set it on the shared dev deployment and as the project's default for dev and preview deployments (`convex env default set CRONS off --type dev`, and `--type preview`); production leaves it unset.
4. **Seed.** An idempotent internal function that creates the test identities `docs/agents/dev-loop.md` lists under "Seeded test identities", and stores what the project's crons would produce on a deployment that runs none.
5. **Default environment variables.** Set the Convex project's defaults for dev and for preview deployments (the sign-in keys, the dev-OTP switch and `CRONS`), so a fresh deployment, local and preview ones included, can sign in.
   `pnpm exec convex env default set <NAME> --type dev --project <team>:<project> -- <value>` sets one with the host's login; generate the sign-in keys fresh, never copy production's.
   The value goes after `--`: `JWT_PRIVATE_KEY` is a PEM that starts with dashes, and without `--` the CLI reads it as an option and prints it in its error.
   This writes to the Convex project: the operator does it, or the owner where the operator has no access.
6. **Vercel builds** (projects deployed through Vercel). Copy [`recipes/vercel-build.sh`](recipes/vercel-build.sh) to `scripts/vercel-build.sh` and point `buildCommand` in `vercel.json` at it.
   The production deploy key goes in Vercel's Production environment and the preview deploy key in its Preview environment, both as `CONVEX_DEPLOY_KEY`, with no `NEXT_PUBLIC_CONVEX_URL` there.
   A preview deploy key is generated only in the Convex dashboard (Project Settings, Preview Deploy Keys), so this is the owner's step where the operator has no dashboard access.
   A preview build gets a fresh Convex preview deployment with the pull request's functions and the seed.
7. **Lint, migrations, file manager.** Wire `@convex-dev/eslint-plugin` through oxlint, install `@convex-dev/migrations` as a component, and set `{"aiFiles": {"enabled": false}}` in `convex.json`.
8. **Prove it.** Run the worktree setup in a scratch worktree.
   Done when the seed lands on the worktree's own local deployment, the seeded identities can sign in there, the deployment registers no cron, and `scripts/check` passes from the worktree; then run the teardown.
