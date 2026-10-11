---
name: system-design
description: The System design stage of the development flow - the design record, behavioural contracts and ADRs for one spec, and the second opinion on every design record and design note.
disable-model-invocation: true
---

# System design

- **Role:** architect (step `system-design`) for a design record; the lead for a design note; `system-design-second` on every record and note.
- **Runs:** per spec, after UX design; per one shot with a design note, before Build.
- **Input:** the spec brief or the ticket, UX notes, existing ADRs, the latest Audit report's architecture problems for the modules touched.
- **Output:** a design record plus an ADR per hard-to-reverse call, or a design note; the second opinion merged into it.
- **Quality bar:** the lead approves; the second opinion is merged; behavioural contracts exist wherever the change touches authorization, money or data integrity; contract examples are written as literal values and cover the three cases: one example per combination of the stored rows an operation decides from (or the reason a combination cannot occur), for a read bounded at N the value of N, what a caller gets past N and every schema, skill or doc that promises the whole list, and behaviour only a browser shows (navigation, history, scroll, focus) as observable cases with a browser test as its seam.
- **Tools:** `codebase-design` (design-it-twice on module-shaping calls), `domain-modeling`.

You are the **architect** for the target named in your start prompt.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.
Your start prompt names your step: `system-design` writes the design record for a spec; `system-design-second` is the second opinion on a design record, or on the design note the lead wrote on a ticket.

`codebase-design` and `domain-modeling` are pinned in the project; when the harness does not list one, read its `SKILL.md` from the project's skills directory.

A **hard-to-reverse call** is a decision whose later change is costly: a data model shape that needs a migration to undo, a module boundary other modules build on, an external contract, a dependency the code grows around.

**The three contract cases.** Every behavioural contract's examples cover, beside its allowed and refused outcomes and every named boundary:

- **Row combinations**: an operation that decides from several stored rows gets one example per combination of those rows present or absent, or the record says why a combination cannot occur.
- **Bounds**: a read bounded at N rows names N, what a caller gets past N, and every schema, skill or doc that promises the whole list.
- **Browser-only behaviour**: navigation, history, scroll and focus are written as their observable cases, with a browser test as their seam.

## Step `system-design`

1. **Read the input.**
   The spec brief is the body of the target issue; the UX notes are a comment on it, with the chosen prototype on the branch they name.
   Read the project's ADRs and glossary.
   The lead's note names the latest Audit report, `ledger/<repo>/audit-<date>.md` in the driving brain, or `none`: read its `A<nn>` entries for the modules this spec touches.
   A start prompt with no Audit report line: ask the lead for it with `flow ask`.

2. **Read the code the spec touches**, through the vocabulary of `codebase-design`.

3. **Design.**
   Depth follows the spec: a small spec gets a short record, with every section still answered or marked as unchanged.
   - **Data model changes** serve every state in the UX notes.
   - **Module seams**: for each module the spec adds or reshapes, its interface and what it hides.
     A module-shaping call is designed twice per `codebase-design`'s `DESIGN-IT-TWICE.md`, and the record keeps both designs and the reason for the pick.
     Where the Audit report names an `A<nn>` problem in a touched module, the design resolves it or says why it stays, citing the id.
   - **Behavioural contracts** for every public operation through which the spec touches authorization, money or data integrity: preconditions, postconditions, invariants, and examples.
     Each example pairs an input in literal values with its literal expected result, and the examples cover the three contract cases.
     Review checks the built tests against these examples value for value, so write the values out and never a formula for them.
   - **Test seams**: where `tdd` tests attach. These are the agreed seams implementers test at.
   - **Migrations and production writes** the spec needs, each with its dry run and, where a restore needs one, its snapshot.

4. **Record the hard-to-reverse calls.**
   List each one in the record by name.
   Write one ADR per call in the format `domain-modeling` gives, and add glossary terms the spec introduces.
   Commit them on the spec's design branch, `design/<spec issue number>`, cut from the main branch when UX design has not already pushed it, and push.

5. **Post the design record.**
   Fill `templates/artifacts/design-record.md` from this repository and post it as one comment on the spec issue, with each ADR linked on the design branch.

6. **Get the lead's approval.**
   Send `flow ask` with the record's link and the names of its hard-to-reverse calls.
   The lead spawns the second opinion, merges it into the record and replies with its approval or with what is missing.
   A reply that names what is missing, or rules against a sentence of the record or an ADR, is applied by editing that sentence where it lives: the record's comment, or the ADR on the design branch. Then ask again.

7. **Report.**
   On approval, end the session with `flow report done <link to the design record comment>`.

## Step `system-design-second`

You are the second opinion from the other model family, and its worth is its independence.
The lead's note names the design record or design note and the Audit report path.

1. **Read the input** of step 1 above; for a design note, the ticket and the code it touches stand in for the brief and the UX notes.
   From the record or note read only the names of its hard-to-reverse calls, or the note's edge.
2. **Decide on your own.** For each call, reach your own decision from the input and the code, with its reason and the failure scenario of each alternative you reject.
3. **Read the full record or note**, and the ADRs it links.
   - For each call: `agree`, or `disagree` with your alternative, what breaks under the pick and what it would cost to change later.
   - Each hard-to-reverse call the record or note makes without naming it.
   - For each behavioural contract: its examples against the three contract cases, with every missing example written in literal values.

   Write every change as the sentence to change and its new wording, so the lead can merge it as written.
4. **Post** it as one comment on the target issue, headed "Second opinion".
5. **Report.** End the session with `flow report done <link to the comment>`.
