---
name: audit
description: The Audit stage of the development flow - the defect review by both model families and the architecture review of a project's whole codebase at one pinned commit, each writing a step report the audit lead merges.
disable-model-invocation: true
---

# Audit

- **Role:** audit lead (the lead session started with `audit`); auditors (steps `audit`, `audit-second`, `audit-architecture`).
- **Runs:** as its own flow when the client starts it; never inside or at the close of a delivery iteration.
- **Input:** `main` at the pinned commit, the health check rows, the project's Audit lenses, `CODING_STANDARDS.md`.
- **Output:** one Audit report beside the ledger and a request to the client; for what the client picks, one issue per batch with its findings listed, one spec issue per spec, and a bug ticket with its origin spec for a finding caused by a released spec.
- **Quality bar:** every area read in full, defects by both model families and architecture by the primary family; every notable problem carries a finding id, file, line and its consequence at today's scale or the named change it makes expensive; everything below the bar is counted by lens, not itemized; a glossary, ADR or doc line the code contradicts is a finding quoting both lines; a bound a closed spec accepted is reported only with its failure scenario at the bound; a finding a released spec already fixed is closed naming that spec; nothing is filed that the client did not pick.
- **Tools:** the scanner pass, the defect review with its six lenses, `/improve-codebase-architecture`, `flow ledger`.

The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.
The audit lead's part (pinning, merging, the request, filing) is in the lead skill's `references/audit.md`.
This file is the auditors' part.

## Pick your part

- **Step `audit` or `audit-second`** → [The defect review](#the-defect-review).
- **Step `audit-architecture`** → [The architecture review](#the-architecture-review).

`audit` and `audit-second` run the same review on the two model families at the same time.
Their worth is their independence: each judges the code alone, and the audit lead merges the two reports.

## For every auditor

You audit the whole codebase at the commit the lead's note names, in the detached worktree you were started in.
`git rev-parse HEAD` equals that commit; on a mismatch ask the lead with `flow ask`.
The three audit sessions share this worktree, so work read-only: a finding is confirmed by reading the code.

Read `CODING_STANDARDS.md`, the project's ADRs and glossary, and the Audit lenses in `docs/agents/dev-loop.md`.
Apply each Audit lens whose line names your review, by running the skill it names.
The scanner numbers in the note show where unused code, duplication and suppressions concentrate.

**The notable bar.** A finding is **notable** when it has a concrete consequence at today's scale (a user or the agent hits it; data, money or authorization is at risk), or when it is structure that makes a named kind of change expensive or risky.
Itemize every notable finding.
Count the rest by lens, with one line on what they are: defects past bounds production is far from, test-quality items, duplication and dead code with no named cost.

**The standing rules**, applied to every finding:

- A glossary, ADR or doc line the code contradicts is a finding quoting both lines.
- A bound a closed spec accepted is reported only with its failure scenario at the bound.

Number your findings `D001` up (defects) or `A01` up (architecture); the ids are local to your report and the audit lead gives the merged report its own.
Write your report to `"${FLOW_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/flow}/audits/$FLOW_RUN.md"`, with each finding's commit from `git blame` on its lines, so the audit lead can trace the spec that caused it.
End the session with `flow report done <path of the report>`.

## The defect review

1. **Split the codebase into areas** along its modules, each small enough for one subagent to read in full.
   Every source and test file belongs to exactly one area.

2. **Review every area** in its own fresh subagent, in parallel, each reading every file of its area in full with the six lenses and the project's lenses:
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

5. **Sort by the notable bar**, apply the standing rules, and write the report from `templates/artifacts/audit-defect-report.md` in this repository.
   The report is done when every area is listed as read and every confirmed finding is either itemized or counted.

## The architecture review

`improve-codebase-architecture` and `codebase-design` are pinned in the project; when the harness does not list one, read its `SKILL.md` from the project's skills directory.

1. **Run `improve-codebase-architecture`'s Explore step as written**, with no direction given, so it scopes by the hot spots in the commit history.
2. **Keep the notable candidates**: each names the kind of change it makes expensive or risky, with the files that change would touch.
   Every candidate passes the deletion test, and one that contradicts an ADR says so and why the ADR is worth reopening.
3. **Write the report** from `templates/artifacts/audit-architecture-report.md` in this repository; it takes the place of the skill's HTML report and of its question to the user.
   Each candidate names its modules, states the problem as the change it makes hard or the defect it invites, describes the deepening in plain words, and carries the skill's recommendation strength.
4. Stop there: the skill's grilling loop on a chosen candidate belongs to Shape and System design.
