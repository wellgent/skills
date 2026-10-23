# Web stack catalog

Directory of community skills, tools, and known-good configs for web projects. This is not a checklist - read the target project, pick what serves it, skip the rest.

Rationale lives here; membership does not. The rules are in [`standards/web-products.md`](../../standards/web-products.md); a project's membership is what its `skills-lock.json` pins - this catalog explains what each entry is for.

A project pins a skill only when a line names it. Each entry says where that line is: a must-read trigger in the project's `AGENTS.md`, a line in its `docs/agents/dev-loop.md`, or the project's verification skill. Pin by commit: `npx skills add "<source>#<sha>" --skill <name>`, never `npx skills update`.

## Design and UI quality

- `impeccable` from `pbakaus/impeccable` - the design scanner, named on the "Design scanner" line of `docs/agents/dev-loop.md`: rendered `detect` on screens, with `doctor`, `shape`, per-option `critique` and `audit` for design work, and `init` and `document` when `PRODUCT.md` or `DESIGN.md` is missing. Pin 4.5.0 or later: engine 0.1.11 is the first that honours detector ignores in linked git worktrees. Run the scanner only through the pinned `.agents/skills/impeccable/scripts/impeccable detect`, so every session runs one engine. Run hosts set `DO_NOT_TRACK=1` and leave `OPENAI_API_KEY` unset, which keeps impeccable on its code-led path. Detector ignores live in `.impeccable/config.json`, each with its reason
- `web-design-guidelines` from `vercel-labs/agent-skills` - accessibility and UX guidelines; a must-read entry when a change touches a screen
- `vercel-react-best-practices` from `vercel-labs/agent-skills` - React/Next performance patterns; a must-read entry when a change renders or fetches data in React
- Next.js docs ship inside the `next` package (`node_modules/next/dist/docs/`), not as a skill. On 16.3+ nothing to install: `next dev` maintains a small marker-delimited rules block in `AGENTS.md` pointing agents at the bundled docs (`agentRules: false` in `next.config` opts out). On 16.2 the docs are bundled but no block is written: point `AGENTS.md` at `node_modules/next/dist/docs/` by hand. On 16.1 and earlier run `npx @next/codemod@canary agents-md` to copy version-matched docs into a gitignored `.next-docs/` indexed from `AGENTS.md`, and re-run it after Next upgrades. On 16.4+ a Next upgrade runs through `next upgrade --agent`. Next.js workflow skills live in `vercel/next.js` `/skills`

Design-system lint, blocking inside `check`:

- A class-value check that fails arbitrary radius, font-size, colour, spacing and size values, so screens use design tokens only
- A theme reset: the global stylesheet clears the framework's default palette (`--color-*: initial` in Tailwind's `@theme`) before declaring the tokens, so an off-system colour class does not exist
- oxlint `react/forbid-elements` over app code for raw controls (`button`, `input`, `select`, `textarea`), each message naming the kit component to use; the kit directory is exempt

Prototype scaffolding, on `main`:

- A variant switcher component for `?variant=` options on the real routes, rendered only when `VERCEL_ENV` is not `production`
- Only the variant code lives on the `prototype/<slug>` branch, previewed through `scripts/preview` on seeded data like any pull request; losing options are deleted at the pick

## Knowledge

- `find-docs` from `upstash/context7` - library docs lookup instead of guessing APIs; a must-read entry for any library API. The `ctx7` CLI authenticated on the machine (`npx ctx7 setup`) lifts the anonymous rate limit; the skill runs `npx ctx7@latest` and needs no other setup

## Browser tools

For any project with a UI a user opens in a browser. Both are named in the "Running the app" section of `docs/agents/dev-loop.md`, which feeds the project's verification skill.

- `agent-browser` from `vercel-labs/agent-browser` - navigate, interact, screenshot, extract. Native Rust CLI over CDP, no Playwright dependency: install once per machine with `brew install agent-browser && agent-browser install` (npm works where brew isn't an option). Its SKILL.md is a discovery stub - usage is served version-matched by `agent-browser skills get core`, so load that rather than trusting remembered syntax
- `next-dev-loop` from `vercel/next.js` - Next.js projects only: combines Next's `/_next/mcp` with `agent-browser`; needs a running `next dev`. Its check: `get_errors` returns nothing for the routes exercised
- Playwright is the test engine of the journey tests: one plain test per critical journey, in their own config, run by the `test:journeys` script against a started app
- How to launch, sign in to and drive the app is the "Running the app" section of the project's `docs/agents/dev-loop.md`; pstack's `create-verification-skill` writes the project's `verify` (or `verify-<app>`) skill from it

Known-good browser loop - never inspect a page with naive fetching (JS-rendered content comes back blank). Run it in a named session of your own (`export AGENT_BROWSER_SESSION=$(agent-browser session id --scope worktree --prefix verify)`, from a stable directory) so concurrent sessions never share a browser. Wait on a selector or text the page is known to render; `--load networkidle` only for pages known to go quiet:

```bash
agent-browser open http://localhost:3000 && agent-browser wait --selector main
agent-browser set viewport 375 812 && agent-browser screenshot --full mobile.png
agent-browser set viewport 1280 800 && agent-browser screenshot --full desktop.png
agent-browser close
```

If scroll-reveal animations hide content, try `agent-browser set media reduced-motion` first - built in, but only helps when the site respects `prefers-reduced-motion`. For sites that don't, force-reveal before capturing:

```bash
agent-browser eval --stdin <<'EVALEOF'
document.querySelectorAll('*').forEach(el => {
  const s = getComputedStyle(el);
  if (parseFloat(s.opacity) < 0.1 || s.transform !== 'none') {
    el.style.setProperty('opacity', '1', 'important');
    el.style.setProperty('transform', 'none', 'important');
    el.style.setProperty('transition', 'none', 'important');
  }
});
EVALEOF
```

## Quality gate (devDependencies, not skills)

A fast deterministic check pays off disproportionately with agents: they run it dozens of times per session, and "error, never warn" forces fixes where warnings get ignored. Worth proposing for any JS/TS project. For products built the preached way the composition is normative - see the Checks section of [`standards/web-products.md`](../../standards/web-products.md).

```bash
pnpm add -D typescript oxlint @nkzw/oxlint-config oxlint-tsgolint oxfmt knip dependency-cruiser @swc/core
```

TypeScript 7 installs under the plain `typescript` package name (never the `@typescript/native` alias split - it breaks `convex typecheck`). Next 16.3+ runs the project's `tsc` in `next build` by default (`experimental.useTypeScriptCli`); never set it `false` on TS 7, the build exits.

Scripts (pnpm shape; adapt the `check` chain for npm):

```json
{
  "format": "oxfmt .",
  "lint": "oxlint",
  "lint:format": "oxfmt --check .",
  "lint:deps": "depcruise src --config .dependency-cruiser.cjs",
  "knip": "knip",
  "typecheck": "next typegen && tsc --noEmit",
  "test": "vitest run",
  "test": "scripts/slot vitest run",
  "test:journeys": "scripts/slot sh -c 'playwright install chromium && playwright test --config e2e/journeys/playwright.config.ts \"$@\"' sh",
  "audit:prod": "node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON scripts/audit-prod.ts",
  "check": "scripts/slot sh -c 'scripts/check-docs && pnpm typecheck && pnpm lint && pnpm lint:format && pnpm knip && pnpm lint:deps && pnpm test && pnpm build'"
}
```

`next typegen` (Next.js projects) rewrites the route types under `.next/types` before `tsc` reads them, so a build directory left by an earlier commit cannot fail the typecheck. `check` is the one command every session and `scripts/check` run, and every step in it blocks - the check runs what production runs, so the full test suite and the real production build are inside it. A project with a design system adds its design-system lint to the chain, and a Convex project adds `convex` to the `depcruise` paths. `test:journeys` stays outside `check`, and `scripts/check` runs it after `check` against the worktree's own backend. `audit:prod` runs [`recipes/audit-prod.ts`](recipes/audit-prod.ts), copied to `scripts/audit-prod.ts`, with Node's warning about a TypeScript file in a package without `"type"` turned off so the probe prints only its report: the "Advisory probe" line of `docs/agents/dev-loop.md` names it, and it reports and never gates. A Next.js project sets `experimental.agentUpgrade: false` in `next.config.ts`, since under a coding agent Next's upgrade reminder exits `next build` and `next dev` with code 1 while an advisory is open, and the probe reports the advisory instead. Every Playwright config sets `outputDir` through [`recipes/output-dir.ts`](recipes/output-dir.ts), copied to `e2e/support/output-dir.ts`, so two worktrees never write one output directory. The verification skill reads the `next dev` log for `Hydration failed` and `Uncaught` lines since it started the server, which the browser console misses. Every test script runs through `scripts/slot` (from [`templates/project/scripts/slot`](../../templates/project/scripts/slot)), so each test run on the host holds one heavy-run slot and the slots alone bound memory, each run at the test runner's default worker count; a Playwright config that only a package script names goes into knip's Playwright plugin config (`"playwright": { "config": ["e2e/journeys/playwright.config.ts"] }`), since knip cannot read a config named inside `scripts/slot`, and an `entry` line alone leaves the journey files unused. Playwright keeps its browsers in one cache per host, and any project's `playwright install` removes the builds no live install names, a torn-down worktree's included, so `test:journeys` installs the Chromium build its own `@playwright/test` needs before every run, which does nothing when the build is there. Notes:

- Canonical `oxlint.config.ts` (nkzw preset, tsgolint `typeAware`, react/nextjs plugins) and `.oxfmtrc.json` baseline: copy the designated canonical project's files verbatim, per the standard
- Existing eslint + prettier projects: offer the migration, don't force it; if accepted, run oxc's own `migrate-oxlint` skill (`npx skills add https://github.com/oxc-project/oxc --skill migrate-oxlint`) or `npx @oxlint/migrate` on the flat config, get `check` green, and remove the replaced tooling in the same change. `@nkzw/oxlint-config` 2.x bundles its plugins: only `@nkzw/oxlint-config` and `@nkzw/eslint-plugin` stay in devDependencies, the individual `eslint-plugin-*` packages go
- knip: a per-repo config (`knip.json` or `knip.jsonc`) that ignores vendored agent trees (`.agents`, `.claude`) and docs, and declares runtime-read content files as entries; every ignore carries a written reason. A new ignore entry loosens a shared check, so the pull request names it
- dependency-cruiser on TypeScript 7: its TypeScript parser needs the compiler API, which TypeScript 7.0 does not ship, so the config sets `parser: "swc"` (hence `@swc/core`) and `tsConfig` for path aliases. It prints a `missing-typescript-transpiler` notice on every run; the result is complete. Start from the no-cycles rule and add one rule per module boundary the project sets, each `comment` carrying the fix:

```js
// .dependency-cruiser.cjs
module.exports = {
  forbidden: [
    {
      comment: "Break the cycle: move what both modules need into a third module that imports neither.",
      from: {},
      name: "no-circular",
      severity: "error",
      to: { circular: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    parser: "swc",
    tsConfig: { fileName: "tsconfig.json" },
    tsPreCompilationDeps: true,
  },
};
```

  The nkzw preset lints the config file too: its keys are sorted as above, and `oxlint.config.ts` carries an override `{ files: ["**/*.cjs"], env: { commonjs: true } }`. On pnpm 12, `@swc/core` needs `allowBuilds: { "@swc/core": false }` in `pnpm-workspace.yaml` (its binary arrives as an optional dependency, so the build script is not needed), and knip needs `ignoreDependencies: ["@swc/core"]` with the reason that dependency-cruiser loads it by name

- A blocking check that is red on `main` when it is introduced stays out of `check`, listed in the "Pending checks" section of `docs/agents/dev-loop.md` with what gets it green, until a run gets it green

Sign-off - [`recipes/check.sh`](recipes/check.sh), copied to `scripts/check` with the dev-server port range filled: on a clean PR branch it runs the frozen install, `check` and the journeys under one slot, and only on a pass pushes the head and posts the `check` commit status on it. [`templates/project/scripts/land`](../../templates/project/scripts/land) lands a pull request only on that status. An agent-run project has no GitHub Actions workflow. [`check.yml`](check.yml) is the job for a project with contributors outside runs: it runs `check` on their pull requests from forks, with build-time values the production build reads (`NEXT_PUBLIC_CONVEX_URL` on a Convex project) as repository secrets.

References: <https://cpojer.net/posts/fastest-frontend-tooling>, <https://github.com/nkzw-tech/oxlint-config>

## Convex backend

For any project with a `convex/` directory. Skills are from `get-convex/agent-skills`; upstream ships 33 - most are thin task cards or prod-ops loops built for Convex's own agent harness, and `convex-improve-convex-plugin` sends the coding-session transcript to Convex (opt-in with a consent prompt, still excluded), so pin only what a line names.
Keep the Convex SDK's file manager off: `convex.json` carries `{"aiFiles": {"enabled": false}}`, because `convex ai-files install` and `update` add the whole pack with no subset option, and `convex dev` would install it on first run without the switch.

- `convex-authz` - deterministic 4-shape authorization audit (identity-from-arg, missing ownership check, PII-leaking query, parent-reference-on-write) plus canonical requireIdentity/requireOwner hardening; a must-read entry when touching Convex code. Its scan matches raw registrars only, so functions built with custom builders are read by hand against the same four shapes
- `convex-reviewer` - Convex-specific review checklist (auth checks, `.filter()` table scans, `Date.now()` in queries, validator coverage, `internal.*` scheduling); a must-read entry before a Convex diff goes into a pull request
- `convex-migrate` - schema change plus data backfill on a deployed app via `@convex-dev/migrations`; a must-read entry when a change touches the schema of a populated table
- `convex/_generated/ai/guidelines.md` - Convex's own rules file and the Convex guidance agents read most; a must-read entry when touching Convex code. With the file manager off nothing updates it: each toolchain sweep replaces it with the current upstream `convex_rules.txt`

Lint - `@convex-dev/eslint-plugin` through oxlint `jsPlugins`, inside `pnpm lint`. Every rule is an error, the two off-by-default rules included; tests and fixtures are outside the override. Oxlint gives JS plugins no type information, so `explicit-table-ids` and `no-collect-in-query` run without their autofix. A deliberately anonymous public function carries a one-line disable with its reason:

```ts
// oxlint.config.ts
import convexPlugin from "@convex-dev/eslint-plugin";
import { defineConfig } from "oxlint";

export default defineConfig({
  jsPlugins: ["@convex-dev/eslint-plugin"],
  ignorePatterns: ["convex/_generated"],
  overrides: [
    {
      files: ["convex/**/*.ts"],
      excludeFiles: ["**/*.test.ts", "**/*.fixtures.ts"],
      rules: {
        ...Object.fromEntries(
          Object.keys(convexPlugin.rules).map((rule) => [`@convex-dev/${rule}`, "error"]),
        ),
      },
    },
  ],
});
```

On an existing codebase the rules start red, so until the cleanup they run from a second config file that spreads the main one, under a `lint:convex` script listed as a pending check. Adopting it is one preparatory run: `npx @convex-dev/codemod explicit-ids` for the implicit table-id calls, one index deleted from each prefix-redundant pair, and the reasoned disables.

Migrations - `@convex-dev/migrations`, installed as a component. Every production migration runs with `dryRun: true` first; the operator puts the dry run's row counts into the production-write approval on the request and runs the migration itself.

Deployments and keys:

- The run host's Convex login is used by the operator and by the worktree setup script; it stays readable on the host
- A local deployment per worktree - [`recipes/worktree-setup.sh`](recipes/worktree-setup.sh), copied to `scripts/worktree-setup.sh` and named on the "Set up" line of `docs/agents/dev-loop.md`. It installs dependencies, creates a local deployment (`convex deployment create local --select`), whose backend runs on the host with its state in the worktree's `.convex/`, uses no plan quota and no deployment slot, and takes the Convex project's default environment variables for dev deployments; it sets `CRONS=off`, pushes and runs the seed. One long-running `convex dev` per worktree serves it ([`recipes/dev-server.sh`](recipes/dev-server.sh) `convex-start`), since `convex dev --once` refuses beside a local backend; once the backend runs, `dev-server.sh` holds the worktree's Convex CLI to it alone: `.env.local` carries `CONVEX_SELF_HOSTED_URL` and `CONVEX_SELF_HOSTED_ADMIN_KEY` from `.convex/local/default/config.json` and a `CONVEX_OVERRIDE_ACCESS_TOKEN` Convex rejects, in place of `CONVEX_DEPLOYMENT`, so the CLI refuses `--prod` and the other deployment flags before any network call and the host's login is never used there; only the long-running `convex dev` gets the local deployment's name on its own command line. A local backend takes about 230 MB, which the host's heavy-run slots account for
- A cloud dev deployment only for work that needs a public URL (an inbound webhook, a cloud agent calling the app): `worktree-setup.sh --cloud` creates one named after the worktree that expires after 5 days, the longest Convex accepts, and saves a `CONVEX_DEPLOY_KEY` scoped to it (`convex deployment token create <name> --save-env`), so every `convex` command in that worktree reaches it only and the CLI ignores `--prod`
- [`recipes/host-claims.sh`](recipes/host-claims.sh), copied to `scripts/host-claims.sh` and sourced by `dev-server.sh` and `worktree-setup.sh`, keeps parallel worktrees on one host apart with claims under `${XDG_STATE_HOME:-$HOME/.local/state}/<project>/`, each a directory taken with `mkdir` that names its owner's pid and checkout and is free again once that pid is gone: a server's port, and one lock from a local backend's create through its first answer, since the Convex CLI picks a backend's ports without binding them. `dev-server.sh` names its pid and log files by the checkout and the port, reports a server ready only once this checkout's listener answers, stops only its own server, and serves a fresh production build on a claimed port with `serve-build`
- [`recipes/worktree-teardown.sh`](recipes/worktree-teardown.sh), copied to `scripts/worktree-teardown.sh`, stops the worktree's `next dev` and `convex dev` with its local backend, then every other process still running from the tree (by its working directory or a tree path on its command line, sparing the caller's own pipeline), and removes the tree, before a run posts its note
- Crons run in production only: `convex/crons.ts` registers none where `CRONS` is `off` (read when functions are pushed), set on the shared dev deployment, as the dev and preview default and by the worktree setup; the seed is an idempotent internal function that creates the test identities `docs/agents/dev-loop.md` lists and stores what the crons would
- Vercel holds the production deploy key in its Production environment and a preview deploy key (generated in the Convex dashboard, Project Settings) in its Preview environment, both as `CONVEX_DEPLOY_KEY`, and no `NEXT_PUBLIC_CONVEX_URL`, which `convex deploy --cmd` injects. [`recipes/vercel-build.sh`](recipes/vercel-build.sh), copied to `scripts/vercel-build.sh` with `"buildCommand": "bash scripts/vercel-build.sh"` in `vercel.json`, deploys production on a production build; on a preview build it creates a fresh Convex preview deployment named `pr-<number>` (`--preview-create`, passed in by `scripts/preview`) with the tree's functions and the seed (`--preview-run`), and sets its `SITE_URL` to the Vercel preview URL. Each new head recreates it, so an earlier head's preview URL stops working. Its other env comes from the project's preview defaults (`CRONS=off`, the dev-OTP switch, fresh sign-in keys, never production's). Convex removes a preview deployment 14 days after creation on Professional

Situational, pinned when the condition is met, each named by the line shown:

- `convex-quickstart` - standing up a new Convex project; named by the setup path, removed after scaffold
- `convex-auth` - a run that adds or changes sign-in (`@convex-dev/auth`); a must-read entry for that run
- `convex-create-component` - a run that builds a reusable Convex component; a must-read entry for that run
- `convex-migrate-rehearse` and `convex-backup` - before a destructive migration on populated production data; named in the production-write approval on the request

Left out: the `convex` router (it routes to skills outside any pin and recommends the AI-files install), `convex-docs` (covered by `find-docs` and the guidelines file), `convex-deploy-guard` (the held worktree CLI and scoped deploy keys do its job by permission), `convex-verify` (the negative tests the `convex-authz` checklist asks for cover it), and the findings and operations skills built for Convex's own findings bus (`convex-advisor`, `convex-insights`, `convex-launch-readiness`, `convex-optimize`, `convex-cost`). `convex insights --details` gives their data directly and is the first diagnostic for a write-conflict or slow-read question.

## Vercel deployment

For projects delivered through Vercel Git integration: a push to `main` builds production, every other git push is skipped, and a pull request labelled `preview` gets its preview from the Vercel CLI.

- `vercel-cli-with-tokens` from `vercel-labs/agent-skills` - drives the Vercel CLI via `VERCEL_TOKEN` (plus `VERCEL_PROJECT_ID`/`VERCEL_ORG_ID` instead of `vercel link`) where interactive `vercel login` isn't possible; named on the "Previews" line of `docs/agents/dev-loop.md` and by the post-ship deploy-status check
- Machine tools: `gh` and `vercel`, both authenticated; brew-install both (`vercel-cli`), never `npm i -g`

Builds - [`recipes/vercel-ignore.sh`](recipes/vercel-ignore.sh), copied to `scripts/vercel-ignore.sh` with `"ignoreCommand": "bash scripts/vercel-ignore.sh"` in `vercel.json`: it builds production and skips every other git push, so no branch builds a preview nobody opens. [`recipes/production-live.sh`](recipes/production-live.sh), copied to `scripts/production-live` with the production domain and the Vercel team and project ids, prints the git commit the production domain serves, read through `vercel api`. `scripts/land` waits for it to show `main`'s tip before it merges, since Vercel runs two production builds of close landings at once and the one that finishes last, older or not, sets the shared Convex production deployment. Needs the host's Vercel CLI login.

Previews - [`recipes/preview.sh`](recipes/preview.sh), copied to `scripts/preview` with the Vercel team and project ids from `.vercel/project.json`: it labels the pull request `preview`, deploys its head from a clean tree with the Vercel CLI (the ignored build step does not run for a CLI deployment), passing `PREVIEW_NAME=pr-<number>` to the build, and comments the URL on the pull request. A run labels an interaction-changing pull request this way for the owner's review, and `scripts/check` redeploys a labelled pull request's new head after each sign-off. Needs the host's Vercel CLI login.

Protected previews (Deployment Protection): configure Protection Bypass for Automation before feature work, store the secret as `VERCEL_AUTOMATION_BYPASS_SECRET`, and keep it out of commits and messages. This is HTTP-layer access to the deployed URL - `VERCEL_TOKEN` auth (`vercel-cli-with-tokens`) authenticates the CLI to the API and does not get requests past protection. For browser review, agent-browser's own `protected-vercel-deployments` skill (`agent-browser skills get protected-vercel-deployments`) is the preferred path: a short-lived OIDC token from `vercel project token` (CLI 53.3+) sent as `x-vercel-trusted-oidc-idp-token`, no long-lived secret in the session. The bypass secret stays for `vercel curl`. A reviewer outside the team opens a preview through a Vercel Shareable Link.

```bash
# needs a recent vercel CLI (the protection subcommand is not in older majors);
# on enable, Vercel generates a secret if none is passed
vercel project protection enable --protection-bypass --protection-bypass-secret "$VERCEL_AUTOMATION_BYPASS_SECRET"

# smoke test (expect 200) - vercel curl resolves the deployment URL and
# applies the bypass from VERCEL_AUTOMATION_BYPASS_SECRET automatically
vercel curl / -- -sS -o /dev/null -w "%{http_code}\n"

# raw equivalent, for arbitrary URLs or older CLIs
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "x-vercel-protection-bypass: $VERCEL_AUTOMATION_BYPASS_SECRET" \
  "https://<preview-url>"

# browser review through the protection
agent-browser set headers "{\"x-vercel-protection-bypass\":\"$VERCEL_AUTOMATION_BYPASS_SECRET\",\"x-vercel-set-bypass-cookie\":\"true\"}"
agent-browser open https://<preview-url> && agent-browser wait --selector main
```

## Situational skills

Pinned by the operator when the condition is met, and named by the line shown. The Convex ones are listed in the Convex section.

- `vercel-optimize` from `vercel-labs/agent-skills` - once the project has production traffic and Observability Plus; a must-read entry for a run that targets production performance
- `next-cache-components-optimizer` from `vercel/next.js` - a run that targets route performance with `cacheComponents` on; a must-read entry for that run
- `next-cache-components-adoption` from `vercel/next.js` - a run that turns `cacheComponents` on; a must-read entry for that run, removed once adoption is done
- `next-partial-prefetching-adoption` and `next-partial-prefetching-optimizer` from `vercel/next.js` - a run that adopts or tunes `partialPrefetching` on Next 16.3+, after Cache Components; must-read entries for that run
- `next-bundle-optimizer` from `vercel/next.js` - a run that targets bundle or initial-load size on Next 16.4+; a must-read entry for that run, run in its audit mode first
- `vercel-react-view-transitions` from `vercel-labs/agent-skills` - a run doing page transitions or shared-element motion with the React View Transition API; a must-read entry for that run
