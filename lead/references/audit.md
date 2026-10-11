# The Audit

Header: `FLOW.md`, stage 10. The auditors' part is `stages/audit/SKILL.md`.
You are the **audit lead**: this session was started with `/lead <owner>/<repo> audit`, by the client.
An Audit inspects the whole codebase at one commit and ends in what the client picks to work, filed as batches, specs and bug tickets; it builds nothing and never blocks delivery, which may run beside it.
Readiness has run and its advise line is `none`.

## 1. Pin the commit

1. In the project checkout, `git fetch origin`.
2. Pin the commit of the project's latest `health` row in the ledger (`ledger/<repo>/*.jsonl`) when it is on the main branch: its numbers are the scanner pass.
   With no health row, pin the tip of `origin/<main>`.
3. Add a detached worktree at the pinned commit, so landings that move the checkout leave the Audit's code still:
   `git -C <checkout> worktree add --detach <checkout>-audit-<sha12> <sha>`.
4. With no health row, run the scanner pass in that worktree: the project's worktree setup from `docs/agents/dev-loop.md`, each command of its "Scanner pass" section, then `flow ledger scan <owner>/<repo> --commit <sha> <measure>=<number> ...`.

## 2. Spawn the three steps

Start all three at once, each in the worktree, with `--note` carrying the pinned commit and the scanner numbers:

```bash
flow spawn audit <owner>/<repo> --cwd <worktree> --note "commit <sha>; scanner: <measure>=<number> ..."
flow spawn audit-second <owner>/<repo> --cwd <worktree> --note "<same>"
flow spawn audit-architecture <owner>/<repo> --cwd <worktree> --note "<same>"
flow tick arm
```

Answer their questions as the lead skill's "Running steps" says.
At each run-end report append its row with `flow ledger run '<the line>'`; the link is the step's report file on this host.

## 3. Merge one ranked report

Write `ledger/<repo>/audit-<YYYY-MM-DD>.md` in the driving brain from `templates/artifacts/audit-report.md`, from the three step reports:

- **Merge** two findings on the same lines with the same failure into one entry, found by both. Two architecture candidates on the same modules with the same problem are one entry, keeping each family's deepening when they differ.
- **Hold the bar.** Re-judge every itemized finding against the notable bar in `GLOSSARY.md`; one that fails it moves into the counts. Re-read the code at the line when the two families disagree.
- **Trace the cause.** For each notable defect, the commit its step report names leads to the target that landed it (the commit message, the branch, the ledger's Release row for that target). A spec with a Release row is the finding's origin: write it on the "Caused by" line.
- **Close what is done.** A finding a spec released after the pinned commit already fixed goes under "Closed", naming that spec; so does a finding an open issue already holds, naming that issue, and a bound a closed spec accepted with no failure scenario at the bound.
- **Rank** the notable problems by consequence: authorization, money and data integrity first, then what users or the agent hit, then structure by the cost of the change it blocks. Give them the report's ids in rank order, `D001` and `A01` up.
- **Count** everything below the bar by lens, once across both families.

The report is done when every step report's finding is merged, counted or closed, and every notable entry has its id, file, line and consequence.
Commit and push it.

## 4. The request

Group the notable problems the way you would work them, and put the groups to the client in one request per [requests](rounds.md):

- a **batch**: related defects by surface or module, about ten findings or 400 changed lines, landing together;
- a **spec**: an architecture problem, or defects whose fix needs a design or a client decision;
- a **bug**: a defect whose origin is a released spec, filed on its own.

One question per group: work it or leave it, with your recommendation and what it costs to leave.
The basis is text, the report's entries linked.
The client picks what gets worked, regroups, and says when; what the client leaves is not filed.
Wait for the answer as the waiting rule says, then record it per [requests](rounds.md), "Answers".

## 5. File the picks

On the project tracker, and nothing beyond what the client picked:

- **One issue per picked batch**, labelled `batch` and `ready-for-agent`, its body listing each finding with the report's path and id, file and line, failure scenario and consequence. It has no sub-issues: a finding that leaves the batch by conflict exit becomes its own ticket then, with the report's finding id as its origin.
- **One spec issue per picked spec**, holding the problem, its findings or the architecture candidate with its proposed deepening, and the report's path. It enters delivery as any input does, through the triage, and Shape writes its brief.
- **One bug ticket per picked defect caused by a released spec**, on the project's bug template with its origin spec, then `flow ledger bug <owner>/<repo>#<bug> --origin <spec> --found <today> [--area authorization|money|data-integrity]`.

Write the filed issues into the report's "Client's picks", with "Not picked: the rest, nothing filed"; commit and push.

## 6. End

1. Remove the worktree: `git -C <checkout> worktree remove <worktree>`.
2. `flow tick disarm`, then `flow ledger lead <owner>/<repo> <this session's id> --stage audit`; commit and push the ledger.
3. Tell the client the report's path and the filed issues; a delivery lead session (`/lead <owner>/<repo> <issue>`) takes them from there. Then end.
