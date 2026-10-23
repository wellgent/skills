# Web products: the approach

How we build web products with agents.
This document is normative for our own products and published as the approach we preach.
It carries the stances - the slow-moving rules.
Exact version pins and per-project registrations are operational state: they live in the consumer's private registry and roll as sweeps, never here.

## Scope

The approach covers web products built *with* agents: the build process is agentic; the products themselves need not be.
Out of scope: non-web tooling and the infrastructure the products run on.

## Judging criterion

Every choice is judged by convenience for agents to build, deploy, overview, and maintain, plus one simple mental model for the operator to drive.
Simplicity over engineering: add nothing for its own sake.
Lean to latest technology versions - newer tends to be more agent-friendly.

Deviations from any rule are allowed with a written justification in the `Deviations` section of the project's `docs/agents/dev-loop.md`: a workflow deviation as its own entry, a stack deviation as a sentence in the same section.

## Frontend

- **Framework**: Next.js, every project.
- **Channel rule**: latest stable by default.
  A pinned exact `preview.N` is allowed only while it carries load-bearing agentic capability, and moves to stable the week stable ships.
  The current target version is an operational pin, kept in the private registry.
- **Agentic baseline** (mandatory, every project):
  - committed `AGENTS.md` managed block maintained by `next dev`
  - bundled `node_modules` Next docs as the agent docs source of truth - no separate Next knowledge skills
  - `next-devtools-mcp` in every repo
  - `agent-browser` >= 0.27 with react-devtools
  - `next-dev-loop` pinned via `skills-lock.json`
  - a real `next build` inside the check command
  - `.next` hygiene: remove a stale `.next` before diagnosing build weirdness; discover the running dev server via its lock file
- **Cache Components**: encouraged, not mandated.
  Greenfield projects default it on; existing projects adopt when the adoption cost is paid deliberately.
- **Currency**: manual, triggered by drift on the observation surface (see Conformance).

## Toolchain

- **TypeScript**: the TS 7 line, one version fleet-wide, installed under the plain `typescript` package name - never the `@typescript/native` alias split (it breaks `convex typecheck`).
  Next 16.3+ runs the project's `tsc` inside `next build` by default (`experimental.useTypeScriptCli`); it is never set `false`, and `next build` inside `check` is where type errors block.
  No dev-build tsgo pins.
  Re-evaluation checkpoint: TS 7.1, when the programmatic compiler API returns.
- **Lint**: oxlint with `@nkzw/oxlint-config`, plus `oxlint-tsgolint` with `typeAware: true`, and the `react`/`nextjs` plugins where applicable.
  ESLint and typescript-eslint are not used.
  Transitive `@typescript-eslint/*` packages (via `@nkzw/oxlint-config`'s stack) declare peers behind TS 7 - a pnpm warning only, lint behavior unaffected; do not chase it.
- **Format**: oxfmt is the only formatter; beta status is accepted deliberately (100% Prettier conformance, built-in import and Tailwind sorting).
  No Prettier and no Prettier residue (`.prettierignore` and friends).
- **Canonical config**: one project's `oxlint.config.ts` and `.oxfmtrc.json` are designated the canonical baseline.
  Projects copy them verbatim, adapting only ignore patterns; every rule override carries a written reason in the config, as the canonical file does.
- **Package manager**: pnpm.
  The `packageManager` field is mandatory in every repo, pinning the exact pnpm version.
  One canonical pnpm supply-chain config applies identically everywhere: `minimumReleaseAge: 1440` in `pnpm-workspace.yaml` - a 24-hour damping window, so a day-old release failing to resolve is the policy working, not an error.
  Node is pinned repo-side (`engines` plus a version file) even on self-hosted machines - the repo, not the host, defines the toolchain.
  The `engines` value and the version file agree on one exact line (`24.x` / `26.x` style); a range (`>=24`) or a disagreement between the two is drift.
- **Runner convention**: our authored surfaces write `pnpm dlx`, never `npx`.
  Third-party content stays verbatim, and following an external doc's `npx ...` line is fine - this is an authoring rule, not an execution ban.
- **Canonical version set**: one exact pin per tool (typescript, oxlint, oxfmt, pnpm, node), declared in the private registry - any project mismatch is drift by definition.
  The node pin bows to the hosting-platform ceiling: a platform-hosted project pins the newest node line its platform's build image supports, and a ceiling pin is conformant, not a deviation.
- **Upgrades** run as sweeps: bump the canonical set in the registry, then roll every project in one pass.
  Never per-project ad hoc - a one-repo upgrade that stops there is the failure mode this rule exists for.

## Hosting and auth

- **Frame**: every product classifies into exactly one audience class - public, team-internal, or personal.
  Classification is the first hosting decision; a class change (a personal tool gains a teammate) triggers a re-host to the new class's standard.
- **Public**: Vercel (app) + Convex (backend); auth is `@convex-dev/auth` with Resend.
  The gating model (marketplace OTP, owner-gate, admin-gate) stays per-product.
- **Team-internal**: self-hosted on the host that homes the product's data, exposed via cloudflared + Cloudflare Access; the app verifies the Access JWT and authorizes on the email claim.
- **Personal**: self-hosted, tailnet-only via `tailscale serve`; the tailnet is the gate, no app-level auth.
- **Placement rule**: internal tools live on the host that homes their data - data gravity is the rule, not an exception.
  A data-uncoupled internal tool has no home under this rule; that case reopens the platform question.
- **Co-location discipline** (mandatory): port block claimed in the operator's port registry with per-host uniqueness; every self-hosted app follows one ops pattern - version-controlled user unit, one-command idempotent ship, commit-equality healthcheck, env-parity smoke proof.
- **No single-platform convergence**: two postures by class - platform-hosted public, data-co-located internal.

## Data layer

Two first-class data layers, applied as a decision rule rather than a default with exceptions:

- If the app's domain data *is* a knowledge base's content, the data layer is that knowledge base's checkout: co-located reads, markdown-first writes.
- Otherwise, if the app needs a database, it is Convex - no per-project debate.

**Skip-criteria** for anything else (supabase pg, sqlite, ...): a sentence in the `Deviations` section of `docs/agents/dev-loop.md` naming the concrete blocker Convex demonstrably cannot serve (execution limit, relational/analytical need, offline/local constraint), judged against the judging criterion.
Preference and familiarity do not qualify.

**Convex canon** (one product is designated the canonical config and directory-layout reference):

- Execution limits are design inputs consulted at planning time: 16,384-doc query cap, batch mutation budget, 4,096-read-call cap, 64-char index names.
- The volume-rehearsal ladder is the proof a data-heavy change carries.
- Components are per-product and namespaced (aggregates, migrations, rate-limiter adopted per need).
- Testing: vitest edge-runtime with inlined `convex-test`.
- Lint: `@convex-dev/eslint-plugin` runs inside `pnpm lint` through oxlint `jsPlugins`, over `convex/` minus tests and fixtures, every rule an error and `require-access-control` on.
  The rule sees raw `query`, `mutation` and `action` registrars only, so ownership inside custom function builders is read by hand against the same shapes and backed by negative tests.
- The catalog's Convex skill set from `get-convex/agent-skills` is installed as ordinary `npx skills` pins (see Skills). The Convex SDK's own file manager stays off (`convex.json`: `{"aiFiles": {"enabled": false}}`): `convex ai-files` installs the whole upstream pack with no subset option, and one of its skills sends session transcripts to Convex.
  With the file manager off nothing refreshes `convex/_generated/ai/guidelines.md`, so every toolchain sweep replaces it with the current upstream `convex_rules.txt`.
- Migrations run through `@convex-dev/migrations`.
  A production migration is dry-run first (`dryRun: true`), and its row counts are part of the production-write approval.
- **A local deployment per worktree.** The worktree setup script creates a local deployment (`convex deployment create local --select`), served by one long-running `convex dev` per worktree, sets `CRONS=off`, pushes and runs the seed, so parallel sessions share no schema or data, use no plan quota or deployment slot, and every runtime check runs against the worktree's own code.
  The teardown stops that `convex dev` and its backend and removes the tree.
  A cloud dev deployment (`--cloud`, expiring, with a `CONVEX_DEPLOY_KEY` scoped to it in `.env.local`) is only for work that needs a public URL.
  The seed lives in the repo as an idempotent function: it creates the test identities `docs/agents/dev-loop.md` names and stores what the crons would.
- **Crons run in production only**: `convex/crons.ts` registers none where the deployment's `CRONS` is `off`, which the shared dev deployment, the project's dev and preview defaults and every worktree set; production leaves it unset.
- **A worktree reaches only its own backend.** The run host's Convex login is used by the operator and by the worktree setup script, and stays readable on the host.
  Once a local worktree's backend runs, its `.env.local` holds the Convex CLI to that backend alone (`CONVEX_SELF_HOSTED_URL`, `CONVEX_SELF_HOSTED_ADMIN_KEY` and a `CONVEX_OVERRIDE_ACCESS_TOKEN` Convex rejects), so `--prod` and the other deployment flags are refused before any network call and the login is never used from the worktree; a cloud worktree's scoped key does the same for its deployment.
  The production build environment holds the production deploy key, the preview build environment the preview deploy key.
- **Previews get their own backend**: a pull request labelled `preview` builds with the preview deploy key into a fresh Convex preview deployment with its own functions and the seed (`--preview-create`, `--preview-run`), recreated on each new head and removed by Convex after 14 days on Professional; `convex deploy` otherwise runs on production builds only, and "codegen touches the deployment" is a standing caution.
- `defineApp` env declaration is required.
- Auth is the hosting standard's territory - see above, not restated here.

**Knowledge-base-checkout apps**: named as a class, not legislated here.
Apps read a co-located checkout and write markdown-first under the owning knowledge base's write model; mechanics (allowlists, sync triggering, derived-state refresh) are governed per knowledge base.

## Checks

- **One check command, everywhere**: `check` = typecheck + lint (oxlint + tsgolint, with the stack's lint plugins) + format check (oxfmt) + design-system lint + unused-code scan (knip) + dependency rules (dependency-cruiser) + full test suite + real production build (`next build`).
  Every step blocks, and tests outside `check` is drift by definition.
  Governing principle: the check runs what production runs.
- **Where it runs: one CI, local, with a sign-off.** `scripts/check` (from [`setup-web-stack/recipes/check.sh`](../setup/setup-web-stack/recipes/check.sh)) refuses a dirty worktree, runs a frozen install, `check` and the journey tests under one of the host's heavy-run slots, and only on a pass pushes the commit and posts a `check` commit status on that exact SHA.
  The implementer runs it on the exact commit before review; the verifier reruns no suite and takes the status as given.
  An agent-run project has no GitHub Actions CI; a GitHub job stays only for contributors outside runs or for work that needs a clean runner, such as publishing ([`setup-web-stack/check.yml`](../setup/setup-web-stack/check.yml) is that job's template).
- **Every test run holds a heavy-run slot**: the test scripts, `check` and every browser suite run through `scripts/slot` (from [`templates/project/scripts/slot`](../templates/project/scripts/slot)), capped per host by `HEAVY_RUN_SLOTS`; the slots alone bound memory, each run at the test runner's default worker count; tests run only through the package scripts.
- **Dependency rules**: no cycles, plus one rule per module boundary the project sets; each rule's message carries the fix.
- **Journey tests**: each project names at most five client-approved critical journeys, one plain Playwright test each.
  `scripts/check` runs them against the worktree's own backend.
  They are the only browser-level suite; the tests inside `check` are the regression net.
- **Code quality judgment is pstack's**: its review (interrogate, thermos, no-comments, deslop) and its principle skills judge a diff, and `/correct` turns a repeated mistake into a lint rule, a type or a test.
  A project rule a lint can enforce is a lint rule.
- **Changing a check**: tightening is free.
  Loosening a shared check (an ignore entry, a disabled rule, a step removed from `check`) is named in the pull request, and an inline suppression carries its reason on the same line.
- **A blocking check that is red on `main` joins `check` once it is green**: until then it sits in the "Pending checks" section of `docs/agents/dev-loop.md` with what gets it green, and a run gets it green.
  No baseline or exemption files.
- **No residue, tool-enforced**: knip fails unused files, exports, types and dependencies; dependency-cruiser fails a boundary breach; every ignore entry carries a written reason.
- **Coverage: no metric, no minimum counts.**
  Tests exist and run inside `check`; the volume-rehearsal ladder governs data-heavy changes.
  Test allocation stays per-product and risk-driven.
- **Prod-parity proofs, per hosting class**:
  - Platform-hosted: `next build` inside `check` pre-ship, a mandatory deploy-status check post-ship.
  - Self-hosted: a `systemd-run --user` env-parity smoke proof pre-ship, the commit-equality healthcheck post-ship.
- **Build-environment pins are deploy-shaped and locally unprovable**: a diff touching `engines`, `packageManager`, a node version file, or platform build settings carries a pre-ship check that the pinned values are supported by the hosting platform's build image (for Vercel, the supported-runtimes doc).
  A preview deploy does not prove it.
- **A ship is complete when the production surface is verified serving the shipped commit** - not when the push succeeds.

## Design

- **impeccable is the design scanner**, pinned at 4.5.0 or later (engine 0.1.11 or later, the first that honours detector ignores in linked git worktrees).
  It runs through one command, the pinned `.agents/skills/impeccable/scripts/impeccable detect`, named on the "Design scanner" line of `docs/agents/dev-loop.md`, so every session runs the same engine.
- **Environment**: `DO_NOT_TRACK=1` is set on every run host, and `OPENAI_API_KEY` stays unset, which keeps impeccable on its code-led path.
- **Design-system lint** blocks inside `check`: arbitrary radius, font-size, colour, spacing and size values fail; the theme resets the framework's default palette so only design tokens exist; raw controls in app code fail through oxlint `react/forbid-elements`, so screens compose kit components.
- **Client choices are made on coded prototypes**: two or three options on a `prototype/<slug>` branch, switched by a variant switcher that lives on `main` and is hidden in production by a `VERCEL_ENV` gate.
  Only the variant code lives on the branch, and the prototype runs on seeded synthetic identities, never production records.
- **Where previews run**:
  - Vercel-hosted projects: Vercel builds `main` only; a pull request, prototypes included, gets its preview from `scripts/preview`, which labels it `preview` and deploys its head with the Vercel CLI onto its own Convex preview deployment.
    A run labels an interaction-changing pull request this way for the owner's review.
  - Self-hosted projects: a scratch dev deployment with an expiry, and a dev server on a tailnet port.

## Version control

- **Linear history on `main`**: every commit on the default branch is one pull request, squash-merged.
  A merge commit carries no content, so the default branch never gets one.
- **Work lands through pull requests**: a run works on a branch in its own worktree, opens a pull request, and lands it under the landing authority its prompt grants once its independent verifier passes.
- **One gate**: `scripts/land <pr>` (from [`templates/project/scripts/land`](../templates/project/scripts/land)) merges only on a passing `check` status on the exact head, `gh pr merge --squash --match-head-commit`, and reads the merge back.
  A pull request need not be up to date with `main`; it restacks only on a real conflict, and there is no CI run on `main`, so the production deploy is the only build `main` gets.
  Where the plan allows required status checks, the repository ruleset requires `check` too, with no up-to-date requirement; no plan is upgraded for it.
  When `scripts/check` cannot run, landing pauses and the run notifies the owner; building and verifying go on.
  Never a merge-commit button, never a `git pull` that merges.
- **Repo settings**: squash and rebase merging on, merge commits off, head branches deleted on merge.

## Skills

A project pins only stack skills: the entries of [`setup-web-stack/catalog.md`](../setup/setup-web-stack/catalog.md) its stack setup names, nothing from `mattpocock/skills` and nothing from this repo.
A brain pins `operate` and the planning skills [`setup-brain`](../setup/setup-brain/SKILL.md) names; pstack's own skills come from the plugin.
The catalog keeps rationale (what each skill is for and where it is named), never membership.

- **A skill runs only when it is named**: by a must-read line in the project's `AGENTS.md`, a line in `docs/agents/dev-loop.md`, or a project playbook.
  Nothing relies on a skill's description firing.
- **Skills only a person invokes** live in the driving brain or at user scope.
- **Situational skills** are catalog-documented, each with the condition that pins it and the line that then names it.
  The operator pins one when its condition is met.
- **Distribution**: `npx skills` pins by commit sha (`npx skills add <source>#<sha>`), recorded as `ref` in `skills-lock.json`, converged by explicit `add` / `remove` per delta, never `skills update`.
  `<source>@<name>` selects a skill by name and pins nothing.
  Cadence: manual, drift-triggered - no cron.

**Where agent-facing content lives** - two axes decide it, ownership and form.
Ownership: vendor-owned content arrives by pin or managed copy and is replaced wholesale on update, so nothing project-owned may live inside a pinned directory; project-owned content is scaffolded once and then belongs to the repo.
Form: a skill is a procedure an agent invokes, and the harness fixes its home under `.agents/skills/`; a doc is what an agent consults, and `docs/agents/` is the project's home for agent-facing docs, with `AGENTS.md` as the entry.
Project rules an agent consults are in the docs set of [project-docs.md](project-docs.md); procedures an agent runs are skills; anything vendor-owned is a pin or a marked managed file wherever it sits.

**Custom skill homing** - three homes:

- **Project-local**: skills whose content is the project's specifics.
  The one every project carries is its verification skill, `verify` or `verify-<app>`, written by pstack's `create-verification-skill` from the "Running the app" section of `docs/agents/dev-loop.md`, which stays the home of how to launch, sign in to and drive the app.
- **This repo** (public): everything we use regularly and can express internals-free - it must work unmodified from a stranger's checkout.
  The setup skills run from a checkout on the host; `operate` is pinned into brains.
- **Private fleet machinery** (sweeps, registries, machine alignment): stays in the operator's private repos, never pinned into product repos.

## Methodology

- **The process is pstack's**: planning, build, review, verification, pull requests, shipping and retro run inside the project through the plugin, started from the brain by `/operate`.
  pstack names no stack; this document carries every stack rule.
- **A project's own surface**, scaffolded from [`templates/project/`](../templates/project/) and then project-owned: the docs set in [project-docs.md](project-docs.md), and `.agents/playbooks/`, optional, with project playbooks that extend pstack's bundled ones with After, Before and In lines, never Replace.

  Promotion litmus: any line that should read identically in every project belongs to the template, and project files hold what is true of this repo.
- **What this stack puts in those files** (Next.js with Convex; a project without one of them drops its lines):
  - Must-read list: `convex/_generated/ai/guidelines.md` and the `convex-authz` checklist when touching Convex code; `convex-reviewer` before a Convex diff goes into a pull request; `convex-migrate` when a change touches the schema of a populated table; `web-design-guidelines` when a change touches a screen; `vercel-react-best-practices` when a change renders or fetches data in React; `find-docs` for a library API.
  - `docs/agents/dev-loop.md`: `agent-browser` and `next-dev-loop` under "Running the app", with the check "`get_errors` returns nothing for the routes exercised"; the design-system lint and the impeccable scanner under "Design system"; `convex/_generated/` under "Not docs".
- **Tracker labels**: one taxonomy across projects - `needs-triage`, `needs-info`, `ready-for-agent`, `needs-human` and `wontfix` on every project tracker, `run` on the brain's.
  Per-project freedom is topical labels only.

## Learning propagation

- **Route at the moment of observation**: a lesson about a shared asset files on that asset's home tracker when it is made (skill and approach lessons on this repo's tracker, machine lessons on the operator's fleet repo).
  Project trackers keep only project-local observations.
  Inside a project, retro is pstack's: `/reflect` at the end of a run, `/correct` for a repeated mistake.
  From a machine whose identity cannot write the destination tracker, the lesson files on the project tracker with an `[upstream:<home>]` title marker - the operator's cross-project board sweep picks those up; the marker makes local pooling protocol, not a miss.
- **Boards get periodic cross-project triage**: the operator sweeps every project's board as one set at their own cadence - closing what reality has already resolved, triaging the `needs-triage` pool per the label taxonomy, reframing issues whose right solution changed, deduplicating within and across projects (the best-framed issue survives and absorbs the rest), and refiling shared-asset issues, including `[upstream:<home>]`-marked ones, on their home trackers.
  The sweep is what keeps every board accurate between sessions without per-project ceremony.
- **Lessons land as changes, not memos**: destination repos turn filed lessons into skill updates, doctrine edits, or catalog entries, propagated by the ordinary sweep.
  Observe, file upstream, fix at source, sweep out.
- **The change queue**: this repo's tracker is the change queue for the skills and this doctrine.
  A refresh pass is an ordinary session working that queue: groom accumulated lesson issues, edit this document / the skills / the catalog, close them.
  Two triggers, both manual, both observable: the drift signal on the observation surface and a visibly non-empty lesson queue.

## New projects

The golden path is this repo's [`setup-web-product`](../setup/setup-web-product/SKILL.md) skill: it takes the few real inputs, then drives the whole bootstrap end to end, deferring each stage to its existing installer.

**Input surface - four decisions, everything else defaulted**:

1. Name + repo home (GitHub org).
2. Audience class (public / team-internal / personal); if internal, one sub-input: the co-location host.
3. Data need (knowledge-base content / needs-a-database / none); a database means Convex and the catalog's Convex branch.
4. Machine for self-hosted (usually implied by co-location).

Defaults applied without asking: Next latest stable per the channel rule, Tailwind v4 on, the full toolchain standard, the check composition, the catalog entries the stack setup picks, port block auto-allocated as the next free block on the target machine, the tracker labels seeded.
Cache Components defaults on for greenfield.

**Composition order**: scaffold (setup-web-stack), claim (registry entries up front, no placeholders downstream), brain (setup-brain: the `operate` skill, the `run` label and request template, the operating section in the brain's `AGENTS.md`), project (setup-project: the pstack plugin at project scope, the stack pins, the sign-off and landing scripts, `AGENTS.md`, `docs/agents/dev-loop.md` and `PRODUCT.md` from the templates, the verification skill; through setup-web-stack the journey tests, the worktree setup and teardown, the dev server and the seed), hosting (per audience class), first ship (check command green, prod-parity proof, registration finalized).

**Two-phase registration**: claim at step 2 (ports, membership), finalize at first ship (public URL, live fields); observation tolerates claimed-but-not-yet-live in between.

**Done means**: the observation surface shows the project green across every conformance column after first ship - skill delta zero, project docs asserted, ports registered, prod serving.
Bootstrap is not "repo created"; it is "conformant and live".

## Conformance

Observation observes; this document prescribes.
The consumer's observation surface asserts per project: framework version and agentic-baseline drift, toolchain canonical-set drift against the registry's pins, skill delta (missing / unrecorded extras / hash drift), `AGENTS.md` and `docs/agents/dev-loop.md` present with headings matching the templates, ports agreeing with the registry.
Zero delta across the columns is conformant; any non-zero delta is the standing manual trigger for a sweep or refresh pass.
No calendar cadence anywhere.
