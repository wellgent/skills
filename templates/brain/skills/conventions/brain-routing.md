# Brain Routing Convention

Cross-cutting rules for which brain and which source an operation targets.

Use this before any skill reads, writes, captures, syncs, imports, or reviews pages.

## Core model

- **Brain** means the database/engine target.
- **Source** means the repo or corpus inside that brain.

Pick one brain and one source for every operation. Do not silently mix them.

## Default rule

Start from the resolved local environment unless the user names another target.

Useful checks:

```bash
gbrain mounts list
gbrain sources current --json
gbrain sources list --json
```

When the runtime or command supports explicit flags, prefer making routing visible:

```bash
gbrain search "query" --source <source-id>
gbrain query "question" --source <source-id>
```

Use the exact flag names supported by the installed GBrain version.

## Source resolution

Current upstream GBrain resolves source context from explicit flags, environment, dotfiles, registered local paths, configured defaults, single-source fallbacks, and finally the seed default. Treat the resolver as the authority.

Before destructive or writeful operations, confirm the current source:

```bash
gbrain sources current --json
```

Do not assume a temp directory, clean clone, or runtime workspace points at the intended brain source.

## When to switch brain

Switch brain only when the user explicitly names a brain/team/client, the data clearly belongs to that brain, or the runtime context is already pinned to it.

If unsure, stay in the current owner/personal brain and ask before writing elsewhere.

## When to switch source

Switch source when:

- the user names a repo/corpus
- the current checkout has a source dotfile
- the data origin belongs to a specific source
- the review routine names a registered brain instance/source path

Do not isolate source scope when the user asked a cross-source question. In that case, search multiple sources explicitly and cite where each finding came from.

## Trust boundary

CLI source resolution is local-context behavior. Remote thin-client callers should use their authenticated allowed brain/source scope and must not inherit server process dotfiles or environment as user intent.

Agent Access reviews should check that hosted or remote clients cannot accidentally write to every source just because the host process can.

## Citations

For single-brain answers, use the target brain's normal citation rules.

For cross-brain or cross-source synthesis, name the brain/source enough that the user can trace it:

```text
[Source: <brain>:<source>:<slug>]
```

## Anti-patterns

- Searching one brain, then answering as if all brains were searched.
- Writing to a team/client brain without explicit intent.
- Letting temp working directories retarget sync/source state.
- Ignoring `.gbrain-source`, registered `local_path`, or an authenticated client's source scope.
