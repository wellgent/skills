---
name: setup-project
description: Bring a project onto the development flow - folder trust, third-party skills pinned by commit, AGENTS.md, dev-loop.md, CODING_STANDARDS.md and the glossary from the templates, critical journeys, tracker labels. Idempotent; Readiness re-runs it.
argument-hint: "<owner>/<repo>"
disable-model-invocation: true
---

# Setup project

Bring one project current with the flow.
Run in the **driving brain**'s checkout, after [`setup-brain`](../setup-brain/SKILL.md) has added the project: its checkout is `projects["<owner>/<repo>"].checkout` in the brain's `flow.json`.
Every step converges on a state, so a re-run changes only what is behind.
What a project must hold is in [`../requires.json`](../requires.json) under `project`; `flow ready <owner>/<repo>` checks it.

This skill names no stack.
Everything stack-specific is written by the project's **stack setup**: for a web product, [`setup-web-stack`](../setup-web-stack/SKILL.md).

## 1. Read the project

- `git pull --rebase` in `~/repos/wellgent-skills` and in the checkout (one without a remote skips it), then its `AGENTS.md`, `docs/agents/`, `skills-lock.json` and package scripts.
- `flow ready <owner>/<repo>`, run in the brain: its `behind project` lines are this run's work list.
- Note what an earlier workflow left: a project skill named `verify`, a driver skill, sections of `AGENTS.md` or `docs/agents/` that describe steps the flow replaced.

## 2. Folder trust

`flow trust <checkout>`.
Each harness asks once per repository per host, and an unanswered prompt stalls `flow spawn`; worktrees of a trusted checkout start clean.

## 3. Skills

A project pins a skill only when a step names it: the set under `.project.skills`, `impeccable` when the project has screens, and each skill its `AGENTS.md` must-read list or `docs/agents/dev-loop.md` names by path.
Each is pinned at the commit the source log names, in the checkout's root:

```bash
npx skills add "<source>#$(flow sources pin <source>)" --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- A skill already locked at that commit (`ref` in `skills-lock.json`) is skipped.
- A skill locked at another commit, or with no `ref`, is removed (`npx skills remove <name> -y`) and added again at the pin. Updates go through `add` and `remove` only; `npx skills update` rewrites lock entries wrongly.
- A pinned skill no step names is removed. One a person still invokes by hand moves to the brain or to user scope: list it in the report.
- A project skill named `verify` is deleted once its launch, sign-in and drive instructions are in the "Running the app" section of `docs/agents/dev-loop.md`. A driver skill from an earlier workflow is deleted with it.
- Layout afterwards: real directories under `.agents/skills/<name>`, a relative link `.claude/skills/<name>` → `../../.agents/skills/<name>` for each. The CLI writes no link and `remove` deletes one, so after every add: `mkdir -p .claude/skills && ln -sfn ../../.agents/skills/<name> .claude/skills/<name>`. `skills-lock.json` is committed with them.

## 4. Project docs

The templates are in [`templates/project/`](../../templates/project/).
A line that reads the same in every project is the template's and is replaced on a re-run; a line that states a fact of this repo is the project's and is kept.

- **`AGENTS.md`** is the real file and `CLAUDE.md` a symlink to it. When both are real files, show the client the difference and ask.
  The sections "Rules for every session", "Must-read" and "Where things live" carry the template's text, with the project's check command and must-read entries.
  The project's own sections stay; one that describes a step the flow replaced is removed, and named in the report.
- **`docs/agents/dev-loop.md`** has the template's sections in the template's order.
  Run the stack setup now: it fills the gate lines, worktrees, running the app, lenses, tools, scanner pass and design system.
  A project on a stack without a setup skill fills them from its own tooling, with the client.
  No placeholder is left: a line that does not apply is deleted.
- **`CODING_STANDARDS.md`** from the template when absent. An existing one is the project's.
- **`GLOSSARY.md`** holds the domain language. A `CONTEXT.md` is renamed (`git mv`) with every reference to it; with neither, create the file with its title only.
- **`docs/agents/issue-tracker.md`, `triage-labels.md`, `domain.md`**: write them from the templates inside the brain's pinned `setup-matt-pocock-skills`, with the choices fixed: the GitHub tracker, each triage role mapped to the label of the same name except `ready-for-human`, which is `needs-human`, and single-context domain docs.
- **`.github/ISSUE_TEMPLATE/bug.md`** from the template, so every bug carries its origin spec.
- **`docs/adr/`** exists.

## 5. Critical journeys

The client names at most five journeys, each a user's goal; nobody else picks them.
Put them to the client with what the product's main flows are and your suggestion.
Each approved journey gets one browser test, scaffolded by the stack setup, and a line under "Critical journeys"; the "Journey tests" gate line names the command that runs them all.
Until the client has approved a list, the section says `none approved` and the gate line is absent.

## 6. Tracker

- Create each label of `.project.labels` the tracker lacks, with `gh label create <label> --repo <owner>/<repo>`.
- `main` lands by fast-forward only:

```bash
gh api -X PATCH repos/<owner>/<repo> -F allow_merge_commit=false -F allow_rebase_merge=true -F delete_branch_on_merge=true
```

## 7. Check

1. Run the check command on `main`. A step that is red moves out of the command and under "Pending checks" in `docs/agents/dev-loop.md`, until a cleanup spec gets it green.
2. Commit and push, by the Landing rule in the project's `AGENTS.md`.
3. Done when `flow ready <owner>/<repo>` prints no `behind project` line and no `behind host` line about this checkout.

## Report

Skills added, re-pinned, removed and moved out; each doc created or changed, with the sections removed; the journeys approved or still open; labels and repo settings; pending checks; the questions put to the client; the final `flow ready` output.
