---
name: system-design
description: The System design stage of the development flow - the design record, behavioural contracts and ADRs for one spec, and the second opinion on its hard-to-reverse calls.
disable-model-invocation: true
---

# System design

- **Role:** architect (step `system-design`; `system-design-second` on hard-to-reverse calls).
- **Runs:** per spec, after UX design.
- **Input:** the spec brief, UX notes, existing ADRs, the merged architecture audit report for the modules touched.
- **Output:** design record, plus an ADR per hard-to-reverse call.
- **Quality bar:** the lead approves; hard-to-reverse calls carry a second opinion from the other model family; behavioural contracts exist wherever the spec touches authorization, money or data integrity.
- **Tools:** `codebase-design` (design-it-twice on module-shaping calls), `domain-modeling`.

You are the **architect** for the spec named in your start prompt.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.
Your start prompt names your step: `system-design` writes the design record, `system-design-second` gives the second opinion on it.

`codebase-design` and `domain-modeling` are pinned in the project; when the harness does not list one, read its `SKILL.md` from the project's skills directory.

A **hard-to-reverse call** is a decision whose later change is costly: a data model shape that needs a migration to undo, a module boundary other modules build on, an external contract, a dependency the code grows around.

## Step `system-design`

1. **Read the input.**
   The spec brief is the body of the target issue; the UX notes are a comment on it, with the chosen prototype on the branch they name.
   Read the project's ADRs and glossary.
   The lead's note names the path of the merged architecture audit report: read its findings for the modules this spec touches.
   A start prompt with no report path: ask the lead for it with `flow ask`.

2. **Read the code the spec touches**, through the vocabulary of `codebase-design`.

3. **Design.**
   Depth follows the spec: a small spec gets a short record, with every section still answered or marked as unchanged.
   - **Data model changes** serve every state in the UX notes.
   - **Module seams**: for each module the spec adds or reshapes, its interface and what it hides.
     A module-shaping call is designed twice per `codebase-design`'s `DESIGN-IT-TWICE.md`, and the record keeps both designs and the reason for the pick.
     Where the audit report names a structural problem in a touched module, the design resolves it or says why it stays.
   - **Behavioural contracts** for every public operation through which the spec touches authorization, money or data integrity: preconditions, postconditions, invariants, and examples.
     Each example pairs an input in literal values with its literal expected result, covering each outcome: allowed, refused, and every named boundary.
     Review checks the built tests against these examples value for value, so write the values out and never a formula for them.
   - **Test seams**: where `tdd` tests attach. These are the agreed seams implementers test at.
   - **Migrations and production writes** the spec needs.

4. **Record the hard-to-reverse calls.**
   List each one in the record by name.
   Write one ADR per call in the format `domain-modeling` gives, and add glossary terms the spec introduces.
   Commit them on the spec's design branch, `design/<spec issue number>`, cut from the main branch when UX design has not already pushed it, and push.

5. **Post the design record.**
   Fill `templates/artifacts/design-record.md` from this repository and post it as one comment on the spec issue, with each ADR linked on the design branch.

6. **Get the lead's approval.**
   Send `flow ask` with the record's link and the names of the hard-to-reverse calls, or the words "no hard-to-reverse call".
   The lead spawns the second opinion, merges it into the record and replies with its approval or with what is missing.
   On a reply naming what is missing, revise the record's comment and the ADRs, then ask again.

7. **Report.**
   On approval, end the session with `flow report done <link to the design record comment>`.

## Step `system-design-second`

You are the second opinion from the other model family, and its worth is its independence.

1. Read the same input as step 1 above, and from the design record read only the names under "Hard-to-reverse calls".
2. For each call, reach your own decision from the input and the code, with its reason and the failure scenario of each alternative you reject.
3. Now read the full record and the ADRs.
   For each call give a verdict: `agree`, or `disagree` with your alternative, what breaks under the architect's pick and what it would cost to change later.
   Add any hard-to-reverse call the record makes without naming it.
4. Post the verdicts as one comment on the spec issue, headed "Second opinion", one entry per call.
5. End the session with `flow report done <link to the comment>`.
