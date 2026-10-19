# Shared core for brains

The placeholder-bearing reference copy of every file all brains carry.
It mirrors brain paths: `templates/brain/<path>` is the core of `<path>` in every brain.
Nothing installs it and nothing links to it at runtime. Each brain keeps its own concrete copies with its own values; `setup-brain` writes the missing ones and cross-checks the rest.

## Layers

- **Planning layer**: the tracker docs under `docs/agents/`, and the "Planning workflow" and "Operating projects" sections of `AGENTS.md`.
- **Brain-ops layer**: the core behavior skills under `skills/` (`brain-ops`, `query`, `capture`, `signal-detector`, `brain-taxonomist`, `repo-architecture`) with their routing evals, the shared conventions under `skills/conventions/`, `skills/_output-rules.md`, `skills/README.md`, `brain-transport` under `ops/brain-infra/skills/`, and the other shared `AGENTS.md` sections.
- **Brain-infra reference copies**: each brain-infra skill that every brain runs has its reference copy under `ops/brain-infra/skills/`, starting with `gbrain-host-reconciler`; the concrete copy and its scripts live in each brain.

[`templates/workspace/AGENTS.md`](../workspace/AGENTS.md) is the brain section of the `AGENTS.md` of an agent runtime workspace bound to a brain on its host.

Everything else develops per brain: `RESOLVER.md`, `schema.md`, the schema pack, page templates, `skills/RESOLVER.md`, `skills/_brain-filing-rules.*`, the brain-local skills, and every `AGENTS.md` section the core does not hold.

## Placeholders

Placeholders exist only here; a brain's copy carries its values and no markers.

- `{{name}}` inside a line is an inline value.
- A line holding only `{{name}}` is a block of any number of lines.
- `{{local}}` marks where a brain may add its own lines, including the end of each `AGENTS.md` section.
- A name repeated within one file carries the same value.

The index:

- `{{brain}}` - the brain's display name.
- `{{owner}}` - the person whose statements are the brain's highest-authority source and who settles ambiguous calls.
- `{{tracker}}` - the brain's GitHub repository as `owner/repo`, which is also its tracker.
- `{{example_org}}` - an organization the brain holds a page for, named in routing-eval fixtures.
- `{{writes_to}}` - block in skill frontmatter: the active page directories a writing skill files into, matching `skills/_brain-filing-rules.json`.
- `{{subject_dirs}}` - the directories whose subject pages carry the brain's domain terms and decisions.
- `{{schema_docs}}` - the files that define page structure: `schema.md` plus any focused schema notes and template directories.
- `{{research_records}}` - where a research run record lands, and the doc that governs it.
- `{{research_route}}` - the skill or tool that runs research leaving the brain, as `AGENTS.md` names it.
- `{{external_research}}` - block in `brain-first.md`: the tool route for each class of external research.
- `{{commit_scopes}}` - block in `AGENTS.md`: the brain's commit scopes as a nested list.
- `{{read_access}}` - block in `brain-transport`: how the `gbrain` CLI reaches the engine on each kind of machine.
- `{{host_write_mechanism}}` - block in `durable-write.md` and `brain-transport`: how the brain host turns pushed commits into the index. In `brain-transport` it also holds the writer roster: each writer, the checkout it commits from, and its author name.
- The host reconciler's `config.json` placeholders are its brain values, each named for what it holds: `{{name}}` (the brain's slug), `{{github_repo}}`, `{{host_home}}`, `{{host_path}}`, `{{source_id}}`, `{{alert_account}}`, `{{ops_alerts_channel}}`, `{{owner_github}}`, `{{reconciler_author}}` and `{{reconciler_email}}`.
- `{{published_copy}}` - workspace: the host path of the brain checkout the workspace reads.
- `{{agent_write_flow}}` - block in the workspace: where and how the workspace's agent commits and pushes brain writes.

## Cross-check

`setup/setup-brain/core-check brain <brain checkout>` compiles each core file into a pattern where placeholders match anything, and reports every file as ok, missing or deviating. `core-check workspace <workspace checkout>` does the same for the workspace section, and `--values` prints the values a target's copies carry.
`AGENTS.md` is checked by section, and blank lines are ignored.

A deviation is settled one of three ways: promote the brain's change to the core, turn the differing text into a placeholder, or revert the brain's copy.
