---
name: setup-brain
description: Make a brain able to plan with wayfinder and operate projects through pstack - the operate skill and the planning skills pinned by commit, the tracker labels, the tracker docs and the request template, and the planning and operating sections of its AGENTS.md. Idempotent.
argument-hint: "<path to the brain checkout>"
disable-model-invocation: true
---

# Setup brain

Converge a **brain**, the repository whose tracker holds maps and run requests, on the state below.
Run from a checkout of this repo; the argument is the brain's checkout (ask if missing). A re-run changes only what is behind.

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

- The sha is the commit the brain already pins for that source when every skill of the source sits on it, otherwise the source's current `main` (`gh api repos/<source>/commits/main --jq .sha`). A newer commit is the owner's decision, never a re-run's side effect.
- Pass every `--skill <name>` as its own pair of arguments: with `-y`, a list the CLI cannot parse installs the whole source without an error.
- A skill locked at the pin (`ref` in `skills-lock.json`) is skipped; one at another commit, or with no `ref`, is removed (`npx skills remove <name> -y`) and added again at the pin. `npx skills update` rewrites lock entries wrongly, so updates go through `add` and `remove` only.
- Every other skill the brain pins from these two sources is removed.
- Layout: real directories under `.agents/skills/<name>`, a relative link `.claude/skills/<name>` → `../../.agents/skills/<name>`. The CLI writes no link and `remove` deletes one, so after every add: `mkdir -p .claude/skills && ln -sfn ../../.agents/skills/<name> .claude/skills/<name>`. Delete any directory the CLI wrote elsewhere.

## 3. Tracker

- Every label in [`templates/brain/labels.json`](../../templates/brain/labels.json) exists on the tracker with that colour and description: `gh label create <name> --repo <tracker> --color <color> --description <description> --force`.
- `.github/ISSUE_TEMPLATE/run.md` in the brain is a copy of [`skills/operate/request.md`](../../skills/operate/request.md), written on every run.

## 4. Docs

`docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md` and `docs/agents/domain.md` in the brain carry the files of the same name in [`templates/brain/`](../../templates/brain/), with `<owner>/<repo>` filled.
Template prose is replaced on a re-run; a line that states a fact of this brain (its own handoff rules, its page and citation conventions, its directories) is the brain's and is kept.

## 5. AGENTS.md

The brain's `AGENTS.md` carries the two sections in [`templates/brain/operating.md`](../../templates/brain/operating.md) with the template's text, wrapped in the brain's own conventions (citations, links); lines the brain adds under them are the brain's and are kept.
Sections under the same headings are replaced; any other section on planning skills or on running projects is removed and named in the report.

## 6. Check

Commit and push the brain by its own rules.
Done when `.agents/skills/` holds the nine skills with working `.claude/skills/` links and a `ref` each in `skills-lock.json`, every label and the request template exist, the three docs carry the template's sections, and `AGENTS.md` carries both sections.

## Report

Skills added, re-pinned and removed; labels created or changed; the template and docs written; the `AGENTS.md` sections written and removed.
