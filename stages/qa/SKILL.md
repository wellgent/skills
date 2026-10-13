---
name: qa
description: The QA stage of the development flow - one exploratory pass in the running app over a reviewed ticket, batch or spec whose diff touches a surface path, with a failing repro test and a ticket per finding.
disable-model-invocation: true
---

# QA

- **Role:** QA (step `qa`).
- **Runs:** once per landing whose diff class is surface path, after Review is clean; skipped and logged otherwise.
- **Input:** the reviewed branch in its own worktree and dev deployment, the behavioural contracts, the list of changed screens, "Running the app".
- **Output:** QA findings.
- **Quality bar:** no open blocking finding; a finding counts only with a failing repro test at the lowest seam that reproduces it, and blocks Land only when this landing caused it.
- **Tools:** the QA stage skill and the project's QA tools from `docs/agents/dev-loop.md`.

You are **QA** for the target named in your start prompt: a ticket, a batch or a spec.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.
The seam tests and journey tests already passed in the gate, so your pass is exploratory: it looks where no test looks.

The project's QA tools and their named checks are declared in `docs/agents/dev-loop.md`; when the harness does not list a tool's skill, read its `SKILL.md` from the project's skills directory.

## Steps

1. **Read the input.**
   - The contracts, by target: a spec's design record and UX notes, linked from its body; a ticket's design note comment and body; a batch's merged sub-issues, each with its design note; a bug ticket's report.
   - The newest "Build run" comment names the reviewed branch and its tip commit.
   - "Running the app", the worktree section, the surface paths and the QA tools in `docs/agents/dev-loop.md`.

2. **Set up the environment.**
   Create the branch `qa/<target issue number>` from the reviewed tip in its own worktree, per the worktree section.
   Start the app there per "Running the app", on its own dev deployment with the seeded test identities.
   Done when you are signed in as a seeded identity on the reviewed code.
   An environment that will not start after following the section: ask the lead with `flow ask`.

3. **Write the charter.**
   - One line per behavioural contract operation, with its outcomes: allowed, refused, each named boundary, and the three contract cases the record or note writes out.
   - One line per changed screen: each screen the diff against the main branch reaches through a surface path, with the states the UX notes list for it when the target has them.

4. **Explore, one pass.**
   Work each charter line once in the running app with the project's QA tools, as each seeded identity the line concerns.
   Go past the contract's own examples: values between and beyond its boundaries, steps out of order, a repeated submit, reload and back in the middle of a flow, one identity reaching for another's records, empty data and a lot of data.
   Run every named check the project declares for QA on the routes you exercise.
   Done when every charter line is covered, or marked "not reached" with the reason.

5. **Turn each observed defect into a finding.**
   - Reproduce it a second time from a clean state and write down the steps, the expected result and the actual result.
   - Write a failing repro test at the lowest seam that reproduces it, starting from the test seams the design record names. A browser test is the choice only when the defect exists solely in the browser wiring. The test asserts the expected result in literal values and fails for the reason you observed.
   - Commit each repro test alone on the `qa/` branch. The branch holds failing tests by design: run each repro test on its own, and leave the check command to the fix run.
   - Decide the cause. This landing caused it when the code at fault is in the landing's diff against the main branch, or the repro test passes on the main branch. Otherwise take the origin spec from `git blame` on the lines at fault, `unknown` when the cause predates the flow.

   A defect you cannot pin in a test stays a finding with "no repro" and its steps.

6. **File one ticket per finding** on the project tracker, per the project's tracker doc.
   The body carries the steps, expected and actual results, the repro test's path and commit, and the cause.
   - **Blocking**: a reproduced defect this landing caused. It is a sub-issue of the target.
   - **Filed**: a reproduced defect this landing did not cause, as a bug ticket with its origin spec, and every finding without a repro test. Each stands alone for the lead's triage and names the target it was found in.

7. **Close the environment.**
   Push the `qa/` branch, stop the app, and remove the worktree and its dev deployment per the worktree section.

8. **Post the findings.**
   Fill `$FLOW_HOME/templates/artifacts/qa-findings.md` and post it as one comment on the target issue.

9. **Report.**
   End the session with `flow report clean <link to the comment>` when no finding blocks, otherwise `flow report blocking <link to the comment>`.
