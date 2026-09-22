---
name: setup-web-product
description: Bootstrap a new web product end to end along the golden path - four inputs, then scaffold, claim, skills, workflow, contract, hosting, and first ship, each stage deferred to its existing installer.
argument-hint: "<product name> (remaining inputs gathered interactively)"
disable-model-invocation: true
---

# Setup web product

The golden path for a new web product, per the "New projects" section of [`standards/web-products.md`](../../standards/web-products.md).
This skill is pure composition: it gathers the four real inputs, then drives each stage through the tool that owns it - no stage's knowledge is duplicated here.
Done means conformant and live, not repo-created.

## 1. Gather the four inputs

1. **Name + repo home** - product name and GitHub org.
2. **Audience class** - public / team-internal / personal; decides hosting entirely per the standard's hosting section.
   If internal: which host co-locates it (data gravity picks the host).
3. **Data need** - knowledge-base content / needs-a-database / none, per the standard's data layer rule.
   A database means Convex and flips the convex pack trigger.
4. **Machine** for self-hosted products - usually implied by co-location.

Everything else is defaulted, not asked: Next latest stable per the channel rule, Tailwind v4 on, the full toolchain standard, the gate composition, base skills plus triggered packs, next free port block on the target machine, canonical label taxonomy.
Cache Components defaults on for greenfield (the user can decline).

## 2. Drive the stages, in order

1. **Scaffold** - run `/setup-web-stack` against the new checkout, on its greenfield route: scaffold from the defaults reference, then toolchain, gate scripts, AGENTS.md/CLAUDE.md convention.
2. **Claim** - registration writes up front, so nothing downstream uses placeholders.
   This stage is pluggable: where the operator keeps a project registry (port map, capability declarations, skill membership), add the project there now - next free port block on the target machine, capability declarations, pack assignment.
   With no registry, the ports still land in `.agents/launch.json`; move on.
3. **Skills** - install the membership verdict: the registry's declared set where one exists, otherwise the curated base plus the packs the repo's facts trigger (per the standard's Skills section), by explicit `npx skills add`.
4. **Workflow** - run `/setup-matts-skills` against the checkout: the curated set, instructions-file convention, orchestrate driver, canonical labels.
5. **Contract** - dev-loop declarations from orchestrate's `dev-loop-declarations.md` reference; the claimed ports land in `.agents/launch.json` (with the committed `.claude/launch.json` symlink); project `verify` skill from `verify-reference.md`.
6. **Hosting** - per audience class: Vercel + Convex link for public; the self-hosted ops pattern plus cloudflared + Access (team) or `tailscale serve` (personal) for internal.
7. **First ship** - the gate runs green, production serves the shipped commit per the class's prod-parity proof, then finalize the registration (public URL, live fields) where a registry exists.

Two-phase registration is deliberate: claim at stage 2, finalize at stage 7; observation tolerates claimed-but-not-yet-live in between.

## Report

End with: the four inputs as decided, per-stage outcomes, the claimed ports and membership assignment, the prod-parity evidence from first ship, and any conformance column not yet green.
