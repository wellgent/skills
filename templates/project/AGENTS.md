# <Project name>

<What the product is and who uses it, in one or two lines.>

## Rules for every session

- **Check before push.** A session that changes files signs its commit off with `scripts/check` before its PR is reviewed and quotes its result.
  `scripts/check` is the one CI: it runs the frozen install, `<check command>` and the journey tests on the worktree's own backend, then pushes the head and posts the `check` commit status on it.
  No GitHub Actions run for this project.
- **Verification.** A verifier reruns no suite: it drives the changed surface, reads the diff and the test changes, and takes the head's `check` status as an input.
- **Landing.** Work lands only through `scripts/land <pr>`, which squash-merges a PR onto `main` when its exact head carries a passing `check`; `main` stays linear.
  A run merges only under the landing authority its prompt grants, restacks only on a real conflict and never waits on a production deploy.
  When `scripts/check` cannot run (exit 2), landing pauses and the run posts a stop.
- **Agents.** No agent sleeps or polls inside its own turn, every spawn passes `model`, and a stop runs leaves first; [docs/agents/dev-loop.md](docs/agents/dev-loop.md) under "Agents" has the full rules.
- **Tests** run only through the package scripts, never the test runner directly: the scripts take one of the host's heavy-run slots through `scripts/slot`.
- **Deletes.** A delete through a variable is written `rm -f "${VAR:?}"/...`, or with a literal path.
- **Cleanup.** Before a run posts its note, it tears down every worktree and scratch tree it created with `<worktree teardown command>`, so `git worktree list` shows only the main checkout.
- **Production.** Sessions work on their own dev environment per [docs/agents/dev-loop.md](docs/agents/dev-loop.md). A production read or write, a deploy, a data deletion and a message to a user are stops: each goes to the request issue, or to the person in the chat, and waits for the answer.

## Must-read

Read each file when its trigger matches your work, before you write code.

- <trigger> → `<path>`

## Where things live

- [PRODUCT.md](PRODUCT.md): what the product does, for whom, and the product rules a change must keep.
- [DESIGN.md](DESIGN.md): the design system and the kit map.
- [docs/agents/dev-loop.md](docs/agents/dev-loop.md): the check command, the sign-off and landing rules, verification and previews, the agent rules, worktrees, running the app and the critical journeys.
- `.agents/playbooks/`: this project's playbooks extending pstack's bundled ones.

@~/.claude/pstack-models.md
