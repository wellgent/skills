# Audit report: <project>, <date>

Audited commit: <sha on `main`>
Health check row: <ledger file and row>
Steps: audit <session>, audit-second <session>, audit-architecture <session>

## Notable problems, ranked

1. **D<nnn>** (<severity>) <lens> `<file>:<line>`: <failure scenario>. Consequence: <who hits it at today's scale, or the data, money or authorization at risk>. Found by: <family | both>. Caused by: <released spec | none>.
2. **A<nn>** <modules>: <problem>. Makes expensive: <the named kind of change>. Proposed deepening: <...>. Strength: <Strong | Worth exploring>.

## Below the bar, counted by lens

- <lens>: <n>, <one line on what they are>

## Standing rules

- A glossary, ADR or doc line the code contradicts is a finding quoting both lines.
- A bound a closed spec accepted is reported only with its failure scenario at the bound.
- A finding a released spec already fixed is closed naming that spec.

## Client's picks

- Batch <issue>: D<nnn>, D<nnn>
- Spec <issue>: A<nn>
- Bug <issue>: D<nnn>, origin spec <spec>
- Not picked: the rest, nothing filed
