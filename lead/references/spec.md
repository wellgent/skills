# A spec through its stages

Headers: `FLOW.md`, stages 3 to 9.
One spec is one issue on the project tracker (`<target>` below is `<owner>/<repo>#<spec>`) and one integration branch.
After every run-end report: append the row (`flow ledger run`), read the artifact, check the stage's quality bar, then take the next step here.

## 1. UX design

Only when the brief says the spec has a user-visible surface. Otherwise append `flow ledger stage ux-design <target> skipped --reason "no user-visible surface"`.

1. `flow spawn ux-design <target>`.
2. Answer the designer's questions by kind: questions about the spec's intent are yours, as product owner; gaps in `DESIGN.md` are yours, from the code; audience, brand and tone (`PRODUCT.md`) are the client's, once per project, in a round.
3. When the designer reports its options, put them to the client as a design question per [rounds](rounds.md) and send the pick back.
4. Done at the run-end report: the chosen prototype branch and the UX notes comment on the spec issue.

## 2. System design

1. `flow spawn system-design <target>`, with `--note` naming the path of the latest merged architecture audit report.
2. When the design record names a hard-to-reverse call, `flow spawn system-design-second <target>` and merge the second opinion into the record's comment yourself.
3. Approve the record when all three hold: every hard-to-reverse call has its second opinion and an ADR, behavioural contracts with literal examples exist wherever the spec touches authorization, money or data integrity, and the data model serves every state in the UX notes.
   Otherwise answer the architect's session with what is missing.

## 3. Plan

1. Write the spec with `to-spec`, its template unchanged, replacing the brief as the issue body and linking the UX notes and the design record.
   Append `flow ledger stage plan <target> done <issue link>`.
2. `flow spawn grooming <target>`.
3. Approve the ticket graph when every contract example and every UX state is covered by a ticket, each ticket names the contract examples it implements, and blocking edges serialize every pair of tickets that cannot run in parallel.

## 4. Build and the gate

1. `flow spawn build <target>`.
2. At its run-end report, in the worktree holding the integration branch: `flow gate <target>`, then `flow ledger gate <target>`.
   - `pass`: go to Review.
   - `red`: `flow spawn build <target>` again, `--note` naming the failing check.
   - `flagged`: judge each flag.
     A tightened check is fine.
     A loosened shared check (a new ignore entry, a disabled rule, a removed check step) stands only when a ticket names it or you approve it.
     A removed, skipped or weakened test stands only when a ticket changed or deleted the behaviour it tested.
     A suppression stands only with its reason on the same line.
     All stand: re-run with `--accept "<reason>"`. Otherwise back to Build with the flags in `--note`.

## 5. Review

1. `flow spawn review <target> --cwd <integration worktree>`.
2. Blocking findings (correctness, a spec gap, a breach of a documented standard) are tickets under the spec: `flow spawn build <target>` with `--note` naming them, then the gate, then `flow spawn review` again with `--note` naming the fix diff's base commit. Repeat until a Review run reports no blocking finding.
3. Every other finding goes to your triage per [shape](shape.md).

## 6. QA

Once per spec, after Review is clean.

1. A spec with no user-facing change gets no pass: `flow ledger stage qa <target> skipped --reason "<why>"`.
2. Otherwise `flow spawn qa <target>`.
3. A reproduced defect in behaviour the spec added or changed blocks: spawn one `build` for all blocking findings, then the gate, then Review on the fix diff. QA does not run again.
4. A reproduced defect the spec did not cause, and a finding without a repro test, go to your triage.

## 7. Release

1. In the integration worktree: `flow land <target>`. Exit 3 means `main` moved and the tree changed: run the gate again, then land.
2. Deploy by the card's deploy path and run its live check against production.
3. Run any production write the spec needs under the Production rule in the skill.
4. Post the Release report from `templates/artifacts/release-report.md` as a comment on the spec issue. For every change it says what the client must do to see it.
5. `flow ledger stage release <target> released <comment link>`, then `flow ledger check <target>`.
6. Close the spec issue and remove its worktrees and merged branches.

A failed live check is a bug with this spec as its origin: fix it forward through the single-bug path.

## The single-bug path

A bug ticket outside a spec, `<target>` being the bug ticket.

1. `flow spawn build <target>`: one session runs `diagnosing-bugs`, then `implement` on the ticket.
2. The gate, Review and its fix loop, as above.
3. QA under its skip rule.
4. Release as above, the report on the bug ticket.

A build session that reports no correct seam for the fix has found a structural problem: triage it per [shape](shape.md).
