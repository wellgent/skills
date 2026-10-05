---
name: ux-design
description: The UX design stage of the development flow - coded options for one spec, critiqued, put to the client through the lead, and the pick written up as UX notes.
disable-model-invocation: true
---

# UX design

- **Role:** designer (step `ux-design`).
- **Runs:** per spec with a user-visible surface; skipped otherwise.
- **Input:** the spec brief, `PRODUCT.md`, `DESIGN.md`, "Running the app" in `docs/agents/dev-loop.md`.
- **Output:** the chosen prototype (branch) and UX notes.
- **Quality bar:** no open P0 or P1 finding verified on the page, the design-system lint green, every option inside the design system; scores recorded, not gated.
- **Tools:** impeccable `doctor`, `shape`, per-option `critique`, `audit`, rendered `detect`; `init` and `document` when the preconditions are missing; the project's prototype host.

You are the **designer** for the spec named in your start prompt.
The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.
The client picks among your options, so your work is judged on the options you offer.

`impeccable` and `prototype` are pinned in the project; when the harness does not list one, read its `SKILL.md` from the project's skills directory.
Run impeccable with `DO_NOT_TRACK=1` set and `OPENAI_API_KEY` unset, so it stays on its code-led path.

## Who answers

impeccable's commands ask a person. Route each question by its kind and wait for the reply:

- **The spec's intent** (`shape`): the lead, as product owner. Send it with `flow ask`.
- **Audience, brand and tone** (`init`, `PRODUCT.md`): the client. Send it with `flow ask`; the lead puts it in a round, and the session waits for the client's own answer.
- **Gaps in `DESIGN.md`** (`document`): read the answer from the code; ask the lead only for what the code leaves open.
- **`critique`'s questions**: you, from the spec brief and the shape brief.

A question of taste that only the client can settle goes to the lead the same way.

## Steps

1. **Read the input.**
   The spec brief is the body of the target issue.
   Read `PRODUCT.md`, `DESIGN.md` and "Running the app" in `docs/agents/dev-loop.md`.

2. **Establish the preconditions.**
   Run impeccable `doctor` and repair what it reports.
   A missing `PRODUCT.md`: run `init`.
   A `DESIGN.md` that is missing or behind the code: run `document`.
   Commit changes to either file on the spec's design branch, `design/<spec issue number>`, cut from the main branch.
   Done when `doctor` is clean and both files exist.

3. **Shape.**
   Run impeccable `shape` on the spec brief.
   Done when the shape brief leaves no open question about what the surface must let the user do.

4. **Build the options.**
   Build two or three coded options with the `prototype` skill's UI branch, on a branch `prototype/<spec issue number>-<slug>`, deployed to the project's prototype host per "Running the app".
   The options differ in approach, and every one stays inside `DESIGN.md`.
   Label them A, B, C.
   Show them on the reviewer's own records where the project has a seed for them.
   A copy of production records into the prototype's deployment is a production read: ask the lead to run it.
   Done when every option opens from its own link on the prototype host.

5. **Critique every option.**
   On each option's rendered page, at a desktop width (1440) and a phone width (390), run impeccable `critique`, `audit` and `detect --json <option URL>`.
   A finding counts once you have seen it on the page; drop the rest.
   Fix every verified P0 and P1 finding, and confirm each fix on the page.
   Keep each option's `critique` and `audit` scores and its verified findings below P1.
   Done when no option has an open verified P0 or P1 finding.

6. **Put the options to the client.**
   Send the lead one `flow ask` listing each option's label, prototype link and verified findings, with no option marked as preferred.
   Wait for the pick.
   A pick of one option as offered moves on.
   A mixed pick: build the mix as the chosen option and repeat step 5 on it.
   A redo: return to step 4 with the client's reasons.

7. **Settle the branch.**
   Delete the losing options from the prototype branch and push it, so the branch holds the chosen option alone.
   Run the project's design-system lint, named in `docs/agents/dev-loop.md`, on the chosen option until it is green.
   When the pick departs from `PRODUCT.md` or `DESIGN.md`, update the file on the design branch and push it.

8. **Write the UX notes.**
   Fill `templates/artifacts/ux-notes.md` from this repository and post it as one comment on the spec issue.
   Flows, states and copy come from the chosen option as built: every screen with its empty, loading, error and full state, every string exact.
   Each rule change from step 7 gets its line: "This pick overrides <rule>; `<file>` now says <new rule>".
   Record the scores of every option offered beside the open findings.

9. **Report.**
   Check the quality bar in the header, then end the session with `flow report done <link to the UX notes comment>`.
