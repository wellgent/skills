# A landing

Headers: `FLOW.md`, "The floor" and stages 6 to 9.
A landing takes one target (`<target>` below is `<owner>/<repo>#<issue>`: a ticket, a batch or a spec) from Build onto `main`.
The floor is the same on every path; the diff class the gate prints decides the only skips.
After every run-end report: append the row (`flow ledger run`), read the artifact, check the stage's quality bar, then take the next step here.

## 1. Build

1. `flow spawn build <target>`.
   `--note` names the design note's comment when one exists; for a fix run, the finding tickets, the failing check or the gate flags.
   A spec's Build merges its design branch itself.
2. At its run-end report the Build run comment names the branch, its tip commit and the worktree.
   An outcome `no-correct-seam` is a structural problem: triage it per [triage](triage.md).

## 2. The gate

1. In the worktree the Build run comment names: `flow gate <target>`.
   The result arrives as `gate: <target> <verdict> <diff class> <result path>`; append `flow ledger gate <target>`.
2. By verdict:
   - `pass`: go to Review.
   - `red`: `flow spawn build <target>` again, `--note` naming the failing check.
   - `flagged`: judge each open flag in the result (flags accepted earlier for this target are carried and already judged).
     A tightened check is fine.
     A loosened shared check (a new ignore entry, a disabled rule, a removed check step) stands only when a ticket names it or you approve it.
     A removed, skipped or weakened test stands only when a ticket changed or deleted the behaviour it tested.
     A suppression stands only with its reason on the same line.
     All stand: `flow gate <target> --accept "<reason>"`, which records the reasons and passes the result without a re-run. Otherwise back to Build with the flags in `--note`.
3. The diff class sets the rest of the floor: `prose-only` goes straight to Land; `no-surface-path` takes Review; `surface-path` takes Review and QA.

## 3. Review

Skipped only on `prose-only`: `flow ledger stage review <target> skipped --reason "diff class prose-only"`.

1. `flow spawn review <target> --cwd <the worktree>`; after a rebase since the Build run comment, `--note` names the tip and the gate result path.
2. Blocking findings (correctness, a spec gap, a breach of a documented standard) are tickets under the target.
   `flow spawn build <target>` with `--note` naming them; the fix run reviews its own diff before it reports.
   Then the gate, then `flow spawn review <target> --cwd <the worktree> --note "fix diff from <base commit>"`.
   Repeat until a Review run reports no blocking finding.
3. Every other finding is an intake: triage it per [triage](triage.md).

## 4. QA

Runs once, after Review is clean, on `surface-path` only.
Otherwise `flow ledger stage qa <target> skipped --reason "diff class <class>"`.

1. `flow spawn qa <target>`.
2. A reproduced defect this landing caused blocks: one `flow spawn build <target>` for all blocking findings, then the gate, then Review on the fix diff. QA does not run again.
3. A reproduced defect the landing did not cause, and a finding without a repro test, go to triage with their origin spec.

## 5. Land and Release

1. In the worktree: `flow land <target>`.
   Exit 3 means `main` moved and the tree changed: run the gate again, then land.
   The health check row is appended by `flow land`; `health: <target> <commit> appended|failed|skipped ...` arrives. A `failed` or `skipped` health check is a ticket on the project tracker.
2. Deploy by the card's deploy path and run its live check against production.
3. Run any production write the target needs under the Production rule in the skill, naming its ADR or record line.
4. Tell the client:
   - a spec: the Release report from `templates/artifacts/release-report.md` as a comment on the spec issue, each change with what the client must do to see it and its behaviour quoted from a contract example;
   - a ticket or batch: one FYI comment on its issue with the ticket list and the link to see the change.
5. `flow ledger stage release <target> released <comment link>`, then `flow ledger lead <owner>/<repo> <this session's id>`; commit and push the ledger.
6. Close the issue (a batch with its tickets) and remove its worktrees and merged branches.
7. Re-ask the two questions of [triage](triage.md) on what the landing surfaced: a finding left for triage, a ticket that left the batch, a structural problem.

A failed live check is a bug with this target as its origin: fix it forward as a new ticket through this file.
