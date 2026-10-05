---
name: audit
description: The Audit stage of the development flow - the scanner pass, the defect review and the architecture review of a project's main branch, each review run by two model families.
disable-model-invocation: true
---

# Audit

- **Role:** auditor (steps `audit`, `audit-second`, `audit-architecture`, `audit-architecture-second`).
- **Runs:** at the client's close, reused as the next iteration's start; in full on a project's first run.
- **Input:** `main`, the scanner pass numbers, the project's Audit lenses, `CODING_STANDARDS.md`.
- **Output:** a scanner row in the ledger, one merged defect report, one merged architecture report.
- **Quality bar:** every finding has file, line and failure scenario; the lead has triaged every finding (bug ticket, Shape candidate, cleanup spec, or closed with a reason).
- **Tools:** the scanner pass, the defect review prompt with its six lenses, `/improve-codebase-architecture`.

The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.

## Pick your part

- **You are the lead** → [The lead's part](#the-leads-part).
- **Step `audit` or `audit-second`** → [The defect review](#the-defect-review).
- **Step `audit-architecture` or `audit-architecture-second`** → [The architecture review](#the-architecture-review).

A `-second` step follows the same part as its first step, on the other model family.
Its worth is its independence: both sessions run at the same time and the lead merges their reports.

## For every auditor

You audit the whole codebase at the commit the lead's note names, in the project checkout on the main branch.
`git rev-parse HEAD` equals that commit; on a mismatch ask the lead with `flow ask`.
Four audit sessions share this checkout, so work read-only: findings are confirmed by reading the code.

Read `CODING_STANDARDS.md`, the project's ADRs and glossary, and the Audit lenses in `docs/agents/dev-loop.md`.
Apply each Audit lens whose trigger names your review, by running the skill it names.
The scanner numbers in the note show where unused code, duplication and suppressions concentrate.

Write your report to `"${FLOW_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/flow}/audits/$FLOW_RUN.md"`, with your model family in each "Found by" or "Proposed by" and each "Triage" left to the lead.
End the session with `flow report done <path of the report>`.

## The defect review

1. **Split the codebase into areas** along its modules, each small enough for one subagent to read in full.
   Every source and test file belongs to exactly one area.

2. **Review every area** in its own fresh subagent, in parallel, each with the six lenses and the project's lenses:
   - **Silent failures**: errors caught and dropped, failures returned as success or as an empty result, fallbacks that hide a fault.
   - **Logic duplicated across modules**: one rule implemented in more than one place, where one copy can change without the other.
   - **Dead schema fields, dead indexes and scanner-exempt dead code**: fields nothing reads, indexes no query uses, code in ignored paths or behind entry points nothing reaches.
   - **Authorization and ownership**: for every public operation, who may call it and whose records it reads or writes.
   - **Seams on the wrong side of a boundary**: a rule placed where it cannot be enforced or tested, such as a check only the client makes or a multi-step write the caller composes.
   - **Test quality** against the test bar in `CODING_STANDARDS.md`.

   Each subagent returns its findings with lens, file, line and failure scenario, and a list of the rules and calculations its area implements.

3. **Match across areas.**
   Compare the areas' lists for the same rule implemented twice and for a rule enforced on the wrong side of a boundary between areas.

4. **Verify every finding** by reading the code at its line, and keep the ones you confirm.
   The failure scenario is concrete: the input or state, the path through the code, the wrong result.
   For dead code it is the evidence that nothing reads it; for a test it is the defect the test lets through.
   Leave out what the project's check command already blocks.

5. **Write the report** from `templates/artifacts/audit-defect-report.md` in this repository.

## The architecture review

`improve-codebase-architecture` and `codebase-design` are pinned in the project; when the harness does not list one, read its `SKILL.md` from the project's skills directory.

1. **Run `improve-codebase-architecture`'s Explore step as written**, with no direction given, so it scopes by the hot spots in the commit history.
2. **Write the candidates** into `templates/artifacts/audit-architecture-report.md` from this repository; this report takes the place of the skill's HTML report and of its question to the user.
   Each candidate names its files, states the problem as the change it makes hard or the defect it invites, describes the deepening in plain words, and carries the skill's recommendation strength.
   Every candidate passes the deletion test, and one that contradicts an ADR says so and why the ADR is worth reopening.
3. Stop there: the skill's grilling loop on a chosen candidate belongs to Shape and System design.

## The lead's part

1. **Pin the commit.**
   Bring the project checkout to the tip of the main branch and note its commit.
2. **Run the scanner pass** as `docs/agents/dev-loop.md` declares it, and append its numbers:
   `flow ledger scan <owner>/<repo> --commit <sha> <measure>=<number> ...`, with the nine measures in `ledger/README.md` and the project's own.
3. **Spawn the four steps together** on `<owner>/<repo>`, each with `--note` carrying the commit and the scanner numbers.
4. **Merge at the four run-end reports**, each linking its report file.
   - Defects: `ledger/<repo>/<iteration>-audit-defects.md` in the driving brain. Two findings on the same lines with the same failure are one entry, found by both.
   - Architecture: `ledger/<repo>/<iteration>-audit-architecture.md`. Two candidates on the same modules with the same problem are one entry, proposed by both, keeping each family's deepening when they differ.

   Commit and push both files.
5. **Triage every finding** per the lead skill's iteration reference and write the outcome on its "Triage" line.
