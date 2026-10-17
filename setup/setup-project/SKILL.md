---
name: setup-project
description: Bring a project onto pstack - the plugin enabled at project scope, stack skills pinned by commit, CI running the check command on every pull request, AGENTS.md and dev-loop.md from the templates, the verification skill, and the files an earlier workflow left. Idempotent; also where the plugin pin moves.
argument-hint: "<owner>/<repo>"
disable-model-invocation: true
---

# Setup project

Bring one project current with pstack.
Run from a checkout of this repo on a host that holds the project at `~/repos/<repo>`.
Every step converges on a state, so a re-run changes only what is behind.

This skill names no stack.
Everything stack-specific is written by the project's **stack setup**: for a web product, [`setup-web-stack`](../setup-web-stack/SKILL.md).

## 1. Read the project

- `git pull --rebase` here and in the checkout, then its `AGENTS.md`, `docs/agents/`, `skills-lock.json`, `.claude/settings.json`, `.github/workflows/` and package scripts.
- Note what an earlier workflow left, for step 5: skills that drove specs or verified the app, `CODING_STANDARDS.md`, `GLOSSARY.md`, `docs/adr/`, `docs/agents/issue-tracker.md`, `triage-labels.md` and `domain.md`, a bug issue template, and sections of `AGENTS.md` describing steps pstack now runs.

## 2. The plugin

- The marketplace is known at user scope on this host: `claude plugin marketplace list` names `pstack-claude`; otherwise `claude plugin marketplace add michael-denyer/pstack-claude`. A host managed from a dotfiles repo declares it there.
- In the checkout: `claude plugin install pstack@pstack-claude -s project`, which enables the plugin in the project's `.claude/settings.json`; that file is committed. Never at user scope, so a brain session keeps its own skills.
- **Version.** The plugin stays at the installed version until `claude plugin update pstack@pstack-claude` is run on purpose; third-party marketplaces do not auto-update. Before an update, read the port's `CHANGES.md` between the two versions; after it, run `node <plugin root>/skills/poteto-mode/scripts/check-playbooks.mjs` in the checkout and fix every project playbook it flags in the same commit.
- **Models.** `~/.claude/pstack-models.md` exists on the host and `~/.claude/CLAUDE.md` includes it with `@~/.claude/pstack-models.md`; a host managed from a dotfiles repo has both. Values are family names with an effort suffix (`fable @xhigh`); a full `claude-*` id is rejected.
- **Folder trust.** Start `claude` once in the checkout and accept the trust prompt, so an unattended start is not held by it.

## 3. Skills

A project pins only stack skills: the catalog entries its stack setup names, each by commit, and nothing from `mattpocock/skills` or from this repo.

```bash
npx skills add "<source>#<sha>" --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- Pass every `--skill <name>` as its own pair of arguments: with `-y`, a list the CLI cannot parse installs the whole source without an error.
- A skill locked at the pin (`ref` in `skills-lock.json`) is skipped. A skill at another commit, or with no `ref`, is removed (`npx skills remove <name> -y`) and added again at the pin; `npx skills update` rewrites lock entries wrongly, so updates go through `add` and `remove` only.
- Every pin from `mattpocock/skills`, and every pinned skill no catalog entry names, is removed with its `.claude/skills` link.
- Layout afterwards: real directories under `.agents/skills/<name>`, a relative link `.claude/skills/<name>` → `../../.agents/skills/<name>` for each. The CLI writes no link and `remove` deletes one, so after every add: `mkdir -p .claude/skills && ln -sfn ../../.agents/skills/<name> .claude/skills/<name>`. `skills-lock.json` is committed with them.

## 4. Project docs

The templates are in [`templates/project/`](../../templates/project/).
The template's prose reads the same in every project and is replaced on a re-run; a line that states a fact of this repo is the project's and is kept.
No `<placeholder>` is left: each is filled, or its line deleted when it does not apply.

- **`AGENTS.md`** is the real file and `CLAUDE.md` a symlink to it. A lone real `CLAUDE.md` is renamed (`git mv`); when both are real files, show the owner the difference and ask. The sections "Rules for every session", "Must-read" and "Where things live" carry the template's text with the project's check command and must-read entries; the project's own sections follow them.
- **`docs/agents/dev-loop.md`** has the template's sections in the template's order. For a stack with a setup skill, run it now: it fills the check command, CI, running the app, worktrees, journeys and the design system. For any other stack, fill them from the project's own tooling.
- **`PRODUCT.md`** exists: what the product does and for whom, and the product rules a run must keep. A project without one gets the file with its title and a line per rule found in the earlier docs (step 5).

## 5. What an earlier workflow left

Each item leaves in its own commit, named in the report:

- Skills that drove specs or verified the app: `git rm -r` the directory and its link, once "Running the app" in `docs/agents/dev-loop.md` holds whatever of their launch, sign-in and drive instructions still applies.
- `CODING_STANDARDS.md`: a rule a lint rule can enforce becomes that lint rule in the same commit; the rest is deleted. A rule that recurs as a mistake later comes back through pstack's `/correct`.
- `GLOSSARY.md` and `docs/adr/`: a rule in them that still shapes behaviour moves into `PRODUCT.md` as one sentence; then the files are deleted. A project with many records gets this as its own run: list them in the report and stop short.
- `docs/agents/issue-tracker.md`, `triage-labels.md`, `domain.md`, the bug issue template: deleted.
- `AGENTS.md` sections that describe a step pstack now runs (a conflict exit, test tiers, a gate, a lead): deleted.

## 6. CI and the repository

- `.github/workflows/check.yml` runs the check command on every pull request and on pushes to `main`; the stack setup writes it from its own template, any other stack writes the equivalent. Secrets the check needs (a build-time backend URL) are repository secrets, named in the report.
- Repository settings: squash and rebase merging on, merge commits off, head branches deleted on merge, so `main` stays linear under pstack's squash merges:

```bash
gh api -X PATCH repos/<owner>/<repo> -F allow_merge_commit=false -F allow_squash_merge=true -F allow_rebase_merge=true -F delete_branch_on_merge=true
```

- Labels: `needs-triage`, `needs-info`, `ready-for-agent`, `needs-human`, `wontfix`, created when missing.

## 7. Verification skill

pstack proves changes on the real app through a project verification skill.
When the project has none (`.claude/skills/verify*`), run `/pstack:create-verification-skill` in the checkout, fed by "Running the app" in `docs/agents/dev-loop.md`, and commit what it writes.

## 8. Check

1. Run the check command on `main`. A step that is red moves out of the command into the "Pending checks" section of `docs/agents/dev-loop.md` until a run gets it green.
2. Commit on `main` and push.
3. Open a throwaway pull request from a one-line branch and watch the `check` run appear on it; close it.

## Report

The plugin version and where it is enabled; skills added, re-pinned and removed; each doc created or changed; each item of step 5 with its commit; CI, repository settings and labels; pending checks; the verification skill; anything only the owner can do (secrets, dashboard-only keys).
