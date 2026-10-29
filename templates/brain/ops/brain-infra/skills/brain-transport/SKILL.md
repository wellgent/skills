---
name: brain-transport
description: "How an agent reaches and writes this brain: gbrain CLI reads, markdown-plus-Git durable writes, which checkout a writer commits from, and checkout freshness. The CLI-plus-files surface is the one canonical access model."
---

# Brain Transport

Use when working in a {{brain}} checkout, or when a task involves {{brain}}/GBrain reads or durable brain writes.

## Contract

- Shared brain behavior comes from `skills/`; read `skills/RESOLVER.md` before substantive brain work, then the skill it routes to.
- Brain reads use the `gbrain` CLI: `search`, `get`, `query`, `timeline`, validation, and status.
- Durable writes are markdown plus Git, pushed to `main` on GitHub. The brain host is the sole GBrain database writer: it imports and embeds what lands on `main` (see Host).
- On-box agent writers committing through `gbrain git commit-push` may land the merge commits it makes in memory when `main` has moved; every other writer lands linearly on `main`.
- Read governance files directly from the filesystem, not through GBrain retrieval: `AGENTS.md`, `README.md`, `RESOLVER.md`, `schema.md`, directory `README.md` files, and `skills/`.
- The CLI-plus-files surface is the one canonical access model for every session agent: reads are checkout files plus the `gbrain` CLI, writes are markdown plus Git. Session agents do not register or use raw GBrain MCP tools.

## Reaching the engine

{{read_access}}

## Access stance

- Off the brain host, people and their tools read the brain only through its thin client: a personal read-only OAuth client against the brain's HTTP endpoint, as Reaching the engine describes.
- Writes go through Git: a push to `main` on GitHub from a checkout, or an on-box writer clone through `gbrain git commit-push`.
- SSH to the brain host is for host administration. One-shot `gbrain` commands over SSH stay allowed there (doctor, repairs, the GBrain upgrade lane). A stdio `gbrain serve` over SSH is never allowed, for anyone: it runs a second persistence consumer next to the host's own, which GBrain's doctor flags as `two_consumers_on_host`.
- An agent that finds its MCP entry or a script running `gbrain serve` over SSH to the brain host switches it to the thin client, set up as Reaching the engine describes with the person's own client credentials.

## Checkout write flow

1. Run `git pull --rebase origin main` before durable edits.
2. Read the matching shared skill from `skills/`.
3. Use the `gbrain` CLI to inspect existing context.
4. Edit markdown source files.
5. Validate changed pages when practical.
6. Stage exact paths only; commit per the `AGENTS.md` commit conventions.
7. Run `git pull --rebase origin main` again, then push. If the push is rejected, rebase and retry.
8. On a rebase conflict, combine compatible edits and keep every citation and evidence row. When the facts themselves disagree, stop and surface the conflict to {{owner}}.
9. Verify with `gbrain get`, `gbrain search`, `gbrain query`, or `gbrain timeline` once the host has had time to index. If retrieval is not fresh yet, the push is still durable; the host owns sync and embed freshness.

Run `gbrain sync`, `gbrain embed`, migrations, or `gbrain serve` from a checkout session only when {{owner}} explicitly asks. The Git push is the durable handoff.

## Host

{{host_write_mechanism}}

{{local}}
