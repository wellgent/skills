---
name: operate
description: Run a brain request on a project through pstack - read the request issue, write the run prompt, start the run in herdr with landing authority, and leave the result to arrive on the issue. Use for /operate <issue>, and /operate cost <session> to price a finished run.
argument-hint: "<request issue> | cost <session id | latest <checkout>>"
disable-model-invocation: true
---

# Operate

The operator between a brain and pstack: a **run request** on the brain's tracker goes in, a pstack run on the project comes out, and the run's note comes back to the request.
Run from the brain's checkout on any host that holds the project at `~/repos/<repo>`.
pstack owns everything inside the run; this skill writes the prompt, starts the session and stops.

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

Fill [`prompt.md`](prompt.md) with the request's URL, its five sections copied as written and the requester's login; save it as `~/.local/state/operate/<repo>-<n>.md`.
Its run lines stay as the template has them.

## 4. Start the run

```bash
bash <this skill's directory>/scripts/start <owner>/<repo> <n> ~/.local/state/operate/<repo>-<n>.md
```

It opens a tab in the project checkout inside the herdr workspace `<repo>-operate`, starts Claude Code there with `/pstack:poteto-mode` pointed at the prompt file, names the session `op-<repo>-<n>`, and prints the session name and pane.
A start that stops at a startup prompt (folder trust, a login) is answered in that pane: `herdr agent read <session> --source visible` shows it.

## 5. Record and stop

Comment on the request: `run: <session> started on <hostname> at <UTC time>`, then end the turn.
The run posts its note on the request and assigns the requester when it is done; nothing here waits for it.

## Cost

`/operate cost <session id>` prices one finished session from its transcript on this host: tokens per model and USD at the API list prices in [`scripts/prices.json`](scripts/prices.json).

```bash
bash <this skill's directory>/scripts/cost <session id>
bash <this skill's directory>/scripts/cost latest ~/repos/<repo>
```

`latest` takes the checkout's newest transcript.
