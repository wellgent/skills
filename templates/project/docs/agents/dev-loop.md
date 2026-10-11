# Dev loop: project declarations

What the development flow reads about this project.
The flow's stage skills name no stack; every stack fact, lens and tool they use is declared here.
Rules for every session are in [AGENTS.md](../../AGENTS.md); code rules and the test bar are in [CODING_STANDARDS.md](../../CODING_STANDARDS.md).

## Gate

`flow gate` reads these lines at every landing.

- **Check command:** `<check command>`
- **Journey tests:** `<journey tests command>`
- **Protected paths:** `<glob>`, `<glob>`
- **Surface paths:** `<glob>`, `<glob>`
- **Prose paths:** `<glob>`, `<glob>`

The check command blocks on every step it runs: <the steps, in order>.
The journey tests, when the project has critical journeys, run in every gate, once per landing.
The protected paths extend the flow's default list of check-defining files.
The surface and prose paths decide the diff class the gate prints: a diff whose every file is a prose path is prose only (no Review, no QA), a diff that touches a surface path gets Review and QA, any other gets Review.
A surface path is one whose change can reach what a user sees or does; a prose path holds no code and no test.
A glob matches a file's full path or its name, and `*` spans directories.

## Critical journeys

At most five, approved by the client; raising the number is the client's decision.
Each journey has one browser test.
Beyond these, Build writes a browser test only where a contract example names behaviour only a browser shows (navigation, history, scroll, focus).

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

The source of the health check: `flow land` runs these commands on every landed commit and appends the numbers to the ledger as the health check row.
One line per measure or group of measures, with one command per measure in the same order; each command exits 0 and prints its number as the last line of its stdout.
The nine named measures are required; a project adds its own below them.

- `unused_code`: `<command>`
- `duplication_source_pct`: `<command>`
- `duplication_tests_pct`: `<command>`
- `dependency_violations`: `<command>`
- `suppressions`: `<command>`
- `tests`, `test_seconds`: `<command>`, `<command>`
- `source_lines`, `test_lines`: `<command>`, `<command>`
- `<project measure>`: `<command>`

## Pending checks

Blocking checks still red on `main`, each joining the check command once green and counted by a scanner pass measure until then:

- <check> - <the cleanup spec that gets it green>

## Design system

- **Design-system lint:** `<command>`
- **Design scanner:** `<command>`

## Deviations

<Each departure from the stack doctrine, with its reason.>
