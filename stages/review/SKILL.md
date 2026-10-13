---
name: review
description: The Review stage of the development flow - the gated diff of a ticket, a batch or a spec, or a fix diff, reviewed for spec, standards and correctness, with a ticket per finding.
disable-model-invocation: true
---

# Review

- **Role:** reviewer (step `review`), the other model family from the builder.
- **Runs:** per landing whose diff class is not prose only: on the gated diff, then on each fix diff until clean.
- **Input:** the branch diff, the ticket or the spec, the design note or record, `CODING_STANDARDS.md`, the project's Review lenses.
- **Output:** Review findings.
- **Quality bar:** no open blocking finding (correctness, spec gap, breach of a documented standard); every contract example has a test with literal expected values; every finding confirmed at its line.
- **Tools:** the Review stage skill (`code-review` as written, a correctness pass and the project lenses, each in a fresh subagent). It never starts the app.

You are the **reviewer** for the target named in your start prompt, a ticket, a batch or a spec, working in the worktree that holds its branch.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.
Your worth is your independence: judge the diff from the spec source and the code alone.

`code-review` is pinned in the project; when the harness does not list it, read its `SKILL.md` from the project's skills directory and follow it as written.
Review works from the code and the tests, by reading them and running the project's test command.
Running the app belongs to QA.

## Steps

1. **Read the input.**
   - The **spec source**, by target:
     - a spec: the body of the target issue, the design record and UX notes it links, and the ADRs they name;
     - a ticket: its body and its design note comment when it has one; a bug ticket's report and its repro test;
     - a batch: the body and design note of each sub-issue the newest Build run comment lists as merged; a ticket taken out of the run is out of the review.
   - The newest "Build run" comment names the branch and its tip commit. `git rev-parse HEAD` equals that tip; on a mismatch ask the lead with `flow ask`.
   - `CODING_STANDARDS.md`, and the Review lenses in `docs/agents/dev-loop.md`, each with its trigger.

2. **Pin the diff.**
   The fixed point is the main branch.
   A note from the lead naming a base commit makes this a fix run: the fixed point is that commit.
   The diff is `git diff <fixed point>...HEAD`.

3. **Run the passes**, each in its own fresh subagent, in parallel.
   - **Spec and Standards**: `code-review` as written on the fixed point. The spec source is the one read in step 1, so built screens and copy are checked against the UX notes when the target has them. The standards source is `CODING_STANDARDS.md`.
   - **Correctness**: one subagent with the diff command and this brief:
     "Find defects in this diff. Read each changed hunk together with the code it calls and the code that calls it. Cover wrong results, states and inputs the code does not handle, failures swallowed or reported as success, who may call each changed public operation and whose records it touches, and writes that can be left half done. Report a defect only when you can state its failure scenario: the concrete input or state, the path through the code, and the wrong result. Per finding: file, line, failure scenario."
   - **Lenses**: for each Review lens whose trigger matches the diff, one subagent that runs the named skill on the matching files and reports in the same form.

   On a fix run every pass takes the fix diff, the spec source for `code-review` is the findings' tickets with the spec lines they cite, and a lens runs only on a file the fix diff touches beyond the findings' files.

4. **Check the contract tests** yourself.
   For every example in the behavioural contracts of the design record or design note, find the test that exercises it.
   - The example has a test.
   - The test's expected values are literals equal to the example's values.

   On a bug ticket, the repro test asserts the report's own values.
   A missing test and a computed expected value are each a blocking `spec` finding.

5. **Verify and classify.**
   Read the code at every reported line and keep a finding only when you confirm it there.
   Each kept finding has an axis (`correctness`, `spec` or `standards`), `<file>:<line>` and a failure scenario; a `standards` finding quotes the rule and names its file.
   - **Blocking**: a correctness defect the diff introduced; a spec requirement that is missing, partial or built wrong; code that departs from a contract example, an invariant or an ADR sentence as it is written now, whatever a comment approved; a breach of a rule written in `CODING_STANDARDS.md`.
   - **Filed**: everything else you confirmed: smell-baseline judgment calls, behaviour the spec source did not ask for, a lens finding without a defect behind it, a defect that was there before the diff.

   On a fix run, also confirm for each blocking ticket of the previous run that the fix diff resolves it.
   An unresolved one stays blocking under its existing ticket.
   The classification is yours; `flow ask` carries a tip mismatch, or a disagreement between a contract example, an ADR and the ticket that these rules leave open.

6. **File one ticket per finding** on the project tracker, per the project's tracker doc.
   The body carries the axis, `<file>:<line>`, the failure scenario and the spec line or rule it rests on.
   A blocking finding is a sub-issue of the target.
   A filed finding stands alone for the lead's triage, names the target it was found in, and says whether the diff introduced it.

7. **Post the findings.**
   Fill `$FLOW_HOME/templates/artifacts/review-findings.md` and post it as one comment on the target issue.
   The run number is one more than the Review findings comments already there.

8. **Report.**
   End the session with `flow report clean <link to the comment>` when no finding blocks, otherwise `flow report blocking <link to the comment>`.
