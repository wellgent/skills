# Run request <request URL>

<Goal, as written>

Done when: <Done check, as written>

Proof: <Proof, as written>

Known: <Known, as written>

Constraints: <Constraints, as written>

Resume from: <hand-back URL; this line goes on a first run>

Run lines from the operator:

- Work in a fresh worktree, under the rules in the project's `AGENTS.md`.
- Keep a decision log, and keep it out of git.
- Scope: on mid-run discoveries, pstack's Orchestrate rule (`orchestrate.md`) holds over its Autonomous run rule (`autonomous-run.md`). Fix only what blocks the done check; everything else parks as a follow-up in your note.
- Before you start any implementer, post your plan on <request URL> as a stop and wait for the operator's go or cut. The plan names each unit's model and effort.
- A unit the approved plan does not hold: a leftover copy of an approved unit's own finding needs no stop and is listed in your next comment; a bug that blocks landing is a run note, fixed in its own pull request; anything else, including a change to a public contract, is a stop.
- The request above is frozen for this run. Every change to it is a comment on <request URL> starting `scope:`; treat each as an answered stop.
- You have landing authority: land each pull request through the project's `scripts/land` once its verifier passes. No merge waits for the operator.
- A stop (a deploy, a data deletion, a message to a user, a product or preference call, the review of an interaction-changing pull request) that the constraints above do not answer goes to the request: post it as a comment on <request URL> with `gh issue comment`, each question with the default you apply without an answer, keep working on what it does not block, and wait with `/loop` reading the issue until a newer comment answers it. A stop's default never ships a behaviour or visible change, and a pull request named in an open stop does not land until the stop is answered. The operator reads every comment you post, answers what it can and brings the requester in for the rest.
- When the operator names in your pane a part of the run to stop, stop it leaves first, then confirm on <request URL> what stopped once `ListAgents` shows none of it.
- When the operator pauses the run in your pane, run pstack's Pause safely and push every branch the resume needs. Then post on <request URL> everything a resume needs, with every path relative to `$HOME`: the decision log as below, then a comment headed `Hand-back` holding the resume note and each working file the resume reads (contracts, scripts, the checkpoint's artifacts) in its own collapsed `<details>` block titled with its path, in as many comments as the length limit needs.
- On a resume, restore each file from the hand-back to its path under `$HOME`, carry on the decision log posted with it, apply every `scope:` comment on <request URL>, and pick up through pstack's Session pickup from the resume note.
- If you are truly stuck after a few hours, stop and write up why.
- When the done check passes, or you stop, post the audited decision log as a comment on <request URL> with `gh issue comment`: a line `Decision log` and the TSV in a collapsed `<details>` block, in as many comments as the length limit needs. Then post your `/ketchup` note as a comment on <request URL> with `gh issue comment`.
