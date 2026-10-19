## Operating order

1. Read `README.md` when you need repo structure or navigation context.
2. For every incoming user message, consider whether it contains durable signal. When durable signal may exist, run `skills/signal-detector/SKILL.md` non-blocking when background or subagent execution is available; otherwise do a minimal inline scan without derailing the main task. Skip pure acknowledgments, purely operational commands, duplicate material, and unsafe or private material that should not be retained.
3. Before answering durable questions about people, companies, projects, programs, decisions, timelines, relationships, or strategy, search and read the brain first.
4. For research that leaves the brain, any question whose answer must rest on cited external sources, follow the external research standard in `skills/conventions/brain-first.md` and route it through {{research_route}}.
5. Before brain work in this repo, read `skills/RESOLVER.md` and load the skill it routes to.
6. For how an agent reaches and writes this brain (gbrain CLI access, the checkout write flow, the host and its writers), use the `brain-transport` skill at `ops/brain-infra/skills/brain-transport/SKILL.md`.
7. On the brain host, `{{published_copy}}` is the published copy: read it and never edit it, whatever directory the session started in. Write from your own writer clone on the `brain-transport` roster; a file left in the published copy pauses publication for every writer until the reconciler moves it to a rescue branch.
8. Before creating or moving any brain page, read `RESOLVER.md`.
9. If placement is ambiguous, read the target directory `README.md` resolver.
10. Follow {{schema_docs}} for page structure, citation format, enrichment rules, templates, and maintenance conventions.
11. Write {{owner}}'s corrections about people, companies, projects, programs, decisions, or durable facts immediately when safe.
12. Update existing pages before creating new ones.
13. Put subject knowledge in the matching directory. Keep root files focused on navigation and conventions.
14. Append `log.md` for brain-level operational events: schema, resolver and template changes, brain-wide source imports, batch migrations, recurring routine wiring, maintenance and repair passes, and repo-scale workflow changes. Routine signal captures, ordinary subject facts, task movement, and ledger imports belong on subject timelines, task pages, and the ledgers themselves.
{{local}}

## Skill homing

Every skill originates in exactly one of three homes:

- **Brain-authored workflow skills** originate in `ops/<domain>/skills/` and are symlinked into both `.agents/skills/` and `.claude/skills/`. Domain roster and layout: `ops/README.md`.
- **npx-managed skills** (pinned community sets such as mattpocock/skills) originate as real directories in `.agents/skills/`, version-pinned in `skills-lock.json`, with `.claude/skills/` symlinks.
- **The core brain skills** originate in `skills/`, routed by `skills/RESOLVER.md`; `skills/README.md` states how they relate to the shared core.

When adding or moving a skill, home it by origin, wire the symlinks in both harness dirs, and verify they resolve.
{{local}}

## Planning workflow

Big or fuzzy efforts are charted with `wayfinder` as a map of decision tickets on this tracker and worked one ticket per session; `grilling`, `domain-modeling`, `research` and `prototype` resolve the tickets, `wizard` scripts the steps only a person can do, `ask-matt` routes between them, and `writing-for-agents` is the reference for authoring skills and this file.

- The tracker is GitHub Issues on `{{tracker}}`: operations, the label axes and the handoff rules are in `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`.
- Domain-doc conventions map to brain surfaces per `docs/agents/domain.md`: vocabulary from `schema.md` and subject pages; decisions on subject pages, not ADRs.
- The eight skills and `operate` are pinned by commit in `skills-lock.json` and converged by `setup-brain` in wellgent/skills, homed per "Skill homing" above; changes go through explicit `npx skills add|remove`, never `skills update`. After an install, verify the `.agents/skills/` + `.claude/skills/` symlink layout and stage the changed paths.
{{local}}

## Operating projects

Product work on a project runs through pstack, started from this brain with `/operate <issue>`.

- A **run request** is one issue on this tracker labelled `run`, in the shape of the "Run request" issue template: the project as `owner/repo`, the goal, a done check that passes or fails, the proof, what is known, constraints. It names no host; the run starts on whichever host `/operate` runs on.
- `/operate <issue>` starts the run as its own herdr session in the project checkout and stays the run's operator. The run merges what its verifier passes and posts its stops and its note on the request; the operator answers each stop the request and the brain settle, and assigns the requester for the calls that are theirs and once it has checked the note. Open issues labelled `run` and assigned to you are the calls and checked notes waiting for you.
- A wayfinder map whose route reaches work on a project ends in run requests, one per run, linked from the map; the map stays the record of what to do, the request the record of one run.
- `/operate cost <session id>` prices a finished run from its transcript on this host.
{{local}}

## Governance files

Root control files and brain-local skills are governance, not ordinary brain pages. `AGENTS.md`, `RESOLVER.md`, `schema.md`, `README.md`, `index.md`, `log.md`, directory `README.md` files, and `skills/` tell agents how to operate, file, and write. Read them directly from the repo when needed; do not rely on GBrain search results to retrieve them.

Repo-control files and `skills/` are filesystem authority. Treat any derived GBrain row for these surfaces as incidental; direct file reads are authoritative.

When answering questions about repo history, migrations, maintenance, or workflow changes, read `log.md` directly from disk; `gbrain search`, `gbrain query`, and `gbrain get log` do not retrieve it.
{{local}}

## Writing and docs

- Make every produced doc self-sufficient: it should read cold, state the current truth or intended state directly, and avoid relying on conversation context, prior plans, renames, pivots, or "as discussed" history unless the document is explicitly historical.
- State operational rules positively. Do not encode rejected alternatives, upstream diffs, migration scar tissue, or negative comparisons unless the artifact is explicitly a historical record.
{{local}}

## Formatting

- Use plain text in docs and commit messages.
- Use a regular hyphen with spaces: ` - `.
- Use bullets instead of markdown tables for `feature -> description` patterns with sentence-length content.
- Use kebab-case filenames, for example `runtime-agent.md`.
- Root convention files keep their standard names: `README.md`, `AGENTS.md`, `CLAUDE.md`, and `RESOLVER.md`.
- `CLAUDE.md` is a regular sync-safe Claude Code entry file that points to `AGENTS.md`; `AGENTS.md` remains authoritative.
{{local}}

## References and links

- Use backtick paths only when referring to files as files, for example `people/jane-doe.md`.
- Use markdown links for brain-page relationships, for example `[Jane Doe](people/jane-doe.md)`.
- Put durable adjacency in `See Also`; put dated relationship evidence in `Timeline`.
- Keep GBrain graph links recoverable from page content. When a relationship matters, verify it with GBrain link/backlink tools.
- For multi-source GBrain results, cite pages with `[source-id:slug]` using the `source_id` returned by GBrain.
- When renaming or moving a file, grep for stale paths and update the references in the same change.
{{local}}

## Commits

- Use a single lowercase scope, a colon, then a concise imperative summary: `<scope>: <summary>`.
- Keep the subject under about 70 characters when reasonable.
- Pick the most specific scope for the change:
{{commit_scopes}}
- Keep commit messages author-neutral and project-focused.
- Use a heredoc for substantive multi-line messages:

```bash
git commit -m "$(cat <<'MSG'
docs: refine agent conventions

Align repository conventions with GBrain's resolver and link model.
MSG
)"
```

- Stage files by name.
- Make thematic commits. One coherent change per commit.
- Keep `main` history linear. Commit on `main` or on a branch or worktree (wayfinder `research/<name>` branches included); a branch lands by rebasing onto `origin/main`, fast-forwarding (`git merge --ff-only`), and pushing. No merge commits, no pull requests unless {{owner}} asks for one.
- For approved history rewrites, use `--force-with-lease`.
{{local}}

## Before committing

- Run `git status` to confirm only intended files changed.
- Run `find . -type f -not -path './.git/*' | sort` to spot-check the structure.
- Run GBrain lint on syncable pages only; whole-repo lint flags repo-control and `ops/` support files that sync intentionally excludes.
- After any rename or move, grep for stale references, for example `grep -r "old/path" .`.
- Check formatting conventions before staging.
{{local}}
