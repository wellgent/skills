# <Project name>

<What the product is and who uses it, in one or two lines.>

## Rules for every session

- **Check before report.** `<check command>` is green on your branch tip before you report work as done or merge a branch.
  Run it yourself on that commit and quote its result.
- **Conflict exit.** When a ticket, its tests or the spec disagree, stop work on that ticket and report the disagreement to the session that started you: what disagrees with what.
  A conflict exit is a correct outcome, and the reply settles which side changes.
- **Test tiers.**
  - A repro test handed to you with a bug ticket or a finding passes unchanged; a repro test you believe is wrong goes through the conflict exit.
  - An existing test changes freely when the ticket changes its behaviour.
    Your report names each test you deleted, each `.skip`, `.only`, `.todo` or `.fails` you added, each net loss of assertions and each loosened matcher, with the reason.
  - A new test is written first, at the seam the design record or the ticket names, with expected values copied as literals from the contract example or the bug report.
  - A journey test changes only in a ticket that changes that journey, and only that ticket runs it.
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
