# Web products: the approach

How we build web products with agents.
This document is normative for our own products and published as the approach we preach.
It carries the stances - the slow-moving rules.
Exact version pins, skill membership, and per-project registrations are operational state: they live in the consumer's private registry and roll as sweeps, never here.

## Scope

The approach covers web products built *with* agents: the build process is agentic; the products themselves need not be.
Out of scope: non-web tooling and the infrastructure the products run on.

## Judging criterion

Every choice is judged by convenience for agents to build, deploy, overview, and maintain, plus one simple mental model for the operator to drive.
Simplicity over engineering: add nothing for its own sake.
Lean to latest technology versions - newer tends to be more agent-friendly.

Deviations from any rule are allowed with a written justification, recorded where the deviation lives: the `Deviations` section of the project's `docs/agents/dev-loop.md` for workflow rules, an ADR in the project repo for stack rules.

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
  Next 16.3+ runs the project's `tsc` inside `next build` by default (`experimental.useTypeScriptCli`); it is never set `false`, and `next build` remains the enforcement gate.
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

**Skip-criteria** for anything else (supabase pg, sqlite, ...): an ADR in the project repo naming the concrete blocker Convex demonstrably cannot serve (execution limit, relational/analytical need, offline/local constraint), judged against the judging criterion.
Preference and familiarity do not qualify.

**Convex canon** (one product is designated the canonical config and directory-layout reference):

- Execution limits are design inputs consulted at spec time: 16,384-doc query cap, batch mutation budget, 4,096-read-call cap, 64-char index names.
- The volume-rehearsal ladder is a first-class gate proof for data-heavy specs.
- Components are per-product and namespaced (aggregates, migrations, rate-limiter adopted per need).
- Testing: vitest edge-runtime with inlined `convex-test`.
- Lint: `@convex-dev/eslint-plugin` runs inside `pnpm lint` through oxlint `jsPlugins`, over `convex/` minus tests and fixtures, every rule an error and `require-access-control` on.
  The rule sees raw `query`, `mutation` and `action` registrars only, so ownership inside custom function builders stays a Review judgment backed by negative tests.
- The catalog's Convex skill set from `get-convex/agent-skills` is installed as ordinary `npx skills` pins (see Skills). The Convex SDK's own file manager stays off (`convex.json`: `{"aiFiles": {"enabled": false}}`): `convex ai-files` installs the whole upstream pack with no subset option, and one of its skills sends session transcripts to Convex.
  With the file manager off nothing refreshes `convex/_generated/ai/guidelines.md`, so every toolchain sweep replaces it with the current upstream `convex_rules.txt`.
- Migrations run through `@convex-dev/migrations`.
  A production migration is dry-run first (`dryRun: true`), and its row counts are part of the production-write approval.
- **Scoped keys guard production.** The run host's Convex login is used by the lead session and by the worktree setup script.
  Every worktree's `.env.local` carries a `CONVEX_DEPLOY_KEY` scoped to that worktree's own dev deployment (`convex deployment token create`), so every `convex` command a spawned session runs there reaches that deployment and no other.
  The login stays readable on the host: the key stops a stray production command, and the `AGENTS.md` rule that a production read or write is a request to the lead covers the rest.
  Build pipelines hold keys scoped the same way: the production deploy key in the production build environment, the preview deploy key in the preview one.
- **One dev deployment per worktree.** The worktree setup script creates an expiring cloud dev deployment (`convex deployment create dev/<worktree> --type dev --select --expiration`), mints its scoped key, pushes once (`convex dev --once`) and runs the seed, so parallel sessions share no schema or data and every runtime check runs against the worktree's own code.
  The seed lives in the repo as an idempotent function and creates the test identities `docs/agents/dev-loop.md` names.
- `convex deploy` runs on production builds and on `prototype/*` preview builds only (see Design); "codegen touches the deployment" is a standing caution.
- `defineApp` env declaration is required.
- Auth is the hosting standard's territory - see above, not restated here.

**Knowledge-base-checkout apps**: named as a class, not legislated here.
Apps read a co-located checkout and write markdown-first under the owning knowledge base's write model; mechanics (allowlists, sync triggering, derived-state refresh) are governed per knowledge base.

## Quality gate

- **One check command, everywhere**: `check` = typecheck + lint (oxlint + tsgolint, with the stack's lint plugins) + format check (oxfmt) + design-system lint + unused-code scan (knip) + dependency rules (dependency-cruiser) + full test suite + real production build (`next build`).
  Every step blocks, and tests outside `check` is drift by definition.
  Governing principle: the gate runs what production runs.
- **A check blocks or is measured, never advisory**: it either sits in the check command, or it runs in the Audit scanner pass and lands as a number in the ledger.
  Judgment belongs to Review and Audit sessions.
- **Dependency rules**: no cycles, plus one rule per ADR that sets a module boundary; each rule's message carries the fix.
- **Journey tests**: each project names at most five client-approved critical journeys, one plain Playwright test each, run once per spec by `flow gate` beside the check command.
  Seam tests written test-first in Build are the regression net; the journey tests are the only browser-level suite.
- **Measured in the scanner pass**: unused-code findings, duplication of source and of tests (jscpd), dependency-rule violations, the react-doctor finding count, inline suppressions, test count and wall time, source and test lines.
  No thresholds on duplication or complexity, and no mutation score.
- **Changing a check**: tightening is free.
  Loosening a shared check (an ignore entry, a disabled rule, a step removed from `check`, a lowered threshold) needs the ticket to name it or the lead's approval, and an inline suppression carries its reason on the same line.
  `flow gate` flags every such change on the spec diff for the lead to judge.
- **A blocking check that is red on `main` joins `check` once it is green**: until then it runs in the scanner pass, the readiness report lists it as pending, and a cleanup spec gets it green.
  No baseline or exemption files.
- **CI: nowhere.**
  `flow gate` on the spec's branch and `flow land`, which fast-forwards `main` only to a commit the gate passed, are the single enforcement point.
  CI would duplicate it in a divergent environment with a demonstrated rot pattern.
  The fact that reopens this decision: unattended or scheduled pushes that bypass the gate becoming real.
- **No residue**: code and docs describe what is; a replacement deletes what it replaces in the same diff; no unused files, exports, types, or dependencies (every dead-code suppression carries a written reason); every `TODO` carries an issue number; tests follow their code; vendor-owned trees are re-pinned, never edited.
  Each project's `CODING_STANDARDS.md` carries these rules and the seven-point test bar that Review judges a diff against.
- **Coverage: no metric, no minimum counts.**
  Tests must exist and run inside `check`; the behavioural contracts of a spec name the examples its tests must carry; the volume-rehearsal ladder governs data-heavy specs.
  Test allocation stays per-product and risk-driven.
- **Prod-parity proofs, per hosting class**:
  - Platform-hosted: the gate's `next build` pre-ship, a mandatory deploy-status check post-ship.
  - Self-hosted: a `systemd-run --user` env-parity smoke proof pre-ship, the commit-equality healthcheck post-ship.
- **Build-environment pins are deploy-shaped and locally unprovable**: a diff touching `engines`, `packageManager`, a node version file, or platform build settings carries a pre-ship check that the pinned values are supported by the hosting platform's build image (for Vercel, the supported-runtimes doc).
  A preview deploy is not a gate proof.
- **A ship is complete when the production surface is verified serving the shipped commit** - not when the push succeeds.

## Design

- **impeccable is the design tool of the UX design stage**, pinned at 4.5.0 or later (engine 0.1.11 or later, the first that honours detector ignores in linked git worktrees).
  Its scanner runs through one command, the pinned `.agents/skills/impeccable/scripts/impeccable detect`, so every stage runs the same engine.
- **Environment**: `DO_NOT_TRACK=1` is set on every run host, and `OPENAI_API_KEY` stays unset, which keeps impeccable on its code-led path.
- **Design-system lint** blocks inside `check`: arbitrary radius, font-size, colour, spacing and size values fail; the theme resets the framework's default palette so only design tokens exist; raw controls in app code fail through oxlint `react/forbid-elements`, so screens compose kit components.
- **Client choices are made on coded prototypes**: two or three options on a `prototype/<spec>-<slug>` branch, switched by a variant switcher that lives on `main` and is hidden in production by a `VERCEL_ENV` gate.
  An idempotent seed and unseed for the reviewer's records also lives on `main`; only the variant code lives on the branch.
- **Where prototypes run**:
  - Vercel-hosted Convex projects: one Convex preview deployment per `prototype/*` branch.
    The build script runs `convex deploy` with the preview deploy key only for those branches and seeds through `--preview-run`; sign-in env comes from the Convex project's default environment variables for previews.
    Every other preview build points at the project's default dev deployment.
  - Self-hosted projects: a scratch dev deployment with an expiry, and a dev server on a tailnet port.
- **Production records in a prototype**: the client approves, once per project, an allowlist of tables keyed to the reviewer's own user that reference no other user.
  One scripted read, run by the lead, copies those records from production into the prototype's preview deployment and nowhere else; credentials and tokens are never on the allowlist.
  Surfaces that involve other users run on seeded synthetic identities.

## Version control

- **Linear history on `main`**: every commit on the default branch is one development step by its author.
  A merge commit carries no content, so the default branch never gets one.
- **Branch freely, land linearly**: work is committed on `main` directly or on a branch or worktree.
  A branch lands by rebasing onto the remote default branch, fast-forwarding (`git merge --ff-only`), and pushing.
  Never `--no-ff`, never a merge-commit button, never a `git pull` that merges.
  `flow land` is this rule applied.
- **No pull requests by default**: review runs in the flow and the gate is local, so a PR adds nothing.
  One is opened only when the operator asks, and it lands the same way - the fast-forward push marks it merged.
- **Squash is not the default**: it collapses the commit chain; it is used only when the operator asks.
- **Repo settings**: merge commits off, rebase merging on, squash left available, head branches deleted on merge.

## Skills

Membership splits along the stance/operations fault line: the curated Matt's selection is declared by this repo's [`setup-matts-skills`](../setup/setup-matts-skills/SKILL.md) skill (the stance); capability packs, per-project assignment, and retired-skill lists live in the consumer's private registry (the operations).
[`setup-web-stack/catalog.md`](../setup/setup-web-stack/catalog.md) keeps rationale (what each skill is for and which step names it), never membership.

- **A skill runs only when it is named**: by a step's stage skill, or by path and trigger in the project's `AGENTS.md` must-read list or `docs/agents/dev-loop.md`.
  Nothing relies on a skill's description firing.
- **A project pins only the skills a step names.**
  The flow's own skills, scripts and templates are read in place from the flow checkout on the run host and are never pinned into a project.
  Skills only a person invokes live in the driving brain or at user scope.
- **Three tiers**: a base set every project carries, capability add-on packs keyed to repo facts, and per-project assignment (packs plus recorded extras).
- **Pack triggers are repo facts, not preferences**: convex pack when the project has a `convex/` directory; vercel-hosted pack when it deploys through Vercel; cache-components-adoption pack only while `cacheComponents` is being adopted, removed once adoption is done.
- **Situational skills** are catalog-documented, each with the condition that pins it and the step that then names it.
  The lead pins one when its condition is met and records it in the registry as a per-project extra.
- **Retired skills** are named in the private registry; sweeps remove them wherever found.
- **Distribution**: `npx skills` pins by commit sha (`npx skills add <source>@<sha>`), recorded in `skills-lock.json`, converged by explicit `add` / `remove` per delta, never `skills update`.
  Cadence: manual, drift-triggered - no cron.

**Where agent-facing content lives** - two axes decide it, ownership and form.
Ownership: vendor-owned content arrives by pin or managed copy and is replaced wholesale on update, so nothing project-owned may live inside a pinned directory; project-owned content is scaffolded once and then belongs to the repo.
Form: a skill is a procedure an agent invokes, and the harness fixes its home under `.agents/skills/`; a doc is what an agent consults, and `docs/agents/` is the project's home for agent-facing docs, with `AGENTS.md` as the entry.
Project rules an agent consults are in `AGENTS.md`, `CODING_STANDARDS.md` and `docs/agents/`; procedures an agent runs are skills; anything vendor-owned is a pin or a marked managed file wherever it sits.

**Custom skill homing** - three homes:

- **Project-local**: skills whose content is the project's specifics.
  No project-local skill is mandated, and no project carries a skill named `verify`: the harness tells every committing session to run a project skill of that name, which would put a browser walk into every implementer.
  How to launch, sign in to and drive the app is the "Running the app" section of `docs/agents/dev-loop.md`.
- **This repo** (public): everything we use regularly and can express internals-free - it must work unmodified from a stranger's checkout.
  Read in place from one checkout per run host.
- **Private fleet machinery** (sweeps, registries, machine alignment): stays in the operator's private repos, never pinned into product repos.

## Methodology

- **Two-layer model**: the flow lives in this repo ([`FLOW.md`](../FLOW.md), the lead skill, the stage skills, the `flow` command) and is read in place, never copied into projects.
  The flow names no stack and no project; this document carries every stack rule.
- **A project's methodology surface is three files**, scaffolded from [`templates/project/`](../templates/project/) and then project-owned:
  - `AGENTS.md`, loaded by every session: the check-before-report rule, the conflict exit, the test tiers, the check-change rule and the must-read list.
  - `docs/agents/dev-loop.md`, read by path by the stages that need it: the gate lines, critical journeys, worktrees, running the app, Review lenses, QA tools, Audit lenses, the scanner pass, the design-system commands, deviations.
  - `CODING_STANDARDS.md`, read by `code-review`, Review and Audit: code rules and the test bar.

  Promotion litmus: any line that should read identically in every project belongs to the template or the flow, and project files hold what is true of this repo.
- **What this stack puts in those files** (Next.js with Convex; a project without one of them drops its lines):
  - Must-read list: `convex/_generated/ai/guidelines.md` and the `convex-authz` checklist when touching Convex code; `convex-migrate` when a ticket changes the schema of a populated table; `find-docs` for a library API; `diagnosing-bugs` on a bug ticket.
    Implementers get stack rules through this list and no judgment lenses.
  - Review lenses: `web-design-guidelines` on UI diffs; `convex-reviewer` on Convex diffs.
  - QA tools: `agent-browser` and `next-dev-loop`, with the named check "`get_errors` returns nothing for the routes exercised".
  - Audit lenses: `vercel-composition-patterns` in the architecture review; `vercel-react-best-practices` in the defect review.
  - Scanner pass: knip, jscpd over source and over tests, dependency-cruiser, a suppression count, the test run's count and wall time, line counts, and the react-doctor finding count as the project measure `react_doctor`.
- **Tracker conventions**: one label taxonomy across projects, identity-mapped - the five triage roles (`needs-triage`, `needs-info`, `ready-for-agent`, `needs-human`, `wontfix`), the `wayfinder:*` set, and the lead's `lead:iteration` and `lead:input`.
  Per-project freedom is topical labels only.
  `docs/agents/issue-tracker.md` and `triage-labels.md` stay per project but are template-owned generated surfaces, always generic `<owner>/<repo>`; a project's file diverges only to declare an actual deviation.
  Every bug ticket carries its origin spec, the spec whose change introduced the bug; the bug issue template has the field.
- **One lane system**: the flow is the standard lane for an iteration toward a destination, run by the lead for a client; a single bug ticket takes the flow's single-bug path; work between iterations runs without the flow, through `implement` on a ticket.
  Lane choice is judgment, not deviation.
- **Where review runs**: `code-review` inside Build; Review on each spec's gated diff by the other model family, with the project's lenses; one exploratory QA pass per spec with a user-facing change; a two-family Audit of the whole codebase at the client's close.
  Scanners feed the Audit as ledger numbers; a Review or QA finding blocks only as a correctness defect, a spec gap, a breach of a written standard, or a defect with a failing repro test.

## Learning propagation

- **Route at the moment of observation**: a lesson about a shared asset files on that asset's home tracker when it is made (skill and approach lessons on this repo's tracker, machine lessons on the operator's fleet repo).
  Project trackers keep only project-local observations.
  Retro routes the lessons of an iteration the same way.
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
3. Data need (knowledge-base content / needs-a-database / none); a database flips the convex pack trigger.
4. Machine for self-hosted (usually implied by co-location).

Defaults applied without asking: Next latest stable per the channel rule, Tailwind v4 on, the full toolchain standard, the gate composition, base skill set plus triggered packs, port block auto-allocated as the next free block on the target machine, canonical label taxonomy seeded.
Cache Components defaults on for greenfield.

**Composition order**: scaffold (setup-web-stack), claim (registry entries up front, no placeholders downstream), skills (install the membership verdict), workflow (setup-matts-skills), project docs (`AGENTS.md`, `docs/agents/dev-loop.md` and `CODING_STANDARDS.md` from the templates, the journey tests, the worktree setup script and the seed), hosting (per audience class), first ship (gate green, prod-parity proof, registration finalized).

**Two-phase registration**: claim at step 2 (ports, membership), finalize at first ship (public URL, live fields); observation tolerates claimed-but-not-yet-live in between.

**Done means**: the observation surface shows the project green across every conformance column after first ship - skill delta zero, project docs asserted, ports registered, prod serving.
Bootstrap is not "repo created"; it is "conformant and live".

## Conformance

Observation observes; this document prescribes.
The consumer's observation surface asserts per project: framework version and agentic-baseline drift, toolchain canonical-set drift against the registry's pins, skill delta (missing / retired-but-present / unrecorded extras / hash drift), the three project docs present with headings matching the templates, ports agreeing with the registry.
Zero delta across the columns is conformant; any non-zero delta is the standing manual trigger for a sweep or refresh pass.
No calendar cadence anywhere.
