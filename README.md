# Wellgent Agent Skills

How we run product work with agents at [Wellgent](https://wellgent.ai), published for anyone to adopt: [pstack](https://github.com/cursor/plugins/tree/main/pstack) runs each project, a brain decides what to run, and the pieces here connect the two.

## The shape

- **pstack** (the [Claude Code port](https://github.com/michael-denyer/pstack-claude), installed as the plugin `pstack@pstack-claude` per project) owns everything inside a project: planning, build, review, verification, pull requests, shipping and retro.
- **A brain** is the repository where decisions and requests live: wayfinder maps for what to do, and **run requests** for what pstack should run. A request is one tracker issue with the five parts pstack's own prompting guide asks for: goal, a done check that passes or fails, the proof, what is known, constraints.
- **`/operate <issue>`**, run from the brain, turns a request into a pstack run: it writes the prompt, starts the run as its own herdr session in the project checkout with landing authority, and stops. The run merges what its verifier passes and posts its note back on the request.

## Layout

- [`AGENTS.md`](AGENTS.md) - the entry for an agent pointed at this repo.
- [`skills/operate/`](skills/operate/) - the operator skill: the request template, the prompt template, the start script and the cost script. Installed into a brain by `setup-brain`.
- [`setup/`](setup/) - the setup skills, run from this checkout:
  - **setup-brain** - pins `operate` and the brain's planning skills from mattpocock/skills, creates the tracker labels, the tracker docs under `docs/agents/` and the request issue template, and writes the planning and operating sections into the brain's `AGENTS.md`.
  - **setup-project** - enables the pstack plugin at project scope, pins the project's stack skills by commit, writes CI for the check command, lays down `AGENTS.md` and `docs/agents/dev-loop.md` from the templates, and offers pstack's verification skill. It names no stack. It is also where the plugin pin moves, on purpose.
  - **setup-web-stack** - the stack setup for a web product: a curated [catalog](setup/setup-web-stack/catalog.md) of community skills, quality tooling and known-good configs, the CI workflow, the journey tests and the Convex branch.
  - **setup-web-product** - the golden path for a new web product, each stage deferred to its installer.
- [`templates/project/`](templates/project/) - `AGENTS.md` and `docs/agents/dev-loop.md` as the setup scaffolds them into a project.
- [`templates/brain/`](templates/brain/) - what `setup-brain` writes into a brain: the labels, the three tracker docs and the `AGENTS.md` sections.
- [`standards/web-products.md`](standards/web-products.md) - the stack doctrine for web products: frontend, toolchain, hosting, data layer, checks, design, version control, skills.

## What belongs here

Everything we use regularly lives here, shared with the world, friends, clients and the machines we manage.
Truly internal things live at project or repo level: one project's specifics stay in that project; maps, requests, version pins and fleet machinery stay in private repos.
Everything published here is internals-free: no person, project, company or host is named, and it works unmodified from a stranger's checkout.

## Conventions assumed

- Claude Code with the pstack plugin on every host that runs a project, and [herdr](https://github.com/herdr) on the host `/operate` runs on.
- A GitHub repository per project and per brain, with GitHub Issues as the tracker and GitHub Actions for the check command.
- [mattpocock/skills](https://github.com/mattpocock/skills) for the brain's planning skills, pinned by commit.

## License

[MIT](LICENSE)
