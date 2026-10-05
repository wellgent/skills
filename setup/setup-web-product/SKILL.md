---
name: setup-web-product
description: Bootstrap a new web product end to end along the golden path - four inputs, then scaffold, claim, brain, project, hosting, and first ship, each stage deferred to its existing installer.
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

1. **Scaffold** - run `/setup-web-stack` against the new checkout, on its greenfield route: scaffold from the defaults reference, then toolchain and gate scripts.
2. **Claim** - registration writes up front, so nothing downstream uses placeholders.
   This stage is pluggable: where the operator keeps a project registry (port map, capability declarations, skill membership), add the project there now - next free port block on the target machine, capability declarations, pack assignment.
   With no registry, the ports still land in `.agents/launch.json`; move on.
3. **Brain** - run `/setup-brain` against the driving brain with the new `<owner>/<repo>`: the project's card, its `flow.json` entry and its ledger directory.
4. **Project** - run `/setup-project <owner>/<repo>` in the brain: folder trust, the pinned skills, `AGENTS.md`, `docs/agents/dev-loop.md` and `CODING_STANDARDS.md` from the templates, the client's critical journeys, tracker labels. It calls `/setup-web-stack` again for the stack's lines, the journey tests and, with a database, the Convex branch.
5. **Hosting** - per audience class: Vercel + Convex link for public; the self-hosted ops pattern plus cloudflared + Access (team) or `tailscale serve` (personal) for internal.
6. **First ship** - the check command runs green, production serves the shipped commit per the class's prod-parity proof, then finalize the registration (public URL, live fields) where a registry exists.

Two-phase registration is deliberate: claim at stage 2, finalize at stage 6; observation tolerates claimed-but-not-yet-live in between.

## Report

End with: the four inputs as decided, per-stage outcomes, the claimed ports and membership assignment, the prod-parity evidence from first ship, and any conformance column not yet green.
