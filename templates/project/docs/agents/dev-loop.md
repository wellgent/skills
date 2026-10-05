# Dev loop: project declarations

What the development flow reads about this project.
The flow's stage skills name no stack; every stack fact, lens and tool they use is declared here.
Rules for every session are in [AGENTS.md](../../AGENTS.md); code rules and the test bar are in [CODING_STANDARDS.md](../../CODING_STANDARDS.md).

## Gate

`flow gate` reads these three lines.

- **Check command:** `<check command>`
- **Journey tests:** `<journey tests command>`
- **Protected paths:** `<glob>`, `<glob>`

The check command blocks on every step it runs: <the steps, in order>.
The journey tests run once per spec, in the gate.
The protected paths extend the flow's default list of check-defining files.

## Critical journeys

At most five, approved by the client; raising the number is the client's decision.
Each journey has one browser test, and Build writes no other browser tests.

- <journey, as the user's goal> → `<test file>`

## Worktrees

Every branch is worked in its own worktree with its own dev environment, so parallel sessions share no server, port or data.

- **Set up:** `<worktree setup command>`, run once in a new worktree. <What it creates: dependencies, env file, own dev backend, seed data.>
- **Tear down:** `<worktree teardown command>`, before the worktree is removed.

## Running the app

- **Start:** `<start command>`. <Where the port comes from and how to read the URL.>
- **Stop:** `<stop command>`.
- **Dev sign-in:** <how a session signs in on a dev environment without a real inbox or phone.>
- **Seeded test identities:** <identity> - <role and the records the seed gives it>.
- **Reset:** `<command that returns the dev environment to the seed>`.
- **Prototype branches:** <how a `prototype/*` branch reaches the prototype host, and where its option links are printed>.

## Review lenses

Each lens runs when its trigger matches the diff.

- <trigger on the diff> → `<skill>`

## QA tools

- `<tool>`: <what QA uses it for>.

Named checks:

- <a check QA runs on every pass, with its pass condition>

## Audit lenses

Each lens names the review it joins: the defect review or the architecture review.

- <review> → `<skill>`

## Scanner pass

One command per measure of the ledger's `scan` row.
The lead runs the pass on `main` and records the numbers with `flow ledger scan`.

- `unused_code`: `<command>`
- `duplication_source_pct`: `<command>`
- `duplication_tests_pct`: `<command>`
- `dependency_violations`: `<command>`
- `suppressions`: `<command>`
- `tests`, `test_seconds`: `<command>`
- `source_lines`, `test_lines`: `<command>`
- `<project measure>`: `<command>`

Pending checks, blocking checks still red on `main` that join the check command once green:

- <check> - <the cleanup spec that gets it green>

## Design system

- **Design-system lint:** `<command>`
- **Design scanner:** `<command>`

## Deviations

<Each departure from the stack doctrine, with its reason.>
