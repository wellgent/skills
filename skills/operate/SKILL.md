---
name: operate
description: Run a brain request on a project through pstack - read the request issue, write the run prompt, start the run in herdr with landing authority, then watch the request, answer the run's stops or bring them to the requester, and check its note. Use for /operate <issue>, and /operate cost <session> to price a finished run.
argument-hint: "<request issue> | cost <session id | latest <checkout>>"
disable-model-invocation: true
---

# Operate

The operator between a brain and pstack: a **run request** on the brain's tracker goes in, a pstack run on the project comes out, and the run's note comes back to the request.
Run from the brain's checkout on any host that holds the project at `~/repos/<repo>`.
pstack owns everything inside the run; this skill writes the prompt, starts the session, and stays the run's operator until its note is handled: every stop the run posts reaches this session first, and the requester hears only the calls that are theirs.

## The request

One open issue on the brain's tracker labelled `run`, in the shape of [`request.md`](request.md): the repo as `<owner>/<repo>`, then Goal, Done check, Proof, Known and Constraints.
A request missing a section gets one comment naming the missing sections, and no run starts.

## 1. Read the request

`gh issue view <n> --json title,body,author,url,labels,comments` on the brain's tracker (`git remote get-url origin` in the brain).
Every section present, the label `run` present (add it when missing), and no comment starting `run:` on the issue, which marks a run already started.

## 2. Check the project

In `~/repos/<repo>`: `git fetch`, a clean tree on the main branch at its remote head, `pstack@pstack-claude` enabled in `.claude/settings.json`, and `gh auth status` green.
Anything missing stops the run with its fix; a project not set up gets `setup-project`.

## 3. Write the prompt

Fill [`prompt.md`](prompt.md) with the request's URL, and its five sections copied as written; save it as `~/.local/state/operate/<repo>-<n>.md`.
Its run lines stay as the template has them.

## 4. Start the run

```bash
bash <this skill's directory>/scripts/start <owner>/<repo> <n> ~/.local/state/operate/<repo>-<n>.md
```

It opens a tab in the project checkout inside the herdr workspace `<repo>-operate`, starts Claude Code there with `/pstack:poteto-mode` pointed at the prompt file, names the session `op-<repo>-<n>`, and prints the session name and pane.
A start that stops at a startup prompt (folder trust, a login) is answered in that pane: `herdr agent read <session> --source visible` shows it.

## 5. Record and watch

Comment on the request: `run: <session> started on <hostname> at <UTC time>`.
Start the watch in the background, then end the turn:

```bash
bash <this skill's directory>/scripts/watch <n> [<comment id>]
```

It returns with every comment newer than the given one (default: the newest now) and exits 0, or exits 3 when the run's session is gone with no new comment.
Restart it after each return, from the newest comment id it printed or that this session posted, until the note is handled.
This session stays open for the run's whole length; a closed operator leaves the run's stops unread.

## Stops

A stop is a comment from the run with questions it waits on, each with the default it applies when nobody answers.
Sort every question:

- **Answer it** when the request, the brain (the map the request came from, decisions on subject pages) or the project's own records settle it, or when it is reversible and the run's default is sound.
- **Escalate it** when it is a product or preference call only the requester can make, an irreversible action the constraints do not authorize, or work outside what the request asks for.

To escalate, catch the requester up in this session in `/ketchup`'s voice: how many calls wait on them, then each call with your recommendation and why, and what the run does without an answer.
Assign the requester on the request, so the call shows in their open `run` issues, and wait for their answer.

Answer the stop in one comment on the request covering every question, the requester's calls in their substance, and remove the assignee.
Then tell the run, so it reads the answer before its next poll: the pane is `herdr agent get <session>`'s `.result.agent.pane_id`.

```bash
herdr pane send-text <pane> "Your stop on <request URL> is answered: read it now."
herdr pane send-keys <pane> Enter
```

## The note

The run ends with its decision log and then its `/ketchup` note on the request.
Check the note's claims against the project: the pull requests it names are merged, and the done check's commands that run on this host pass on the main branch.
Then catch the requester up in `/ketchup`'s voice, with what the check found, and assign them on the request; closing it is their acceptance.
A watch exit 3 means the run ended without a note: read its pane or transcript, tell the requester what is known, and assign them.

## Cost

`/operate cost <session id>` prices one finished session from its transcript on this host: tokens per model and USD at the API list prices in [`scripts/prices.json`](scripts/prices.json).

```bash
bash <this skill's directory>/scripts/cost <session id>
bash <this skill's directory>/scripts/cost latest ~/repos/<repo>
```

`latest` takes the checkout's newest transcript.
