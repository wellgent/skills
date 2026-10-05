# Web stack catalog

Directory of community skills, tools, and known-good configs for web projects. This is not a checklist - read the target project, pick what serves it, skip the rest.

Rationale lives here; membership does not. The rules are in [`standards/web-products.md`](../../standards/web-products.md); a team's skill membership is declared in its own private registry - this catalog explains what each entry is for.

A project pins a skill only when a flow step names it. Each entry says which step that is: a stage skill, the project's `AGENTS.md` must-read list, or a lens or tool line in its `docs/agents/dev-loop.md`. Pin by commit sha: `npx skills add <source>@<sha> --skill <name>`.

## Design and UI quality

- `impeccable` from `pbakaus/impeccable` - the design tool of the UX design stage, which runs its `doctor`, `shape`, per-option `critique`, `audit` and rendered `detect`, with `init` and `document` when `PRODUCT.md` or `DESIGN.md` is missing. Pin 4.5.0 or later: engine 0.1.11 is the first that honours detector ignores in linked git worktrees. Run the scanner only through the pinned `.agents/skills/impeccable/scripts/impeccable detect`, so every session runs one engine. Run hosts set `DO_NOT_TRACK=1` and leave `OPENAI_API_KEY` unset, which keeps impeccable on its code-led path. Detector ignores live in `.impeccable/config.json`, each with its reason
- `web-design-guidelines` from `vercel-labs/agent-skills` - accessibility and UX audit; a Review lens on UI diffs
- `vercel-composition-patterns` from `vercel-labs/agent-skills` - compound components, render props, context patterns; an Audit lens in the architecture review
- `vercel-react-best-practices` from `vercel-labs/agent-skills` - React/Next performance patterns; an Audit lens in the defect review
- Next.js docs ship inside the `next` package (`node_modules/next/dist/docs/`), not as a skill. On 16.3+ nothing to install: `next dev` maintains a small marker-delimited rules block in `AGENTS.md` pointing agents at the bundled docs (`agentRules: false` in `next.config` opts out). On 16.2 the docs are bundled but no block is written: point `AGENTS.md` at `node_modules/next/dist/docs/` by hand. On 16.1 and earlier run `npx @next/codemod@canary agents-md` to copy version-matched docs into a gitignored `.next-docs/` indexed from `AGENTS.md`, and re-run it after Next upgrades. Next.js workflow skills live in `vercel/next.js` `/skills`

Design-system lint, blocking inside `check`:

- A class-value check that fails arbitrary radius, font-size, colour, spacing and size values, so screens use design tokens only
- A theme reset: the global stylesheet clears the framework's default palette (`--color-*: initial` in Tailwind's `@theme`) before declaring the tokens, so an off-system colour class does not exist
- oxlint `react/forbid-elements` over app code for raw controls (`button`, `input`, `select`, `textarea`), each message naming the kit component to use; the kit directory is exempt

Prototype scaffolding, on `main`:

- A variant switcher component for `?variant=` options on the real routes, rendered only when `VERCEL_ENV` is not `production`
- An idempotent seed and unseed for the reviewer's records, as internal functions
- Only the variant code lives on the `prototype/<spec>-<slug>` branch; losing options are deleted at the pick

## Knowledge

- `find-docs` from `upstash/context7` - library docs lookup instead of guessing APIs; a must-read entry for any library API. The `ctx7` CLI authenticated on the machine (`npx ctx7 setup`) lifts the anonymous rate limit; the skill runs `npx ctx7@latest` and needs no other setup

## Browser tools

For any project with a UI a user opens in a browser. Both are QA tools; implementers run no browser walks.

- `agent-browser` from `vercel-labs/agent-browser` - navigate, interact, screenshot, extract. Native Rust CLI over CDP, no Playwright dependency: install once per machine with `brew install agent-browser && agent-browser install` (npm works where brew isn't an option). Its SKILL.md is a discovery stub - usage is served version-matched by `agent-browser skills get core`, so load that rather than trusting remembered syntax
- `next-dev-loop` from `vercel/next.js` - Next.js projects only: combines Next's `/_next/mcp` with `agent-browser`; needs a running `next dev`. Its named QA check: `get_errors` returns nothing for the routes exercised
- Playwright is the test engine of the journey tests, never a second reviewer: one plain test per critical journey, in their own config, run by the `test:journeys` script against a started app
- How to launch, sign in to and drive the app is the "Running the app" section of the project's `docs/agents/dev-loop.md`; a project carries no skill named `verify`

Known-good browser loop - never inspect a page with naive fetching (JS-rendered content comes back blank). Run it in a named session of your own (`export AGENT_BROWSER_SESSION=$(agent-browser session id --scope worktree --prefix qa)`, from a stable directory) so concurrent sessions never share a browser. Wait on a selector or text the page is known to render; `--load networkidle` only for pages known to go quiet:

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

A fast deterministic gate pays off disproportionately with agents: they run it dozens of times per session, and "error, never warn" forces fixes where warnings get ignored. Worth proposing for any JS/TS project. For products built the preached way the composition is normative - see the quality gate section of [`standards/web-products.md`](../../standards/web-products.md).

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
  "typecheck": "tsc --noEmit",
  "test": "vitest run",
  "test:journeys": "playwright test --config e2e/journeys/playwright.config.ts",
  "check": "pnpm typecheck && pnpm lint && pnpm lint:format && pnpm knip && pnpm lint:deps && pnpm test && pnpm build"
}
```

`check` is the single command agents gate on, and every step in it blocks - the gate runs what production runs, so the full test suite and the real production build are inside it. A project with a design system adds its design-system lint to the chain, and a Convex project adds `convex` to the `depcruise` paths. `test:journeys` stays outside `check`: `flow gate` runs it once per spec from the "Journey tests" line of `docs/agents/dev-loop.md`. Notes:

- Canonical `oxlint.config.ts` (nkzw preset, tsgolint `typeAware`, react/nextjs plugins) and `.oxfmtrc.json` baseline: copy the designated canonical project's files verbatim, per the standard
- Existing eslint + prettier projects: offer the migration, don't force it; if accepted, run oxc's own `migrate-oxlint` skill (`npx skills add https://github.com/oxc-project/oxc --skill migrate-oxlint`) or `npx @oxlint/migrate` on the flat config, get `check` green, and remove the replaced tooling in the same change. `@nkzw/oxlint-config` 2.x bundles its plugins: only `@nkzw/oxlint-config` and `@nkzw/eslint-plugin` stay in devDependencies, the individual `eslint-plugin-*` packages go
- knip: a per-repo config (`knip.json` or `knip.jsonc`) that ignores vendored agent trees (`.agents`, `.claude`) and docs, and declares runtime-read content files as entries; every ignore carries a written reason. A new ignore entry loosens a shared check, so it needs the ticket or the lead
- dependency-cruiser on TypeScript 7: its TypeScript parser needs the compiler API, which TypeScript 7.0 does not ship, so the config sets `parser: "swc"` (hence `@swc/core`) and `tsConfig` for path aliases. It prints a `missing-typescript-transpiler` notice on every run; the result is complete. Start from the no-cycles rule and add one rule per ADR that sets a boundary, each `comment` carrying the fix:

```js
// .dependency-cruiser.cjs
module.exports = {
  forbidden: [
    {
      name: "no-circular",
      severity: "error",
      comment: "Break the cycle: move what both modules need into a third module that imports neither.",
      from: {},
      to: { circular: true },
    },
  ],
  options: {
    parser: "swc",
    tsConfig: { fileName: "tsconfig.json" },
    tsPreCompilationDeps: true,
    doNotFollow: { path: "node_modules" },
  },
};
```

- A blocking check that is red on `main` when it is introduced stays out of `check` until a cleanup spec gets it green; until then its count is a scanner-pass number
- Installing Matt's `code-review` project skill replaces the bundled `/code-review` (a project skill wins over a bundled one of the same name); the bundled review stays reachable as `/review`

Scanner pass - measured at each Audit and recorded with `flow ledger scan`, never pass/fail. The commands go on the "Scanner pass" lines of `docs/agents/dev-loop.md`:

- `unused_code`: `pnpm knip --reporter json`, counting issues; zero on a repo that carries knip in `check`
- `duplication_source_pct`, `duplication_tests_pct`: `pnpm dlx jscpd --min-tokens 50 --min-lines 5 --reporters json` twice, once over source with tests, fixtures and generated code ignored, once over the test and fixture files alone. jscpd finds textual clones only; logic duplicated under different names is the Audit defect review's lens
- `dependency_violations`: `pnpm lint:deps --output-type json`, counting violations
- `suppressions`: a grep count of `oxlint-disable`, `eslint-disable`, `@ts-expect-error`, `@ts-ignore` and `as any` over source
- `tests`, `test_seconds`: the test run's own summary
- `source_lines`, `test_lines`: `git ls-files` piped to `wc -l`, split by the test file pattern
- `react_doctor` (project measure): `pnpm dlx react-doctor@latest . --no-score --no-supply-chain`, the `N issues` line. `--no-score` keeps the score upload, share URL and usage telemetry off; `--no-supply-chain` keeps the dependency lookups off

References: <https://cpojer.net/posts/fastest-frontend-tooling>, <https://github.com/nkzw-tech/oxlint-config>

## Convex backend

For any project with a `convex/` directory. Skills are from `get-convex/agent-skills`; upstream ships 33 - most are thin task cards or prod-ops loops built for Convex's own agent harness, and `convex-improve-convex-plugin` sends the coding-session transcript to Convex (opt-in with a consent prompt, still excluded), so pin only what a step names.
Keep the Convex SDK's file manager off: `convex.json` carries `{"aiFiles": {"enabled": false}}`, because `convex ai-files install` and `update` add the whole pack with no subset option, and `convex dev` would install it on first run without the switch.

- `convex-authz` - deterministic 4-shape authorization audit (identity-from-arg, missing ownership check, PII-leaking query, parent-reference-on-write) plus canonical requireIdentity/requireOwner hardening; a must-read entry when touching Convex code. Its scan matches raw registrars only, so functions built with custom builders are read by hand against the same four shapes
- `convex-reviewer` - Convex-specific review checklist (auth checks, `.filter()` table scans, `Date.now()` in queries, validator coverage, `internal.*` scheduling); a Review lens on Convex diffs
- `convex-migrate` - schema change plus data backfill on a deployed app via `@convex-dev/migrations`; a must-read entry when a ticket changes the schema of a populated table
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
          Object.keys(convexPlugin.configs.recommended[0].rules).map((rule) => [rule, "error"]),
        ),
        "@convex-dev/import-wrong-runtime": "error",
        "@convex-dev/no-collect-in-query": "error",
        "@convex-dev/require-access-control": "error",
      },
    },
  ],
});
```

Adopting it on an existing codebase is one preparatory ticket: `npx @convex-dev/codemod explicit-ids` for the implicit table-id calls, one index deleted from each prefix-redundant pair, and the reasoned disables.

Migrations - `@convex-dev/migrations`, installed as a component. Every production migration runs with `dryRun: true` first; the lead puts the dry run's row counts into the production-write approval and runs the migration itself.

Deploy keys - production reach is a permission, not a prompt:

- The run host's Convex login belongs to the lead session
- Every worktree works through a `CONVEX_DEPLOY_KEY` in its `.env.local`, scoped to that worktree's own dev deployment: `convex deployment token create <name> --save-env`. With the key in scope every `convex` command in that directory reaches that deployment only
- Vercel holds the production deploy key in its Production environment and the preview deploy key in its Preview environment, both as `CONVEX_DEPLOY_KEY`

One dev deployment per worktree - [`recipes/worktree-setup.sh`](recipes/worktree-setup.sh), copied to `scripts/worktree-setup.sh` and named on the "Set up" line of `docs/agents/dev-loop.md`. It installs dependencies, creates an expiring cloud dev deployment named after the worktree, mints the scoped key, pushes the functions once and runs the seed. The seed is an idempotent internal function that creates the test identities `docs/agents/dev-loop.md` lists. New dev deployments take their environment variables from the Convex project's default environment variables, so the sign-in keys are set there once. A deployment is removed by its expiry.

Prototype previews - [`recipes/vercel-build.sh`](recipes/vercel-build.sh), copied to `scripts/vercel-build.sh` with `"buildCommand": "bash scripts/vercel-build.sh"` in `vercel.json`. A `prototype/*` branch build runs `convex deploy` with the preview deploy key, which creates a Convex preview deployment named after the branch and seeds it through `--preview-run`. Preview deployments expire (5 days on the free plans, 14 on paid); a round that outlives one redeploys and reseeds. Preview sign-in keys come from the project's default environment variables for previews.

Production records in a prototype - [`recipes/prototype-copy.sh`](recipes/prototype-copy.sh), copied to `scripts/prototype-copy.sh`. The lead runs it with the preview deployment's name, the reviewer and the tables of the client-approved allowlist on the project card. The project supplies the two internal functions it calls: a read that returns one owner's rows of one allowlisted table and refuses any other table, and a write that inserts them with ids remapped and refuses outside a preview deployment.

Situational, pinned when the condition is met, each named by the step shown:

- `convex-quickstart` - standing up a new Convex project; named by the setup path, removed after scaffold
- `convex-auth` - a spec that adds or changes sign-in (`@convex-dev/auth`); a must-read entry for that spec
- `convex-create-component` - a spec that builds a reusable Convex component; a must-read entry for that spec
- `convex-migrate-rehearse` and `convex-backup` - before a destructive migration on populated production data; named in the lead's production-write approval

Left out: the `convex` router (it routes to skills outside any pin and recommends the AI-files install), `convex-docs` (covered by `find-docs` and the guidelines file), `convex-deploy-guard` (scoped deploy keys do its job by permission), `convex-verify` (the test bar's first point asks for the same negative tests), and the audit and operations skills built for Convex's own findings bus (`convex-advisor`, `convex-insights`, `convex-launch-readiness`, `convex-optimize`, `convex-cost`). `convex insights --details` gives their data directly and is the first diagnostic for a write-conflict or slow-read question.

## Vercel deployment

For projects delivered through Vercel Git integration (branch push → preview, push to main → production).

- `vercel-cli-with-tokens` from `vercel-labs/agent-skills` - drives the Vercel CLI via `VERCEL_TOKEN` (plus `VERCEL_PROJECT_ID`/`VERCEL_ORG_ID` instead of `vercel link`) where interactive `vercel login` isn't possible; named by the lead's Release and by the prototype deploy
- Machine tools: `gh` and `vercel`, both authenticated; brew-install both (`vercel-cli`), never `npm i -g`

Skip builds for markdown-only commits - `vercel.json`:

```json
{
  "ignoreCommand": "bash scripts/vercel-ignore-docs.sh"
}
```

`scripts/vercel-ignore-docs.sh`:

```bash
#!/usr/bin/env bash
# Skip Vercel builds when only markdown files changed.
set -euo pipefail

current_sha="${VERCEL_GIT_COMMIT_SHA:-HEAD}"
prev_sha="${VERCEL_GIT_PREVIOUS_SHA:-}"

if [ -n "$prev_sha" ] && git cat-file -e "$prev_sha^{commit}" 2>/dev/null; then
  files="$(git diff --name-only "$prev_sha" "$current_sha")"
else
  files="$(git show --name-only --pretty=format: "$current_sha")"
fi

if echo "$files" | grep -qvE '(^$|.*\.md$)'; then
  exit 1  # non-markdown changed -> build
else
  exit 0  # only markdown -> skip
fi
```

Protected previews (Deployment Protection): configure Protection Bypass for Automation before feature work, store the secret as `VERCEL_AUTOMATION_BYPASS_SECRET`, and keep it out of commits and messages. This is HTTP-layer access to the deployed URL - `VERCEL_TOKEN` auth (`vercel-cli-with-tokens`) authenticates the CLI to the API and does not get requests past protection. For browser review, agent-browser's own `protected-vercel-deployments` skill (`agent-browser skills get protected-vercel-deployments`) is the preferred path: a short-lived OIDC token from `vercel project token` (CLI 53.3+) sent as `x-vercel-trusted-oidc-idp-token`, no long-lived secret in the session. The bypass secret stays for `vercel curl` and CI. A reviewer outside the team opens a prototype through a Vercel Shareable Link.

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

Pinned by the lead when the condition is met, and named by the step shown. The Convex ones are listed in the Convex section.

- `vercel-optimize` from `vercel-labs/agent-skills` - once the project has production traffic and Observability Plus; an Audit lens in the defect review
- `next-cache-components-optimizer` from `vercel/next.js` - a spec that targets route performance with `cacheComponents` on; a must-read entry for that spec
- `next-cache-components-adoption` from `vercel/next.js` - a spec that turns `cacheComponents` on; a must-read entry for that spec, removed once adoption is done
- `next-partial-prefetching-adoption` and `next-partial-prefetching-optimizer` from `vercel/next.js` - a spec that adopts or tunes `partialPrefetching` on Next 16.3+, after Cache Components; must-read entries for that spec
- `vercel-react-view-transitions` from `vercel-labs/agent-skills` - a spec doing page transitions or shared-element motion with the React View Transition API; a must-read entry for that spec
