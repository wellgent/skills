# Dev loop: project declarations

What a session reads about running this project.
Stack facts only; the process is pstack's.

## Check

- **Check command:** `<check command>`
- **CI:** `.github/workflows/check.yml` runs it on every pull request and on pushes to `main`.

The check command blocks on every step it runs: <the steps, in order>.

## Critical journeys

At most five, approved by the product's owner.
Each journey has one browser test; the verification skill runs them before a pull request opens, and CI runs them where the stack setup wired a deployment for it.

- <journey, as the user's goal> → `<test file>`
- **Journey tests:** `<command that runs them all>`

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
- **Prototype branches:** <how a `prototype/*` branch reaches its preview, and where its option links are printed>.

## Design system

- **Design-system lint:** `<command>`
- **Design scanner:** `<command>`

## Pending checks

Blocking checks still red on `main`, each joining the check command once green:

- <check> - <what gets it green>

## Deviations

<Each departure from the stack doctrine, with its reason.>
