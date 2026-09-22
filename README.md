# Wellgent Agent Skills

The agentic engineering approach we design and run in production at [Wellgent](https://wellgent.ai), published for anyone to adopt: the skills, the setup paths, and the normative doctrine behind them.

Install skills into a project with the [skills](https://www.skills.sh/) CLI:

```bash
npx skills add wellgent/skills
```

Select specific skills with `-s`:

```bash
npx skills add wellgent/skills -s orchestrate
```

## Skills

Distributed skills: installed into consumer projects as ordinary `npx skills` pins and read in place there.

- **orchestrate** - run one dev-loop session as the driver: preflight, select, drive one spec end to end, tear down, report.
  Harness-generic: grooming drafts run in fresh subagents of the driving harness; implementation takes run on the executor the project contract names - the harness's native subagents by default, or an external harness via a runner file (`runners/codex.md` ships takes as `codex exec` sessions). Review and every tracker write stay with the driver.

## Setup paths

Operator skills under [`setup/`](setup/): run from a checkout of this repo against a target project path, in either harness (`.claude/skills/` and `.agents/skills/` link to them). They are never installed into a project and never listed by the skills CLI - they carry the catalog and the curated selection, so they run at this repo's HEAD by design.

- **setup-matts-skills** - set up Matt Pocock's engineering workflow in a target project: the curated `mattpocock/skills` selection (declared in the skill - it is the stance), the AGENTS.md convention, and the orchestrate driver on top.
- **setup-web-stack** - equip a web project from a curated [catalog](setup/setup-web-stack/catalog.md) of community skills, quality tooling, and known-good configs: two routes - scaffold greenfield from the defaults reference, or read an existing project and install just what fits it.
- **setup-web-product** - the golden path for a new web product: four inputs, then scaffold, claim, skills, workflow, contract, hosting, and first ship, each stage deferred to its installer.

## The doctrine

[`standards/web-products.md`](standards/web-products.md) is the normative approach the setup skills implement: judging criterion, frontend and toolchain stances, hosting classes, data layer, quality gate, skills model, and methodology.
It carries the slow-moving rules; exact version pins and per-project membership are operational state and live in the adopter's own private registry.

## What belongs here

Everything we use regularly lives here - shared with the world, friends, clients, and the machines we manage.
Truly internal things live at project or repo level: one project's specifics stay in that project; operational registries, version pins, and fleet machinery stay in private repos.

A skill published here is internals-free - any coupling to a specific product, company, or environment is expressed generically - and works unmodified in a stranger's repo: install it, read it, run it, with no tribal knowledge required.
A distributed skill under `skills/` is consumed like any third-party skill: an ordinary `npx skills` pin in the consuming repo's `skills-lock.json`. A setup path under `setup/` is consumed by cloning this repo and running it against the target.

## Conventions these skills assume

`orchestrate` is an **add-on to [mattpocock/skills](https://github.com/mattpocock/skills)**, not a standalone workflow: it drives that set's `to-tickets` (grooming) and `implement` (takes), and rides the triage-label conventions its `setup-matt-pocock-skills` establishes.
Install the mattpocock set into the project first - `setup-matts-skills` is the path that does it.

The loop's semantics ship with the skill and are read in place - [`dev-loop-protocol.md`](skills/orchestrate/references/dev-loop-protocol.md) - so skill updates carry protocol updates with no per-project reconcile.
Takes always run on the driving harness's native subagent mechanism (Claude Code spawns Claude subagents, Codex its own way); an explicit invocation request may route takes through a runner file instead (`runners/codex.md`).

On top of that, the project carries only what is project-specific:

- a slim declarations contract at `docs/agents/dev-loop.md` - ports, scripts, gate proofs, and any deliberate protocol deviations; on conflict the contract wins. Scaffold it from [`dev-loop-declarations.md`](skills/orchestrate/references/dev-loop-declarations.md)
- tracker mechanics at `docs/agents/issue-tracker.md`, and a project-local `verify` skill for runtime verification (shared mechanics read in place from [`verify-protocol.md`](skills/orchestrate/references/verify-protocol.md); scaffold: [`verify-reference.md`](skills/orchestrate/references/verify-reference.md))
- a GitHub-style issue tracker with labels (`ready-for-agent`, `in-progress`, `needs-human`, `needs-triage`, `needs-info`), sub-issues, and blocking edges

A project missing these can still read the skill as a reference workflow, but the loop's guarantees come from the protocol plus the contract.

## License

[MIT](LICENSE)
