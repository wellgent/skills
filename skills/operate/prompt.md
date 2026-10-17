# Run request <request URL>

<Goal, as written>

Done when: <Done check, as written>

Proof: <Proof, as written>

Known: <Known, as written>

Constraints: <Constraints, as written>

Run lines from the operator:

- Work in a fresh worktree.
- Keep a decision log, and keep it out of git.
- You have landing authority: land each pull request through Shipping once its independent verifier passes. No merge waits for the operator.
- A stop (a deploy, a data deletion, a message to a user, a product or preference call, the review of an interaction-changing pull request) that the constraints above do not answer goes to the request: post it as a comment on <request URL> with `gh issue comment`, assign the requester with `gh issue edit <request URL> --add-assignee <requester>`, and wait with `/loop` reading the issue until a newer comment answers it; then remove the assignee and continue.
- If you are truly stuck after a few hours, stop and write up why.
- When the done check passes, or you stop, post the audited decision log as a comment on <request URL> with `gh issue comment`: a line `Decision log` and the TSV in a collapsed `<details>` block, in as many comments as the length limit needs. Then post your `/ketchup` note as a comment on <request URL> with `gh issue comment`, then `gh issue edit <request URL> --add-assignee <requester>`.
