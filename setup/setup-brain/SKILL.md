---
name: setup-brain
description: Make a brain able to plan with wayfinder, operate projects through pstack, and carry the shared core - the operate skill and the planning skills pinned by commit, the tracker labels and the request template, and every shared-core file, written where missing and cross-checked where present. Idempotent.
argument-hint: "<path to the brain checkout>"
disable-model-invocation: true
---

# Setup brain

Converge a **brain**, the repository whose tracker holds maps and run requests, on the state below.
Run from a checkout of this repo; the argument is the brain's checkout (ask if missing). A re-run changes only what is behind, and never overwrites a file the brain already has.

## 1. Read the brain

`git pull --rebase` here and in the brain (a brain without a remote skips it), then the brain's `AGENTS.md` (how it commits, which conventions wrap a file) and `skills-lock.json`.
The tracker is `git remote get-url origin`.

## 2. Skills

Two sources, each pinned by commit, in the brain's root:

- `wellgent/skills`: `operate`, pinned by [`skills/operate/scripts/sync-brain`](../../skills/operate/scripts/sync-brain) `<brain checkout>`, which also writes the run request template and the `run` label; `/operate`'s Ready runs the same script before every run.
- `mattpocock/skills`: `wayfinder`, `grilling`, `domain-modeling`, `research`, `prototype`, `writing-for-agents`, `wizard`, `ask-matt`, through the steps below.

```bash
npx skills add "<source>#<sha>" --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- The sha is the commit the brain already pins for that source when every skill of the source sits on it, otherwise the source's current `main` (`gh api repos/<source>/commits/main --jq .sha`). A newer commit is the owner's decision, never a re-run's side effect.
- Pass every `--skill <name>` as its own pair of arguments: with `-y`, a list the CLI cannot parse installs the whole source without an error.
- A skill locked at the pin (`ref` in `skills-lock.json`) is skipped; one at another commit, or with no `ref`, is removed (`npx skills remove <name> -y`) and added again at the pin. `npx skills update` rewrites lock entries wrongly, so updates go through `add` and `remove` only.
- Every other skill the brain pins from these two sources is removed.
- Layout: real directories under `.agents/skills/<name>`, a relative link `.claude/skills/<name>` → `../../.agents/skills/<name>`. The CLI writes no link and `remove` deletes one, so after every add: `mkdir -p .claude/skills && ln -sfn ../../.agents/skills/<name> .claude/skills/<name>`. Delete any directory the CLI wrote elsewhere.

## 3. Tracker

- Every label in [`labels.json`](labels.json) exists on the tracker with that colour and description: `gh label create <name> --repo <tracker> --color <color> --description <description> --force`.
- `.github/ISSUE_TEMPLATE/run.md` in the brain is a copy of [`skills/operate/request.md`](../../skills/operate/request.md), written by `sync-brain` in step 2.

## 4. Shared core

The shared core is [`templates/brain/`](../../templates/brain/): every file all brains carry, at its brain path, with placeholders that [`templates/brain/README.md`](../../templates/brain/README.md) indexes.
Cross-check the brain against it:

```bash
setup/setup-brain/core-check brain <brain checkout> --values
```

Each core file comes back `ok`, `missing` or `deviates`; for `AGENTS.md`, each core section does.

- **Missing**: write it from the core, every placeholder filled. A value comes from what `--values` prints for the brain's other copies, else from the brain itself (`git remote get-url origin` for `tracker`, `skills/_brain-filing-rules.json` for `writes_to`, `README.md`, `RESOLVER.md` and `schema.md` for the rest), else from the owner. Each `{{local}}` is written as nothing. A missing `AGENTS.md` section goes in under its core heading, unless the brain already covers that subject under another heading; then it counts as a deviation.
- **Deviates**: leave the file as it is, and name it in the report with the core line it fails. Settling it is the owner's call: promote the brain's text to the core, turn it into a placeholder, or revert the brain's copy.

Re-run `core-check` until every file it reports is `ok` or a deviation named in the report.

## 5. Check

Commit and push the brain by its own rules.
Done when `.agents/skills/` holds the nine skills with working `.claude/skills/` links and a `ref` each in `skills-lock.json`, every label and the request template exist, and `core-check` reports each core file `ok` or as a reported deviation.

## Report

Skills added, re-pinned and removed; labels created or changed; the request template written; core files and `AGENTS.md` sections written; every deviation with its failing core line.
