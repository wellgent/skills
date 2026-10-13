# <Project name>

<What the product is and who uses it, in one or two lines.>

## Rules for every session

- **Check before report.** A session that changes files has `<check command>` green on its branch tip before it reports: run it yourself on that commit and quote its result.
  A subagent inside the session proves its diff with the lint, the typecheck and the test files the diff touches; the session's one full check covers every branch it merges.
  A session that changes no file runs no check.
- **Conflict exit.** Stop work on a ticket and report to the session that started you when the ticket, its tests or the spec disagree (say what disagrees with what), when the ticket needs a decision it does not hold, or when the work touches a hard-to-reverse thing the ticket does not name: stored-data shape or a migration, an external contract, money, authorization, a production delete.
  Size is never a reason. A conflict exit is a correct outcome, and the reply settles what changes.
- **Test tiers.**
  - A repro test handed to you with a bug ticket or a finding passes unchanged; a repro test you believe is wrong goes through the conflict exit.
  - An existing test changes freely when the ticket changes its behaviour.
    Your report names each test you deleted, each `.skip`, `.only`, `.todo` or `.fails` you added, each net loss of assertions and each loosened matcher, with the reason.
  - A new test is written first, at the seam the design record or the ticket names, with expected values copied as literals from the contract example or the bug report.
  - A journey test changes only in a ticket that changes that journey, and only that ticket runs it in its session; `flow gate` runs every journey test at each landing.
- **Checks.** Tightening a check is free.
  Loosening a shared check (an ignore entry, a disabled rule, a step removed from the check command, a lowered threshold) needs the ticket to name it or the lead's approval.
  An inline suppression carries its reason on the same line.
- **Standards.** `CODING_STANDARDS.md` holds the code rules and the test bar your work is reviewed against.
- **Production.** Sessions work on their own dev environment per [docs/agents/dev-loop.md](docs/agents/dev-loop.md).
  A production read or write is a request to the lead.
- **Landing.** `main` history stays linear: a branch lands by rebase onto `origin/main` and a fast-forward push, and landing a spec's branch is the lead's.

## Must-read

Read each file when its trigger matches your work, before you write code.

- <trigger> → `<path>`

## Where things live

- [GLOSSARY.md](GLOSSARY.md): the project's domain language. Use its terms in code, tests, tickets and commits.
- [CODING_STANDARDS.md](CODING_STANDARDS.md): code rules and the test bar.
- [docs/agents/dev-loop.md](docs/agents/dev-loop.md): the gate, worktrees, running the app, critical journeys, and the lenses and tools of Review, QA and Audit.
- `docs/adr/`: architecture decisions. An ADR is settled; a ticket that contradicts one is a conflict exit.
- [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md), [docs/agents/triage-labels.md](docs/agents/triage-labels.md): tracker mechanics and label strings.
- [docs/agents/domain.md](docs/agents/domain.md): how to read the glossary and the ADRs before exploring the code.
