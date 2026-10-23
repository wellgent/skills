# Project docs

Every project carries the same docs in the same places.
Each doc answers one question for one reader, each fact lives in one doc and the others link to it, and each doc has something that keeps it true.
A markdown file outside this set is a deviation: `scripts/check-docs` fails on it inside the check command, and [`setup-project`](../setup/setup-project/SKILL.md) converges the project back.

## The set

- **`README.md`**, for a person who opens the repository: what the product is, its Components, the tech stack, getting started on a new machine, and a link to `AGENTS.md` for working on it.
  It restates no rule another doc states, and links to `docs/agents/dev-loop.md` for environments and deployments.
- **`AGENTS.md`**, loaded by every session, with `CLAUDE.md` a symlink to it: "Rules for every session", "Must-read" and "Where things live" from [the template](../templates/project/AGENTS.md), then the project's rules that most sessions need and the rule table `/correct` keeps.
  A rule only work in one area needs lives in that area's topic guide.
- **`PRODUCT.md`**: what the product does, for whom, and the product rules a change must keep.
- **`GLOSSARY.md`**: the domain terms, each with the terms to avoid for it, and no implementation detail.
  Code, tests and copy name things by it.
- **`DESIGN.md`** with its sidecar `.impeccable/design.json`, in every project with screens: the design system and the kit map.
  With `PRODUCT.md` it is the whole design context impeccable reads; a design direction, a screen export or a style guide is folded into it.
- **`docs/agents/dev-loop.md`**: the check, sign-off, landing, verification, agents, environments, worktrees, running the app and the critical journeys, in [the template's](../templates/project/docs/agents/dev-loop.md) sections.
- **`docs/agents/<topic>.md`**, a topic guide: what work in one area needs, such as driving the app, a browser test harness or how auth works.
  `AGENTS.md` names each one in a Must-read trigger.
- **`docs/adr/NNNN-<decision>.md`**: a decision that is hard to reverse, surprising without context and the result of a real trade-off.
  It states the decision in force: when the decision changes, the record is rewritten or deleted, and git keeps what it said before.
  The folder appears with the first such decision; the `AGENTS.md` line naming it is there from the start.

## Outside the set

- Not docs, and not checked: `.agents/` (pinned skills and `.agents/playbooks/`), `.claude/`, and the paths the "Not docs" section of `docs/agents/dev-loop.md` lists, which are product content written in markdown or vendor-generated files.
- Never in a project, each with its home:
  - research, plans, specs and status: the brain and its tracker;
  - history, changelogs and what a doc said before: git;
  - process and conventions, including tracker, triage and domain docs and coding-standards files: this repo and pstack;
  - a rule a lint can enforce: that lint rule;
  - a map of the schema or the code: the code itself.

## Writing

- Present tense, current truth only.
- A doc states what the code cannot say, and never restates the code.
- A number that mirrors a constant has a test that fails when the two differ, or the doc leaves it out.
- The why of a decision lives in its ADR when it passes the three tests, in a code comment beside a constraint local to one place, and otherwise in the pull request body, which the squash merge keeps on `main`.
- A change updates every doc it makes untrue in the same pull request.
- A brain session writes nothing into a project: a term or decision a brain settles goes into the run request, and the run writes it into the project's doc.
