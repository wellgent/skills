# Web stack catalog

Directory of community skills, tools, and known-good configs for web projects. This is not a checklist - read the target project, pick what serves it, skip the rest.

Rationale lives here; membership does not. The rules are in [`standards/web-products.md`](../../standards/web-products.md); a team's skill membership is declared in its own private registry - this catalog explains what each entry is for.

## Design and UI quality

- `impeccable` from `pbakaus/impeccable` - the go-to for UI/UX/branding work: design direction and quality bar for any project with a visual surface
- `web-design-guidelines` from `vercel-labs/agent-skills` - accessibility and UX audit during review
- `vercel-composition-patterns` from `vercel-labs/agent-skills` - compound components, render props, context patterns
- `vercel-react-best-practices` from `vercel-labs/agent-skills` - React/Next performance patterns
- `vercel-react-view-transitions` from `vercel-labs/agent-skills` - React View Transition API for page transitions, shared-element and list animations; only for projects doing that kind of motion work
- Next.js docs ship inside the `next` package (`node_modules/next/dist/docs/`), not as a skill. On 16.3+ nothing to install: `next dev` maintains a small marker-delimited rules block in `AGENTS.md` pointing agents at the bundled docs (`agentRules: false` in `next.config` opts out). On 16.2 the docs are bundled but no block is written: point `AGENTS.md` at `node_modules/next/dist/docs/` by hand. On 16.1 and earlier run `npx @next/codemod@canary agents-md` to copy version-matched docs into a gitignored `.next-docs/` indexed from `AGENTS.md`, and re-run it after Next upgrades. Next.js workflow skills live in `vercel/next.js` `/skills`
- `next-cache-components-adoption` and `next-cache-components-optimizer` from `vercel/next.js` - Next 16+ projects turning on or tuning `cacheComponents`: adoption flips the flag and works through the blocking routes it surfaces, the optimizer tunes the static shell and route navigation once it's on
- `next-partial-prefetching-adoption` and `next-partial-prefetching-optimizer` from `vercel/next.js` - the same pair for `partialPrefetching` on Next 16.3+ with Cache Components on: adoption flips the flag and opts routes in (`export const prefetch = 'partial'`) through the insights it surfaces; the optimizer tunes what selected client navigations prefetch (default, viewport, intent) once both flags are live. Adopt after Cache Components, not alongside

## Knowledge and writing

- `find-docs` from `upstash/context7` - library docs lookup instead of guessing APIs; the `ctx7` CLI authenticated on the machine (`npx ctx7 setup`) lifts the anonymous rate limit; the skill runs `npx ctx7@latest` and needs no other setup
- `writing-guidelines` from `vercel-labs/agent-skills` - reviews docs and prose against Vercel's writing guidelines; useful in nearly any project with user-facing text

## Browser verification

For any project with a UI a user opens in a browser - it is how an agent observes what it actually built.

- `agent-browser` from `vercel-labs/agent-browser` - navigate, interact, screenshot, extract. Native Rust CLI over CDP, no Playwright dependency: install once per machine with `brew install agent-browser && agent-browser install` (npm works where brew isn't an option). Its SKILL.md is a discovery stub - usage is served version-matched by `agent-browser skills get core`, so load that rather than trusting remembered syntax
- `next-dev-loop` from `vercel/next.js` - Next.js projects only: verifies runtime behavior after edits by combining Next's `/_next/mcp` with `agent-browser`; needs a running `next dev`. agent-browser is the sole browser driver - Playwright stays a test engine where a project runs Playwright tests, never a second reviewer
- A repo `verify` skill plus an ephemeral dev-server script - both set up by the `setup-verify` setup path (source: wellgent/skills, checkout-run): the project-specific manual for launching, signing in as an agent, and driving the app, and the port-scoped `scripts/dev-server.sh` it rides on. The dev-loop workflow's gate calls `/verify` for any ticket with runtime surface, and the skill is where hard-won driving gotchas accumulate

Known-good review loop - never verify visually with naive fetching (JS-rendered content comes back blank). Run it in a named session of your own (`export AGENT_BROWSER_SESSION=$(agent-browser session id --scope worktree --prefix verify)`, from a stable directory) so concurrent sessions never share a browser. Wait on a selector or text the page is known to render; `--load networkidle` only for pages known to go quiet:

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
pnpm add -D typescript oxlint @nkzw/oxlint-config oxlint-tsgolint oxfmt
```

TypeScript 7 installs under the plain `typescript` package name (never the `@typescript/native` alias split - it breaks `convex typecheck`). Next 16.3+ runs the project's `tsc` in `next build` by default (`experimental.useTypeScriptCli`); never set it `false` on TS 7, the build exits.

Scripts (pnpm shape; adapt the `check` chain for npm):

```json
{
  "format": "oxfmt .",
  "lint": "oxlint",
  "lint:format": "oxfmt --check .",
  "typecheck": "tsc --noEmit",
  "test": "vitest run",
  "check": "pnpm typecheck && pnpm lint && pnpm lint:format && pnpm test && pnpm build"
}
```

`check` is the single command agents gate on - the gate runs what production runs, so the full test suite and the real production build are inside it. Notes:

- Canonical `oxlint.config.ts` (nkzw preset, tsgolint `typeAware`, react/nextjs plugins) and `.oxfmtrc.json` baseline: copy the designated canonical project's files verbatim, per the standard
- Existing eslint + prettier projects: offer the migration, don't force it; if accepted, run oxc's own `migrate-oxlint` skill (`npx skills add https://github.com/oxc-project/oxc --skill migrate-oxlint`) or `npx @oxlint/migrate` on the flat config, get `check` green, and remove the replaced tooling in the same change. `@nkzw/oxlint-config` 2.x bundles its plugins: only `@nkzw/oxlint-config` and `@nkzw/eslint-plugin` stay in devDependencies, the individual `eslint-plugin-*` packages go
- On-demand React scan that complements code review: `pnpm dlx react-doctor@latest . --diff main --verbose`

References: <https://cpojer.net/posts/fastest-frontend-tooling>, <https://github.com/nkzw-tech/oxlint-config>

## Convex backend

For any project with a `convex/` directory. All from `get-convex/agent-skills`; upstream ships 33 - most are thin task cards or prod-ops loops built for Convex's own agent harness, and `convex-improve-convex-plugin` sends the coding-session transcript to Convex (opt-in with a consent prompt, still excluded), so pick deliberately rather than installing `--all`.
Keep the Convex SDK's file manager off: `convex.json` carries `{"aiFiles": {"enabled": false}}`, because `convex ai-files install` and `update` add the whole pack with no subset option, and `convex dev` would install it on first run without the switch.

- `convex` - entry-point router: recognizes Convex work and routes to the specific convex-* skill
- `convex-auth` - wire authentication (`@convex-dev/auth`, OAuth/passkeys) including the auth.config.ts plumbing
- `convex-authz` - deterministic 4-shape authorization audit (identity-from-arg, missing ownership check, PII-leaking query, parent-reference-on-write) plus canonical requireIdentity/requireOwner hardening and tsc verify; targets the measured top defect class in agent-built Convex backends
- `convex-create-component` - build a reusable Convex component with clear boundaries; the deepest skill in the set
- `convex-deploy-guard` - identify and announce the target deployment before any deployment-affecting command, fresh per-action consent for prod, read-only session mode, MCP prod-flag discipline; other convex skills compose it as step 0
- `convex-docs` - version-currency discipline: pin the installed convex/component versions and fetch current docs or node_modules types instead of writing a possibly-stale API from memory
- `convex-migrate` - schema change + data backfill on a deployed app via `@convex-dev/migrations`
- `convex-optimize` - broad audit of an existing app: security, scale, upgrades, observability
- `convex-quickstart` - stand up a new Convex + web project; greenfield path
- `convex-reviewer` - Convex-specific review checklist (auth checks, `.filter()` table scans, `Date.now()` in queries, validator coverage, `internal.*` scheduling) for the review stage; catches what generic code review misses
- `convex-verify` - prove a built feature: seed, drive as owner / other user / unauthenticated via convex-test `withIdentity`, assert positive and negative behavior; the negative authz assertions are the load-bearing half

Situational, adopt per project when the need is real: `convex-migrate-rehearse` and `convex-backup` (snapshot-rehearsed schema changes and restore drills once production data matters), `convex-advisor` (read-limit/OCC insights on large tables), `convex-billing` (Stripe), `convex-agent` (`@convex-dev/agent` backends), `convex-launch-readiness` (pre-launch composite audit), `convex-cost` (ranks functions by read volume and projects spend, pairs with the advisor), `convex-insights` (logs and health in natural language over the official MCP), `convex-explain-app` (read-only explainer from schema and functions, for onboarding), `convex-seed` (seed or import data), `convex-domains` (custom domains).

## Vercel deployment

For projects delivered through Vercel Git integration (branch push → preview, push to main → production).

- `deploy-to-vercel` from `vercel-labs/agent-skills` - preview deploys, project linking, git-push setup
- `vercel-cli-with-tokens` from `vercel-labs/agent-skills` - drives the Vercel CLI via `VERCEL_TOKEN` (plus `VERCEL_PROJECT_ID`/`VERCEL_ORG_ID` instead of `vercel link`) where interactive `vercel login` isn't possible; for headless environments (CI, cloud agents) - auth plumbing that complements `deploy-to-vercel`, not a second deploy path
- `vercel-optimize` from `vercel-labs/agent-skills` - metric-backed cost and performance recommendations for deployed projects (bill, slow or expensive routes, caching, Core Web Vitals)
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

Protected previews (Deployment Protection): configure Protection Bypass for Automation before feature work, store the secret as `VERCEL_AUTOMATION_BYPASS_SECRET`, and keep it out of commits and messages. This is HTTP-layer access to the deployed URL - `VERCEL_TOKEN` auth (`vercel-cli-with-tokens`) authenticates the CLI to the API and does not get requests past protection. For browser review, agent-browser's own `protected-vercel-deployments` skill (`agent-browser skills get protected-vercel-deployments`) is the preferred path: a short-lived OIDC token from `vercel project token` (CLI 53.3+) sent as `x-vercel-trusted-oidc-idp-token`, no long-lived secret in the session. The bypass secret stays for `vercel curl` and CI.

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

