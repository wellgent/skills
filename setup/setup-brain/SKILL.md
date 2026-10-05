---
name: setup-brain
description: Scaffold the development flow into a driving brain - flow config, labels, the lead's pinned skills, and a card, config entry and ledger directory per project. Idempotent; Readiness re-runs it.
argument-hint: "<path to the brain checkout> [<owner>/<repo> of a project to add or refresh]"
disable-model-invocation: true
---

# Setup brain

Bring a **driving brain** current with the flow: the repository the lead runs from.
Run from a checkout of this repo, `~/repos/wellgent-skills`; the argument is the brain's checkout (ask if missing) and, optionally, one project.
Every step converges on a state, so a re-run changes only what is behind.
What a brain must hold is in [`../requires.json`](../requires.json) under `brain`; `flow ready`, run in the brain, checks it.

## 1. Read the brain

- `git pull --rebase` in `~/repos/wellgent-skills` and in the brain (a brain without a remote skips it), then the brain's `AGENTS.md`: where project pages live, how it commits, which page conventions wrap a file.
- `flow.json`, `skills-lock.json` and the tracker (`git remote get-url origin`).
- `flow ready [<owner>/<repo>]`, run in the brain: its `behind` lines for `brain` and `host` are this run's work list. Run it again once `flow.json` exists, since most brain checks read it. `behind project` lines belong to [`setup-project`](../setup-project/SKILL.md).

## 2. Flow config

`flow.json` sits at the brain's root, from [`templates/brain/flow.json`](../../templates/brain/flow.json).

- Absent: copy the template, set `tracker` to the brain's `<owner>/<repo>` and `projects` to `{}`.
- Present: add each step the template has and the file lacks, with the template's entry, and the `harness` block when absent.
  An existing step entry is the brain's choice and stays as it is.

## 3. Labels

Create each label of `.brain.labels` the tracker lacks:

```bash
jq -r '.brain.labels[]' ~/repos/wellgent-skills/setup/requires.json | while read -r label; do
  gh label create "$label" --repo <tracker> 2>/dev/null || true
done
```

## 4. The lead's skills

The lead reads its third-party skills from the brain, pinned at the commit the source log names.
For each source under `.brain.skills`, in the brain's root:

```bash
npx skills add "<source>#$(flow sources pin <source>)" --agent codex --copy -y --skill <name> [--skill <name> ...]
```

- Pass every `--skill <name>` as its own pair of arguments: with `-y`, a list the CLI cannot parse installs the whole source without an error.
- A skill already locked at that commit (`ref` in `skills-lock.json`) is skipped.
- A skill locked at another commit, or with no `ref`, is removed (`npx skills remove <name> -y`) and added again at the pin. Updates go through `add` and `remove` only; `npx skills update` rewrites lock entries wrongly.
- Every other skill the brain already pins from a logged source moves to the same pin, and one the source no longer ships at that commit is removed.
- Layout afterwards: real directories under `.agents/skills/<name>`, a relative link `.claude/skills/<name>` → `../../.agents/skills/<name>` for each. The CLI writes no link and `remove` deletes one, so after every add: `mkdir -p .claude/skills && ln -sfn ../../.agents/skills/<name> .claude/skills/<name>`. Delete any directory the CLI wrote elsewhere.
- A `CONTEXT.md` the brain keeps for its own domain language is renamed to `GLOSSARY.md` (`git mv`), with every reference to it.

## 5. The project (when one is named)

1. **Card.** The card is a brain page from [`templates/brain/card.md`](../../templates/brain/card.md), filed where the brain's `AGENTS.md` puts project pages.
   The brain's own page conventions (frontmatter, links, citations) wrap the template's lines.
   An existing card gains the template lines it lacks.
   Fill every line from the brain's pages and the project's repo; a line only the client can answer (the client, the seed allowlist, a change to authority) is asked, never guessed.
2. **Config entry.** `projects["<owner>/<repo>"]` in `flow.json` holds `checkout` (the project's checkout on this host, `~` allowed) and `card` (the card's path in the brain). `iteration` is the lead's: a new entry has none, an existing one keeps its value.
3. **Ledger directory.** `ledger/<repo>/` exists and is tracked (a `.gitkeep` when empty). The iteration's ledger file and its two merged Audit reports live there.

## 6. Host

- `flow trust <brain checkout>`, and `flow trust <project checkout>` when a project is named, so neither harness stops a session there on a folder-trust prompt.
- `flow ready` names anything else the host lacks. Two links make the flow reachable, and a host that manages its home directory from a dotfiles repo declares them there:

```bash
ln -s ~/repos/wellgent-skills/lead ~/.claude/skills/lead
ln -s ~/repos/wellgent-skills/bin/flow ~/.local/bin/flow
```

## 7. Check

Commit and push the brain by its own rules.
Done when `flow ready [<owner>/<repo>]`, run in the brain afterwards, prints no `behind brain` line, and every remaining `behind host` line is reported with its fix.

## Report

What changed (config, labels, skills added, re-pinned and removed, card lines filled, ledger directory), the questions put to the client, and the final `flow ready` output.
