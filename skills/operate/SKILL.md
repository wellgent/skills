---
name: operate
description: Run a brain request on a project through pstack - read the request issue, bring the brain, the project and the host up to date and prove the project's tools (Ready), write the run prompt, start the run in herdr with landing authority, then watch the request, answer the run's plan and stops or bring them to the requester, pause the run near the weekly usage limit, check its note and review the run. Use for /operate <issue>, which also resumes a paused run, and /operate cost <session> to price a finished run.
argument-hint: "<request issue> | cost <session id | latest <checkout>>"
disable-model-invocation: true
---

# Operate

The operator between a brain and pstack: a **run request** on the brain's tracker goes in, a pstack run on the project comes out, and the run's note comes back to the request.
Run from the brain's checkout on any host that holds the project at `~/repos/<repo>`.
pstack owns everything inside the run, under the rules in the project's own files; this skill writes the prompt, starts the session, and stays the run's operator until its note is handled: every stop the run posts reaches this session first, and the requester hears only the calls that are theirs.
Every comment the operator posts opens with `**Operator:**`, or with `**Operator, <requester>'s call:**` when it relays the requester's answer, since the run, the operator and the requester may share one GitHub account.
The operator's answers, `scope:` comments and catch-ups hold only calls about this one run; a rule every run should follow belongs in host setup or the project template, and goes to the requester as that proposal.

## The request

One open issue on the brain's tracker labelled `run`, in the shape of [`request.md`](request.md): the repo as `<owner>/<repo>`, then Goal, Done check, Proof, Known and Constraints.
A request missing a section gets one comment naming the missing sections, and no run starts.
The body is frozen once a run starts: every change, from the operator or the requester, is a comment starting `scope:` (see Scope changes).

## 1. Read the request

`gh issue view <n> --json title,body,author,url,labels,comments` on the brain's tracker (`git remote get-url origin` in the brain).
Every section present, the label `run` present (add it when missing), and no `run:` comment from the operator on the issue, which marks a run already started.
The one exception is a paused run: when the newest `run:` comment is followed by a comment from the run headed `Hand-back`, this is its resume (see Resume).

## 2. Check the project

In `~/repos/<repo>`: `git fetch`, a clean tree on the main branch with no commit its remote lacks, `pstack@pstack-claude` enabled in `.claude/settings.json`, `scripts/land` present, and `gh auth status` green.
Anything missing stops the run with its fix; a project not set up gets `setup-project`.

## 3. Ready

A run starts on the newest `operate`, the newest pstack release, the newest stack skill pins and project docs on the current templates, with the project's tools proven on this host.
`ready` (below) fast-forwards a checkout that is only behind, so the brain and the project start at their remote heads.

1. `bash <this skill's directory>/scripts/sync-brain <brain checkout>` pins `operate` at the newest wellgent/skills commit that touches it, with the run request template and the `run` label. When it moved the pin, read the new `SKILL.md` and carry on from this step under it.
2. `bash <this skill's directory>/scripts/ready <owner>/<repo>` from the brain: the brain and the project at their remote heads, this skill's own tools, the weekly usage as a warning that never blocks, each check under "Host tools" in the project's `docs/agents/dev-loop.md`, the host's pstack version and every stack pin against upstream. Exit 1 is blocked, exit 3 is behind.
3. `setup-project` with `latest` on the project, from the wellgent/skills checkout at `~/repos/wellgent-skills` pulled first: pstack at the version its marketplace serves on this host (a host change, no commit), every stack pin at its source's newest commit, and the project's docs on the current templates. A change to the repository goes on a branch `ready/<n>` as one PR, signed off with `scripts/check` in its own worktree, and lands through `scripts/land`; its sign-off is the smoke test, and Ready ends only once `scripts/production-live` prints its merge commit, since every landing of the run waits for production to run `main`'s tip. A production deploy of it that fails stops Ready: read its build log for the cause, and a redeploy of that commit is the requester's call.
4. Without a change, `bash <this skill's directory>/scripts/ready --smoke <owner>/<repo>`: a fresh worktree of `origin/main`, its Set up command, `scripts/check --dry`, then its Tear down.

Comment on the request `**Operator:** ready: <hostname>, main at <sha>`, then what moved (the `operate` pin, pstack, each pin, the docs, with old and new) and the smoke's duration; the run starts from that commit.
Anything that fails in Ready, a blocked check, a failed update or a red smoke, stops here: no run starts. Leave the failed PR open, catch the requester up in `/ketchup`'s voice with what failed and a recommendation, assign them, and wait for their call.
On a resume, Ready moves nothing: run `ready --smoke`, report what is behind in the `ready:` comment, and start only when it passes.

## 4. Write the prompt

Fill [`prompt.md`](prompt.md) with the request's URL, and its five sections copied as written; save it as `~/.local/state/operate/<repo>-<n>.md`.
On a resume, the resume line takes the URL of the first `Hand-back` comment; otherwise it goes.
Its run lines stay as the template has them.

## 5. Start the run

```bash
bash <this skill's directory>/scripts/start <owner>/<repo> <n> ~/.local/state/operate/<repo>-<n>.md
```

It opens a tab in the project checkout inside the herdr workspace `<repo>-operate`, starts Claude Code there with `/pstack:poteto-mode` pointed at the prompt file, names the session `op-<repo>-<n>`, and prints the session name and pane.
A start that stops at a startup prompt (folder trust, a login) is answered in that pane: `herdr agent read <session> --source visible` shows it.

## 6. Record and watch

Comment on the request: `**Operator:** run: <session> started on <hostname> at <UTC time>`, or on a resume `**Operator:** run: <session> resumed on <hostname> at <UTC time> from <hand-back URL>`.
Start the watch in the background from the `ready:` comment's URL, then end the turn: a run can post its plan before the `run:` comment, and the watch then prints both.

```bash
bash <this skill's directory>/scripts/watch <n> <ready: comment URL>
```

It returns with one reason, printed:

- **Exit 0**: every comment newer than the given one (default: the newest now), skipping the operator's own, once the newest has been quiet for 90 seconds, so a stop and its amendment arrive together. Handle each: the plan, a stop, a confirmation, the hand-back or the note.
- **Exit 3**: the run's session is gone with no new comment (see The note).
- **Exit 4**: this host's weekly usage is at 90% or above: pause the run (see Pause).
- **Exit 5**: the run's session has done nothing for 30 minutes with no new comment, while nobody is assigned on the request. Read its pane (`herdr agent read <session> --source visible`) and act on what holds it: a five-hour usage limit waits for its reset, then the run is told in its pane to carry on; anything else is handled like a stop. A pane that names a unit as still running answers nothing: check how long that unit has been silent, and tell the run to look at it.
- **Exit 6**: this host's weekly usage has been unreadable for 30 minutes. Read the weekly percentage from the run's status line in its pane; at 90% or above pause the run, otherwise restart the watch.

Restart it after each return, from the newest comment id it printed, or from the id it started from when it printed none, until the note is handled. Never restart it from a comment this session posted: the watch skips the operator's own comments, and a run comment posted just before the operator's would go unread.
This session stays open for the run's whole length; a closed operator leaves the run's stops unread.

## Talking to the run

The run reads the request only while it waits on a stop, so every message to it goes to its pane, which is `herdr agent get <session>`'s `.result.agent.pane_id`:

```bash
herdr pane send-text <pane> "<message>"
herdr pane send-keys <pane> Enter
```

## The plan

The run's first stop is its plan, posted before any implementer starts.
Check it against the request: every item serves the done check within the constraints.
Answer in one comment with a go, or with a cut naming what leaves the plan, then tell the run as for a stop.
Only an out-of-scope ask in the plan reaches the requester, escalated as in Stops.

## Stops

A stop is a comment from the run with questions it waits on, each with the default it applies when nobody answers.
Sort every question:

- **Answer it** when the request, the brain (the map the request came from, decisions on subject pages) or the project's own records settle it, or when it is reversible and the run's default is sound.
- **Escalate it** when it is a product or preference call only the requester can make, the review of a change to layout, look and feel or functionality on its preview, an irreversible action the constraints do not authorize, or work outside what the request asks for. A bug fix, or a fix that makes the UI match the project's design records, is not escalated: it lands on its verifier's pass.

A review on a preview goes to the requester as the preview URL and what changed, never as screenshots.
To escalate, catch the requester up in this session in `/ketchup`'s voice: how many calls wait on them, then each call with your recommendation and why, and what the run does without an answer.
Assign the requester on the request, so the call shows in their open `run` issues, and wait for their answer.

Answer the stop in one comment on the request covering every question, the requester's calls in their substance, and remove the assignee.
Then tell the run: "Your stop on <request URL> is answered: read it now."

## needs-human

`needs-human` on a project's tracker marks a call or task that stays with the requester after the run, or someday; open `needs-human` issues across projects are the requester's queue.
Anything that can be settled within the run's scope is a stop taken to the requester in this session, never a `needs-human` issue.
The operator files one only for what is on the requester after the run, with that call written on the issue, and never closes or edits one.

## Scope changes

A change to what the run does, from the requester or the operator's own reading, is one comment on the request starting `scope:`, stating the change; the body stays as it was.
The run treats it as an answered stop; tell it: "A `scope:` comment on <request URL> changes the run: read it now."
A `scope:` comment the requester posts gets the same message.

## Partial stop

To stop part of the run (a track, a review, a set of agents), name it in the run's pane: "Stop <what> now, leaves first, and confirm on <request URL>."
The run's confirmation comes back through the watch; a part still running after it gets named again.

## Pause

At watch exit 4 the run pauses through pstack's Pause safely; a five-hour limit never pauses a run.

1. Tell the run: "Weekly usage is at <percent>%: pause the run now and post the hand-back on <request URL>." Restart the watch with `WATCH_WEEKLY_LIMIT=off` until the hand-back is in.
2. Check the request holds everything a resume needs, with paths relative to `$HOME`: the decision log, the `Hand-back` comment with the resume note and the run's working files, and every branch it names on the remote. Ask the run in its pane for whatever is missing; nothing a resume needs stays only on this host.
3. End the run's session with `/exit` in its pane.
4. Catch the requester up in `/ketchup`'s voice: the run is paused, what it landed and what is open, and a recommended host and time to resume, from the weekly reset that `bash <this skill's directory>/scripts/usage` prints and any other host holding the project with usage to spare. Assign the requester on the request.

## Resume

The requester picks the host and time.
`/operate <issue>` on that host finds the hand-back at step 1 and starts a new run from it, under the same request, done check and `scope:` comments, through the same steps; the watch and everything after it run as for any run.

## The note

The run ends with its decision log and then its `/ketchup` note on the request.
Check the note's claims against the project: the pull requests it names are merged, and the done check's commands that run on this host pass on the main branch, with the check and the journeys through `bash <this skill's directory>/scripts/ready --smoke <owner>/<repo>`, since the journeys need the worktree backend and port that `scripts/check` gives them.
Check the run cleaned up: `git worktree list` in the checkout shows only the main checkout, `git branch` shows no local branch of a pull request the run landed, and no worktree, scratch tree, evidence directory or log the run created is left on the host; the project's teardown removes any worktree that remains, and the operator deletes the rest. Nothing the run uploaded for evidence (a gist, an attachment) is left either.
Price the run session and this session with `scripts/cost` (see Cost), then review the run (see Run review).
Then catch the requester up in `/ketchup`'s voice: what the check found, both totals, what the review fixed, and the review's calls as numbered questions, each with a recommendation. Assign them on the request; closing it is their acceptance, and their answers to the calls are applied before it closes.
A watch exit 3 means the run ended without a note: read its pane or transcript, tell the requester what is known, and assign them.

## Run review

Every run ends with a review from outside it, so each run leaves the protocol and the setup better than it found them.

1. **Read the run as evidence:** the decision log, the trail review's flags, the deviations the note lists, every stop and how it was answered, the `ready:` comment, cost, and any host load or usage limit the log records.
2. **Judge it against the protocol:** Ready, the plan stop, units outside the approved plan, stop defaults, the review rule, `needs-human`, the final-tree check, cleanup and cost. For each, it held or it did not, with the evidence.
3. **Sort every finding:**
   - **Fix now**, with no ask, when it repairs setup code or makes it match a rule already decided: route the run's setup changes as The setup says, port them to wellgent/skills, and re-pin with `sync-brain`.
   - **A call for the requester** when it adds or changes a rule, a budget, a model choice or a tool: the run lines, stop rules, slots, models, a candidate tool. Apply it once answered.
   - **Project work** for a later run: a `scope:` addition if the requester wants it now, otherwise a line for the next request.
   - **No change**, with the reason.
4. **Post one `Run review` comment** on the request: what held, what did not, what was fixed with its commits, the calls, and the run's numbers (cost per PR, PRs landed, stops and how many reached the requester, deviations, wall time) beside those of the last closed `run` request's review.

## The setup

A project's run machinery is not the project's own: it comes from wellgent/skills, and a fix to it belongs there first.

- `AGENTS.md`, `docs/agents/dev-loop.md`, `scripts/land` and `scripts/slot` come from `templates/project/`, written by `setup-project`.
- `scripts/check`, `scripts/dev-server.sh`, `scripts/worktree-setup.sh`, `scripts/worktree-teardown.sh`, `scripts/host-claims.sh`, `scripts/vercel-ignore.sh`, `scripts/preview`, `scripts/production-live`, their tests, the Playwright output helper and the advisory probe come from the `setup-web-stack` recipes, filled with the project's values; the stack's rules come from its catalog and `standards/web-products.md`.
- `operate`, the setup skills and the templates are wellgent/skills itself; pstack is the port's (`michael-denyer/pstack-claude`).

In the run review, diff those paths from the run's starting commit to the final main branch, and sort every change:

- **Project-local** when it states a fact of this repo (a port, a command name, a journey, a route): it stays in the project.
- **Setup-wide** when it would hold for every project on the stack (a race in a recipe, a missing rule, a gap in a template): port it to wellgent/skills from its checkout, with the project's values turned back into the recipe's own, in a commit that names the request, before catching the requester up. Other projects take it at their next run's Ready.
- **pstack's** when the fault is in pstack itself: an issue on the port's repository, linked in the catch-up.

The review names what was ported and where.

## Cost

`/operate cost <session id>` prices one finished session from its transcript on this host: tokens per model and USD at the API list prices in [`scripts/prices.json`](scripts/prices.json).

```bash
bash <this skill's directory>/scripts/cost <session id>
bash <this skill's directory>/scripts/cost latest ~/repos/<repo>
```

`latest` takes the checkout's newest transcript.
