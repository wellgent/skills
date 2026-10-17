---
name: setup-project
description: Bring a project onto pstack - the plugin at project scope, stack skills pinned by commit, CI on every pull request, AGENTS.md and dev-loop.md from the templates, the verification skill. Idempotent; the plugin pin moves here.
argument-hint: "<owner>/<repo>"
disable-model-invocation: true
---

# Setup project

Converge one project on the state below.
Run from a checkout of this repo on a host that holds the project at `~/repos/<repo>`; a re-run changes only what is behind.
This skill names no stack: the project's stack setup writes everything stack-specific, for a web product [`setup-web-stack`](../setup-web-stack/SKILL.md).

## 1. Read

`git pull --rebase` here and in the checkout, then its `AGENTS.md`, `docs/agents/`, `skills-lock.json`, `.claude/settings.json`, `.github/workflows/` and package scripts.

## 2. Plugin

- `claude plugin marketplace list` names `pstack-claude`; otherwise `claude plugin marketplace add michael-denyer/pstack-claude`. A host managed from a dotfiles repo declares it there.
- `claude plugin install pstack@pstack-claude -s project` in the checkout, and `.claude/settings.json` is committed. Project scope only, so a brain session keeps its own skills.
- The version moves only through `claude plugin update pstack@pstack-claude`, run on purpose: read the port's `CHANGES.md` between the two versions first, then run `node <plugin root>/skills/poteto-mode/scripts/check-playbooks.mjs` in the checkout and fix every project playbook it flags in the same commit.
- `.claude/settings.json` also carries `"env": {"CLAUDE_CODE_ENABLE_TODO_TOOLS": "1"}`: Claude Code leaves its task tools out on current models, and pstack keeps each run's playbook checklist in them instead of a `todo.md` file.
- `.gitignore` ignores pstack's working files: `/todo.md`, `/decisions.tsv` and `/.audit/`.
- Every host that runs the project has `claude plugin install pstack@pstack-claude -s project` run once in its own checkout; the committed setting alone downloads nothing.
- The host has `gh` signed in, Bun (pstack's `watch-pr` and `orch` scripts) and `plugin-dev@claude-plugins-official` at user scope (the skill-authoring guidance pstack's `reflect`, `automate-me` and skill-authoring playbook hand work to). A host managed from a dotfiles repo declares the plugin there.
- `~/.claude/pstack-models.md` exists on the host, and the project's `AGENTS.md` ends with the line `@~/.claude/pstack-models.md`, so the sheet loads in the project's sessions only. Values are family names with an effort suffix (`fable @xhigh`); the `Agent` tool rejects a full `claude-*` id.
- `claude` has been started once in the checkout and its folder trust prompt and its prompt for the external include accepted, so an unattended start is not held by either. Unattended, both are the checkout's `hasTrustDialogAccepted` and `hasClaudeMdExternalIncludesApproved` set to `true` under `projects` in `~/.claude.json`, written while no session of that checkout runs.

## 3. Skills

The project pins stack skills only: the catalog entries its stack setup names, each by commit.
Pins from `mattpocock/skills` and from this repo are removed with their `.claude/skills` links (`npx skills remove <name> -y`).

```bash
npx skills add "<source>#<sha>" --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- Pass every `--skill <name>` as its own pair of arguments: with `-y`, a list the CLI cannot parse installs the whole source without an error.
- A skill locked at the pin (`ref` in `skills-lock.json`) is skipped; one at another commit, or with no `ref`, is removed and added again at the pin. `npx skills update` rewrites lock entries wrongly, so updates go through `add` and `remove` only.
- Layout: real directories under `.agents/skills/<name>`, a relative link `.claude/skills/<name>` → `../../.agents/skills/<name>`. The CLI writes no link and `remove` deletes one, so after every add: `mkdir -p .claude/skills && ln -sfn ../../.agents/skills/<name> .claude/skills/<name>`. `skills-lock.json` is committed with them.

## 4. Files

The templates are in [`templates/project/`](../../templates/project/).
Template prose reads the same in every project and is replaced on a re-run; a line that states a fact of this repo is the project's and is kept; no `<placeholder>` remains, each filled or its line deleted.

- `AGENTS.md` is the real file and `CLAUDE.md` a symlink to it. A lone real `CLAUDE.md` is renamed (`git mv`); two real files are shown to the owner, who picks. The sections "Rules for every session", "Must-read" and "Where things live" carry the template's text with the project's check command and must-read entries; the project's own sections follow them.
- `docs/agents/dev-loop.md` has the template's sections in the template's order. A stack with a setup skill runs it now to fill the check command, CI, running the app, worktrees, journeys and the design system; any other stack fills them from its own tooling.
- `PRODUCT.md`: what the product does, for whom, and the product rules a run must keep. A project without one gets the file with its title and the rules found under the next bullet.
- Not in a project: `CODING_STANDARDS.md`, `GLOSSARY.md`, `docs/adr/`, `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`, a bug issue template, skills other than the stack pins and the verification skill, and `AGENTS.md` sections on process (a gate, a conflict exit, test tiers, a lead). Each one present leaves in its own commit: a rule in it that a lint can enforce becomes that lint rule, a rule that still shapes behaviour becomes one `PRODUCT.md` sentence, the rest goes. A project with many such records gets that as its own run: list them in the report and stop short.

## 5. CI and repository

- `.github/workflows/check.yml` runs the check command on every pull request and on pushes to `main`; the stack setup writes it from its template, any other stack writes the equivalent. Values the check reads at build time are repository secrets, named in the report when only the owner holds them.
- Repository settings keep `main` linear under pstack's squash merges:

```bash
gh api -X PATCH repos/<owner>/<repo> -F allow_merge_commit=false -F allow_squash_merge=true -F allow_rebase_merge=true -F delete_branch_on_merge=true
```

- Labels `needs-triage`, `needs-info`, `ready-for-agent`, `needs-human` and `wontfix` exist.

## 6. Verification skill

The project has a verification skill (`.claude/skills/verify*`) pstack proves changes with on the real app.
Without one, run `/pstack:create-verification-skill` in the checkout, fed by "Running the app" in `docs/agents/dev-loop.md`, and commit what it writes.

## 7. Check

1. The check command is green on `main`. A red step moves out of the command into the "Pending checks" section of `docs/agents/dev-loop.md` until a run gets it green.
2. Commit on `main` and push.
3. A throwaway pull request from a one-line branch shows the `check` run; close it.

## Report

The plugin version and where it is enabled; skills added, re-pinned and removed; each file created, changed or removed with its commit; CI, repository settings and labels; pending checks; the verification skill; what only the owner can do (secrets, dashboard-only keys).
