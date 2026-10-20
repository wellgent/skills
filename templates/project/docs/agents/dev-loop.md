# Dev loop: project declarations

What a session reads about running this project: the stack facts, and the rules every run follows whether `/operate` started it or a person did.
The rest of the process is pstack's.

## Check

- **Check command:** `<check command>`

The check command blocks on every step it runs: <the steps, in order>.

- **Slots:** every test run takes one of the host's heavy-run slots: the test scripts, the check command and every browser suite run through `scripts/slot`, which waits for a free slot and holds it while the command runs.
  A test run inside a run that already holds a slot, such as the tests inside the check command, uses that slot.
  The cap is `HEAVY_RUN_SLOTS` from the environment, 2 when unset.
  The slots live in `${XDG_STATE_HOME:-$HOME/.local/state}/heavy-runs/`, shared by every project on the host.
  The slots alone bound memory: each run takes the test runner's default worker count.
- **Tests run only through the package scripts**, never the test runner directly, so every run takes a slot.

## Sign-off

`scripts/check` is the one CI.
No GitHub Actions run for this project.

- **Run it** in the PR branch's worktree on the exact commit to sign off.
  It refuses a dirty worktree, `main` and a detached HEAD.
- **What it runs:** under one heavy-run slot, the frozen install, the check command, <what it prepares on the worktree's own backend>, and the journey tests.
- **On a pass** it pushes HEAD to `origin/<branch>` when the remote branch does not already point at it, and posts the commit status `check` on that SHA, with the host and the duration as its description.
  On a failure it posts nothing.
- **Exit codes:** 0 passed and posted, 1 refused or failed, with the failing step named.
  2 could not run: no `gh` auth, the backend would not start, or no slot dir.
  Exit 2 is infrastructure, not code.
- **Check before push.** The implementer runs `scripts/check` on its commit before the PR is reviewed, and `scripts/check` is what pushes a signed-off head.
  A head pushed any other way has no `check` status and cannot land.
- **Dry run.** `scripts/check --dry` runs the same steps on any checked-out commit, a detached HEAD or `main` included, and pushes and posts nothing.
  `/operate`'s Ready runs it in a fresh worktree as the smoke test before a run starts.

## Landing

- **Only through `scripts/land <pr>`.** It refuses a PR that is not open or does not target `main` (exit 1) and a head SHA without a passing `check` status (exit 3).
  It squash-merges with `--match-head-commit` on that SHA and reads the merge back from `origin/main`.
  When `gh pr merge` exits non-zero, it reads the PR back and lands only a PR that GitHub shows merged on that SHA.
- **No up-to-date requirement.** A PR merges on its own green `check` and need not be rebased on the latest `main`.
  <Whether the repository ruleset also requires the `check` status on `main`, or why the plan does not allow it.>
- **Restack only on a real conflict.** A restack that resolves a conflict sends the resolved hunks back to the verifier, which checks only those, and the new head gets its own `scripts/check`.
- **No wait on a production deploy.** <What a push to `main` deploys>, and landing never waits on it.
  A failed production deploy is reported and fixed as the run's next PR.
- **When `scripts/check` cannot run** (exit 2), landing pauses and the run posts a stop on its request.
  Building and verifying continue.
- **The final tree is checked.** After a run's last landing, the check command and the journey tests run on the `main` head, since each head was signed off on its own base.

## Verification

- **The verifier reruns no suite.** It drives the app on the changed surface with the verification skill, reads the diff, checks the test changes, and takes the head's `check` status as an input.
- **Previews.** <What the host builds from git pushes, and how a PR labelled `preview` gets its preview: the command, where the URL is posted, and the preview backend it gets with the PR's own functions and the seed.>
  A change to layout, look and feel or functionality waits for the product's owner to review its preview before it lands.
  A bug fix, or a fix that makes the UI match the project's design records, lands on its verifier's pass, labelled `preview`, and the run's note lists it.
  The verifier's screenshots are its own evidence: they stay in its evidence directory and are never committed, pushed or posted.

## Agents

- **No agent sleeps or polls inside its own turn.** Waits are background scripts the main session starts, and the main session waits only on merge read-backs through pstack's watcher.
- **A delegate ends its turn** once its PR is pushed or its verdict posted.
- **Every spawn passes `model` explicitly**, and every review brief says whether its reviewer may spawn agents.
  Agents nest at most two levels deep (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` in `.claude/settings.json`).
- **Fix rounds** on a verifier's defect list, restacks and one-site mechanical moves run one effort step below the role sheet.
- **A stop runs leaves first:** `ListAgents`, stop every descendant, then the parent, then `ListAgents` again until it is empty.
- **Deletes.** A delete through a variable is written `rm -f "${VAR:?}"/...`, or with a literal path, so Claude Code's possibly-empty-variable prompt never holds an unattended session.

## Critical journeys

At most five, approved by the product's owner.
Each journey has one browser test, and `scripts/check` runs them all.

- <journey, as the user's goal> → `<test file>`
- **Journey tests:** `<command that runs them all>`

## Worktrees

Every branch is worked in its own worktree with its own dev environment, so parallel sessions share no server, port or data.

- **Set up:** `<worktree setup command>`, run once in a new linked worktree. <What it creates: dependencies, env file, own dev backend, seed data.>
- **Tear down:** `<worktree teardown command>`, run inside the worktree once its work is pushed. <What it stops and removes.>
- **A run cleans up after itself.** Before a run posts its note, it tears down every worktree and scratch tree it created, so `git worktree list` shows only the main checkout and no run directory remains.
- **Main checkout:** <the backend the main checkout keeps for the human's interactive work>.

## Host tools

What a run needs on its host beyond the checkout, each with the check `/operate`'s Ready runs (exit 0 when ready):

- **<tool>:** `<check command>`

## Crons and seed data

- **Crons run in production only.** <The switch, where it is off, and when a change takes effect.>
- **The seed supplies what a cron would produce:** <what the seed stores in their place>.

## Running the app

- **Start:** `<start command>`. <Where the port comes from and how to read the URL.>
- **Stop:** `<stop command>`.
- **Dev sign-in:** <how a session signs in on a dev environment without a real inbox or phone.>
- **Seeded test identities:** <identity> - <role and the records the seed gives it>.
- **Reset:** `<command that returns the dev environment to the seed>`.

## Design system

- **Design-system lint:** `<command>`
- **Design scanner:** `<command>`

## Pending checks

Blocking checks still red on `main`, each joining the check command once green:

- <check> - <what gets it green>

## Deviations

<Each departure from the stack doctrine, with its reason.>
