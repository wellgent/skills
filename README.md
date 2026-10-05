# Wellgent Agent Skills

The agentic engineering approach we design and run in production at [Wellgent](https://wellgent.ai), published for anyone to adopt: the development flow, the setup paths, and the normative doctrine behind them.

## The flow

[`FLOW.md`](FLOW.md) is the development flow on one page: eleven stages from Readiness to Retro, each with one role, one input, one output and a quality bar, and the artifacts handed between them.
[`GLOSSARY.md`](GLOSSARY.md) defines its terms.

The flow is read in place from one checkout of this repo per run host, at `~/repos/wellgent-skills`.
Nothing from it is installed or pinned into a project, so a flow change reaches every project with one `git pull` on the host.
A project pins only the third-party skills a step names, by commit sha.

## Layout

- [`FLOW.md`](FLOW.md), [`GLOSSARY.md`](GLOSSARY.md) - the flow doc and its language.
- `lead/` - the lead skill: the stages the lead runs itself (Readiness, Shape, Plan, Release, Retro) and how it starts and sequences every step. Linked into the user's skills directory on each run host.
- `stages/<stage>/` - one skill per spawned stage: `ux-design`, `system-design`, `grooming`, `build`, `review`, `qa`, `audit`. Each opens with its header from `FLOW.md`. `flow spawn` puts the skill's absolute path in the session's start prompt; a `-second` step and the `audit-architecture` steps read their stage's skill.
- [`bin/`](bin/) - the `flow` command (`spawn`, `gate`, `land`, `tick`, `report`, `ask`, `ledger`) and its scripts, Bash with `jq`; `flow help` lists them and [`bin/README.md`](bin/README.md) holds what they read. `bin/flow` is linked into the user's `PATH` on each run host.
- `ledger/` - the ledger schema and the price table the cost script reads. The ledger files themselves live in the driving brain.
- [`templates/artifacts/`](templates/artifacts/) - the hand-off artifact formats `FLOW.md` names.
- `templates/project/` - what the setup skills scaffold into a project: `AGENTS.md`, `docs/agents/dev-loop.md`, `CODING_STANDARDS.md`.
- `templates/brain/` - what the setup skills scaffold into a driving brain: the flow config and the project card.
- `source-log.md` - every upstream source the flow depends on, with the last version seen and its date. Readiness reviews it in full.
- [`setup/`](setup/) - the setup skills.
- [`standards/`](standards/) - the doctrine.

## Setup paths

Operator skills under [`setup/`](setup/): run from a checkout of this repo against a target path, in either harness (`.claude/skills/` and `.agents/skills/` link to them).

- **setup-matts-skills** - set up Matt Pocock's engineering workflow in a target project: the curated `mattpocock/skills` selection and the `AGENTS.md` convention.
- **setup-web-stack** - equip a web project from a curated [catalog](setup/setup-web-stack/catalog.md) of community skills, quality tooling and known-good configs.
- **setup-web-product** - the golden path for a new web product, each stage deferred to its installer.

## The doctrine

[`standards/web-products.md`](standards/web-products.md) is the normative approach the setup skills implement: judging criterion, frontend and toolchain stances, hosting classes, data layer, quality gate, skills model, and methodology.
It carries the slow-moving rules and every stack-specific one; the flow skills name no stack.
Exact version pins and per-project membership are operational state and live in the adopter's own private registry.

## What belongs here

Everything we use regularly lives here - shared with the world, friends, clients, and the machines we manage.
Truly internal things live at project or repo level: one project's specifics stay in that project; project cards, iteration maps, ledgers, version pins and fleet machinery stay in private repos.

Everything published here is internals-free: no person, project, company or host is named, and it works unmodified from a stranger's checkout.

## Conventions the flow assumes

- [mattpocock/skills](https://github.com/mattpocock/skills) pinned in the project: the flow runs its `to-spec`, `to-tickets`, `implement-spec`, `code-review` and `retro` as written and builds only what they lack.
- A GitHub-style issue tracker with sub-issues and native blocking edges.
- herdr on the run host: every step runs as its own session and reports to the lead's session.
- Claude Code and Codex on the run host: a step's harness follows its model in the flow config.

## License

[MIT](LICENSE)
