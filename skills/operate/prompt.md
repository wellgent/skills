# Run request <request URL>

<Goal, as written>

Done when: <Done check, as written>

Proof: <Proof, as written>

Known: <Known, as written>

Constraints: <Constraints, as written>

Resume from: <hand-back URL; this line goes on a first run>

Run lines from the operator:

- Work in a fresh worktree, under the rules in the project's `AGENTS.md`.
- Keep a decision log, and keep it out of git. A row records a command's result only after its exit is read, and a loop over landings or checks runs in bash.
- Run at most `AGENT_SLOTS` implementers and verifiers at once (the host's environment; the project's `dev-loop.md` under Agents).
- Scope: on mid-run discoveries, pstack's Orchestrate rule (`orchestrate.md`) holds over its Autonomous run rule (`autonomous-run.md`). Fix only what blocks the done check; everything else parks as a follow-up in your note.
- Before you start any implementer, post your plan on <request URL> as a stop and wait for the operator's go or cut. The plan names each unit's model and effort.
- A unit the approved plan does not hold: a leftover copy of an approved unit's own finding needs no stop and is listed in your next comment; a bug that blocks landing is a run note, fixed in its own pull request; anything else, including a change to a public contract, is a stop.
- The request above is frozen for this run. Every change to it is a comment on <request URL> starting `scope:`; treat each as an answered stop.
- You have landing authority: land each pull request through the project's `scripts/land` once its verifier passes. No merge waits for the operator.
- A stop (a deploy, a data deletion, a message to a user, a product or preference call, a change to layout, look and feel or functionality, which waits for the requester's review on its preview before it lands) that the constraints above do not answer goes to the request: post it as a comment on <request URL> with `gh issue comment`, each question with the default you apply without an answer, keep working on what it does not block, and wait until a newer comment answers it, with `/loop` reading the issue or a background script you start that polls it and returns on a newer comment. A stop's default never ships a behaviour or visible change, and a pull request named in an open stop does not land until the stop is answered. The operator reads every comment you post, answers what it can and brings the requester in for the rest.
- A bug fix, or a fix that makes the UI match the project's design records, lands on its verifier's pass, labelled `preview`, and your note lists it.
- A fix round on a review answer changes only what the answer names. Any further change to layout, look and feel or functionality it brings is a new visible change: it waits for the requester's review on its preview before it lands, even where the answer authorized landing on the verifier's pass.
- Screenshots and recordings are an agent's own evidence, never a deliverable: they stay in the evidence directory of the agent that took them and are never committed, pushed, uploaded or posted. A review stop gives the requester the preview URL and what changed. Before you post your note, delete every evidence directory, log and scratch file the run created on the host.
- `needs-human` on the project's tracker marks a call or task that stays with the requester after the run, or someday. Never close, edit or work an issue that carries it. A question within this run's scope is a stop, never a `needs-human` issue; label or open one only for what stays with the requester after the run, with that call written on the issue.
- Start from the main branch as the operator's `ready:` comment on <request URL> names it; a starting commit in the request is the last one known when it was written.
- When the operator names in your pane a part of the run to stop, stop it leaves first, then confirm on <request URL> what stopped once `ListAgents` shows none of it.
- When the operator pauses the run in your pane, run pstack's Pause safely and push every branch the resume needs. Then post on <request URL> everything a resume needs, with every path relative to `$HOME`: the decision log as below, then a comment headed `Hand-back` holding the resume note and each working file the resume reads (contracts, scripts, the checkpoint's artifacts) in its own collapsed `<details>` block titled with its path, in as many comments as the length limit needs.
- On a resume, restore each file from the hand-back to its path under `$HOME`, carry on the decision log posted with it, apply every `scope:` comment on <request URL>, and pick up through pstack's Session pickup from the resume note.
- Delete files only with `rm` on a literal path or `find <dir> -delete`, never `rm` on a glob or a variable: Claude Code stops the session at a permission prompt for those, even with permissions bypassed.
- Never print or write a deployment's whole environment (`convex env list`, `vercel env pull`): read the one value you need (`convex env get <name>`) into a variable, or use the host's own login. A printed environment lands in the session's transcript on disk.
- If you are truly stuck after a few hours, stop and write up why.
- When the done check passes, or you stop, post the audited decision log as a comment on <request URL> with `gh issue comment`: a line `Decision log` and the TSV in a collapsed `<details>` block, in as many comments as the length limit needs. Then post your `/ketchup` note as a comment on <request URL> with `gh issue comment`.
