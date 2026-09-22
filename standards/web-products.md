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

Deviations from any rule are allowed with a written justification, recorded where the deviation lives: the project's dev-loop contract `Deviations` section for workflow rules, an ADR in the project repo for stack rules.

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
  - a real `next build` inside the quality gate
  - `.next` hygiene: remove a stale `.next` before diagnosing build weirdness; discover the running dev server via its lock file
- **Cache Components**: encouraged, not mandated.
  Greenfield projects default it on; existing projects adopt when the adoption cost is paid deliberately.
- **Currency**: manual, triggered by drift on the observation surface (see Conformance).

## Toolchain

- **TypeScript**: the TS 7 line, one version fleet-wide, installed under the plain `typescript` package name - never the `@typescript/native` alias split (it breaks `convex typecheck`).
  Next apps set `experimental.useTypeScriptCli: true` until Next makes TS 7 first-class; `next build` remains the enforcement gate.
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
- The catalog's Convex skill set from `get-convex/agent-skills` is mandatory for every Convex app, installed as ordinary `npx skills` pins (see Skills). The Convex SDK's own file manager stays off (`convex.json`: `{"aiFiles": {"enabled": false}}`): `convex ai-files` installs the whole upstream pack with no subset option, and one of its skills sends session transcripts to Convex.
- `convex deploy` runs on production builds only; "codegen touches the deployment" is a standing caution.
- `defineApp` env declaration is required.
- Auth is the hosting standard's territory - see above, not restated here.

**Knowledge-base-checkout apps**: named as a class, not legislated here.
Apps read a co-located checkout and write markdown-first under the owning knowledge base's write model; mechanics (allowlists, sync triggering, derived-state refresh) are governed per knowledge base.

## Quality gate

- **One gate composition, everywhere**: `check` = lint (oxlint + tsgolint) + format check (oxfmt) + typecheck + full test suite + real production build (`next build`).
  Nothing pushes without all five green; tests outside `check` is drift by definition.
  Governing principle: the gate runs what production runs.
- **CI: nowhere.**
  The dev loop's driver-owned gate (diff review, re-run proofs, push only on green) is the single enforcement point.
  CI would duplicate it in a divergent environment with a demonstrated rot pattern.
  The fact that reopens this decision: unattended or scheduled pushes that bypass the gated loop becoming real.
- **Coverage: no metric, no minimum counts.**
  Tests must exist and run inside `check`; per-spec gate proofs name the evidence a change must produce; the volume-rehearsal ladder governs data-heavy specs.
  Test allocation stays per-product and risk-driven.
- **Prod-parity proofs, per hosting class**:
  - Platform-hosted: the gate's `next build` pre-ship, a mandatory deploy-status check post-ship.
  - Self-hosted: a `systemd-run --user` env-parity smoke proof pre-ship, the commit-equality healthcheck post-ship.
- **Build-environment pins are deploy-shaped and locally unprovable**: a diff touching `engines`, `packageManager`, a node version file, or platform build settings carries a pre-ship check that the pinned values are supported by the hosting platform's build image (for Vercel, the supported-runtimes doc).
  A preview deploy is not a gate proof - unproven work never reaches the remote.
- **A ship is complete when the production surface is verified serving the shipped commit** - not when the push succeeds.

## Skills

Membership splits along the stance/operations fault line: the curated Matt's selection is declared by this repo's [`setup-matts-skills`](../setup/setup-matts-skills/SKILL.md) skill (the stance); capability packs, per-project assignment, and retired-skill lists live in the consumer's private registry (the operations).
[`setup-web-stack/catalog.md`](../setup/setup-web-stack/catalog.md) keeps rationale (what each skill is for), never membership.

- **Three tiers**: a base set every project carries, capability add-on packs keyed to repo facts, and per-project assignment (packs plus recorded extras).
- **Pack triggers are repo facts, not preferences**: convex pack when the project has a `convex/` directory; vercel-hosted pack when it deploys through Vercel; cache-components pack when `cacheComponents` is enabled or actively being adopted.
- **Retired skills** are named in the private registry; sweeps remove them wherever found.
- **Distribution**: `npx skills` lock-pins on disk (`skills-lock.json`), converged by explicit `add -s` / `remove` per delta, never `skills update`.
  Cadence: manual, drift-triggered - no cron.
- **Situational skills** (e.g. `react-view-transitions`) stay catalog-documented; a project adopting one records it in the registry as a per-project extra.

**Custom skill homing** - three homes:

- **Project-local** (default): skills whose content is the project's specifics.
  `verify` is the one mandated project-local skill - every project carries `.agents/skills/verify/SKILL.md` plus `scripts/dev-server.sh`.
  It is two-layer: the shared mechanics (dev-server discipline, browser preflight, review loop, universal gotchas) are read in place from the installed `verify-protocol` skill (wellgent/skills, an ordinary pin beside `orchestrate`); the local skill holds only repo declarations (Ports, Launch, Sign-in, Driving gotchas, Environment gotchas, Checks that work well), scaffolded from that skill's `verify-reference.md`, and earned gotchas append to the local layer.
  Launch-the-app content lives in `verify` - launch is its first chapter, never a companion `run` skill.
  Observation asserts presence only (skill and script exist); section-level conformance is a convergence-time human check.
- **This repo** (public): everything we use regularly and can express internals-free - it must work unmodified in a stranger's repo.
  Distributed as an ordinary npx pin.
- **Private fleet machinery** (sweeps, registries, machine alignment): stays in the operator's private repos, never pinned into product repos.

## Methodology

- **Two-layer model**: the dev-loop protocol lives with the `orchestrate` skill in this repo and is read in place, never copied into projects.
  Each project's entire methodology surface is one declarations file, `docs/agents/dev-loop.md`: Ports, Runtime, Gate proofs, Deviations.
  Promotion litmus: any line that should read identically in every project is protocol material and gets promoted out of the declarations - declarations hold only facts unique to the repo.
- **Contract schema**: owned solely by orchestrate's `dev-loop-declarations.md`.
  This standard mandates the contract's existence and points there - no second copy.
  Scaffolding defers to an existing contract; promotions out of declarations are explicit convergence work, never silent sweep rewrites.
- **Tracker conventions**: one label taxonomy across projects, identity-mapped - the five triage roles (`needs-triage`, `needs-info`, `ready-for-agent`, `needs-human`, `wontfix`), the dev-loop lifecycle labels (`spec`, `in-progress`, `fix-main`), the `wayfinder:*` set.
  Per-project freedom is topical labels only.
  `docs/agents/issue-tracker.md` and `triage-labels.md` stay per project but are template-owned generated surfaces, always generic `<owner>/<repo>`; a project's file diverges only to declare an actual deviation.
- **One lane system**: wayfinder charts large scopes, grilling handles ad-hoc decisions, to-spec/to-tickets groom, **orchestrate is the standard execution lane for spec-scale delivery**, implement serves one-offs that don't warrant the loop, off-loop work runs on the declared port.
  Lane choice is judgment, not deviation - the Deviations section governs protocol overrides inside the loop only.
  Session shapes are protocol: single-flight, fixed driver/implementer roles, spec-at-a-time with continuation as the headroom exception.

## Learning propagation

- **Route at the moment of observation**: a lesson about a shared asset files on that asset's home tracker when it is made (skill and approach lessons on this repo's tracker, machine lessons on the operator's fleet repo).
  Project trackers keep only project-local observations.
  The routing rule is carried in orchestrate's dev-loop protocol, read in place by every loop session.
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

**Composition order**: scaffold (setup-web-stack), claim (registry entries up front, no placeholders downstream), skills (install the membership verdict), workflow (setup-matts-skills), contract (dev-loop declarations + verify skill), hosting (per audience class), first ship (gate green, prod-parity proof, registration finalized).

**Two-phase registration**: claim at step 2 (ports, membership), finalize at first ship (public URL, live fields); observation tolerates claimed-but-not-yet-live in between.

**Done means**: the observation surface shows the project green across every conformance column after first ship - skill delta zero, contract asserted, ports registered, prod serving.
Bootstrap is not "repo created"; it is "conformant and live".

## Conformance

Observation observes; this document prescribes.
The consumer's observation surface asserts per project: framework version and agentic-baseline drift, toolchain canonical-set drift against the registry's pins, skill delta (missing / retired-but-present / unrecorded extras / hash drift), contract-exists with headings matching the skeleton, ports agreeing with the registry, driver pin at source HEAD.
Zero delta across the columns is conformant; any non-zero delta is the standing manual trigger for a sweep or refresh pass.
No calendar cadence anywhere.
