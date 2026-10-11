---
name: retro
description: The Retro step of the development flow - Matt Pocock's retro over a project's ledger since the last Retro, the tracker and the transcripts of its outliers, written up as the Retro report beside the ledger.
disable-model-invocation: true
---

# Retro

- **Role:** retro lead (the lead session started with `retro`); the `retro` step.
- **Runs:** as its own flow when the client starts it; never inside or at the close of a delivery iteration.
- **Input:** the ledger since the last Retro row, the health check rows, the tracker, transcripts sampled by ledger outliers.
- **Output:** a Retro report beside the ledger; checks and standards filed as one-shot tickets on the project tracker; flow text changes pushed; a request to the client for what it decides.
- **Quality bar:** every candidate is routed (check, standard, watch item, flow text change, or dropped with a reason); a flow or skill text change is pushed only with the client's acceptance.
- **Tools:** `retro` read as a file, `writing-for-agents`, `flow ledger rollup`.

The header above is this stage's entry in `FLOW.md`; terms are in `GLOSSARY.md`, both at the root of this repository.
You are the `retro` step: you find and route the candidates and write the report.
Filing, the client's answers and pushing text are the retro lead's part, in the lead skill's `references/retro.md`.

You run in the project checkout, read-only.
The lead's note names the report's path, in the driving brain's ledger directory beside the ledger files; write only that file and leave committing it to the lead.

## Steps

1. **The window.** Run `flow ledger rollup <owner>/<repo>` and keep its output as printed: it is the report's ledger section, the window against the previous one.
   Read the window's raw rows from the ledger files beside the report's path when a number needs its rows.

2. **Escaped defects.** For every `bug` row in the window, read the bug ticket and its origin spec's design record or design note, and write where it was found and what the record, the note or a check missed.

3. **Watch items.** Read the latest Retro report beside the ledger, when one exists, and write what the window shows for each of its watch items.

4. **Outliers.** Pick the sessions to read from the rows: the targets with the most Build runs, the most Review runs, the highest cost and the longest wall time, the sessions with conflict exits, and every session on the origin spec of an escaped defect.
   Each row's `session` names its transcript on this host (Claude Code under `~/.claude/projects/`, Codex under `~/.codex/sessions/`).
   Read each picked transcript in its own fresh subagent, which returns what went wrong or cost most, with the transcript lines that show it.

5. **Run `retro`.** It is pinned in the project; read its `SKILL.md` from the project's skills directory and follow it as written over the window, the tracker and those transcripts, reading `writing-for-agents` as a file from the driving brain's skills directory for its first step.
   Its candidates are the report's; its final step, presenting them, is the report.

6. **Route every candidate** to exactly one of:
   - **check**: a mechanical violation, which becomes a deterministic check in the project's check command;
   - **standard**: a judgment call, which becomes a rule in `CODING_STANDARDS.md`;
   - **watch item**: a stage measure that got worse, with the number the next Retro reads;
   - **flow text change**: a change to `FLOW.md`, a stage or lead skill, the project's `AGENTS.md` or `docs/agents/dev-loop.md`, with its proposed diff, written per `writing-for-agents`;
   - **dropped**, with the reason.

   Each candidate cites its evidence: ledger rows, a session and its transcript lines, tickets.
   Rank them by what they cost in the window: escaped defects first, then wasted runs and money, then friction.

7. **Write the report** from `templates/artifacts/retro-report.md` in this repository at the note's path.
   It is done when every rollup section is in, every escaped defect and watch item has its line, and every candidate has a route and its evidence.
   End the session with `flow report done <path of the report>`.
