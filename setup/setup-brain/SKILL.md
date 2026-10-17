---
name: setup-brain
description: Make a brain able to operate projects through pstack - pin the operate skill and the brain's planning skills by commit, create the run label and the request issue template, and write the operating section into its AGENTS.md. Idempotent.
argument-hint: "<path to the brain checkout>"
disable-model-invocation: true
---

# Setup brain

Bring a **brain**, the repository whose tracker holds maps and run requests, current with the operator.
Run from a checkout of this repo; the argument is the brain's checkout (ask if missing).
Every step converges on a state, so a re-run changes only what is behind.

## 1. Read the brain

`git pull --rebase` here and in the brain (a brain without a remote skips it), then the brain's `AGENTS.md` (how it commits, which conventions wrap a file) and `skills-lock.json`.
The tracker is `git remote get-url origin`.

## 2. Skills

Two sources, each pinned by commit, in the brain's root:

- `wellgent/skills`: `operate`.
- `mattpocock/skills`: `wayfinder`, `grilling`, `domain-modeling`, `research`, `prototype`, `writing-for-agents`, `wizard`, `ask-matt`.

```bash
npx skills add "<source>#<sha>" --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- The sha is the commit the brain already pins for that source when every skill of the source sits on it; otherwise the source's current `main` (`gh api repos/<source>/commits/main --jq .sha`). Moving a source to a newer commit is a decision the brain's owner takes, not a side effect of a re-run.
- Pass every `--skill <name>` as its own pair of arguments: with `-y`, a list the CLI cannot parse installs the whole source without an error.
- A skill locked at the pin (`ref` in `skills-lock.json`) is skipped. A skill at another commit, or with no `ref`, is removed (`npx skills remove <name> -y`) and added again at the pin; `npx skills update` rewrites lock entries wrongly, so updates go through `add` and `remove` only.
- Every other skill the brain pins from these two sources is removed.
- Layout afterwards: real directories under `.agents/skills/<name>`, a relative link `.claude/skills/<name>` → `../../.agents/skills/<name>` for each. The CLI writes no link and `remove` deletes one, so after every add: `mkdir -p .claude/skills && ln -sfn ../../.agents/skills/<name> .claude/skills/<name>`. Delete any directory the CLI wrote elsewhere.

## 3. Tracker

- The label: `gh label create run --repo <tracker> --description "A request for /operate" --color 0E8A16`, when missing.
- The issue template: `.github/ISSUE_TEMPLATE/run.md` in the brain is a copy of [`skills/operate/request.md`](../../skills/operate/request.md); replaced on every run.

## 4. AGENTS.md

The brain's `AGENTS.md` carries the section in [`templates/brain/operating.md`](../../templates/brain/operating.md), with the template's text; the brain's own conventions (citations, links) wrap it.
An existing section with the same heading is replaced.
A section describing an earlier way of running projects (a lead skill, a flow config, a run ledger) is removed and named in the report.

## 5. Check

Commit and push the brain by its own rules.
Done when `.agents/skills/` holds the nine skills with working `.claude/skills/` links, `skills-lock.json` carries a `ref` for each, the `run` label and the template exist, and `AGENTS.md` carries the section.

## Report

Skills added, re-pinned and removed; the label and template; the `AGENTS.md` sections written and removed.
