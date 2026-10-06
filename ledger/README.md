# The ledger

The append-only record of stage runs and client decisions.
One JSONL file per iteration in the driving brain: `ledger/<repo>/<iteration>.jsonl`, where `<iteration>` is the iteration map's issue number.
The lead appends every row with `flow ledger` and commits the file; `flow help` and `flow ledger help` list the commands.

Rows hold observed facts: the spawn record, the run-end report, the gate result, the transcript, the tracker.
A count the lead passes as a measure is read from the stage's artifact, never estimated.

## Fields on every row

- `kind`: `run`, `gate`, `rec`, `decision`, `scan` or `bug`.
- `time`: when the row was appended, UTC. A gate row carries the gate's own time.
- `iteration`, `project` (`<owner>/<repo>`), `spec` (the spec's issue number, the bug ticket's on the single-bug path, null for iteration-level rows).

## `run`: one stage run

Appended by `flow ledger run '<run-end line>'` for a spawned session (it then closes the session's herdr tab, since the transcript keeps the session; `--keep` leaves the tab open), `flow ledger stage` for a stage the lead ran or skipped, and `flow ledger lead` for the lead session itself.

- `stage`: one of the eleven stages, or `lead`. `step`: the spawned step, null for a lead-run stage.
- `role`: `designer`, `architect`, `groomer`, `implementer`, `reviewer`, `qa`, `auditor` or `lead`.
- `run`: the session name. `session`: the harness session id that names the transcript.
- `harness`, `model`, `effort`: what the spawn record says the session started with. An inherited model is read from the transcript.
- `flow_version`: the commit of this repository at spawn. `harness_version`: from the transcript.
- `start` (spawn), `end` (the transcript's last entry), `wall_s`.
- `outcome`: the word the session reported. `skipped` rows carry `skip_reason`.
- `link`: the stage's artifact.
- `asks`, `conflict_exits`: how often the session used `flow ask` and `flow ask --conflict`.
- `measures`: the stage's counts, passed as `<name>=<number>`.
  Review and QA rows carry `blocking` and `filed` (findings that block Land, findings filed for triage).
  Build rows carry `tickets` (tickets merged).
- `cost`: `usd`, `tokens` (`input`, `cache_write`, `cache_read`, `output`), the same per model under `models`, `unpriced` (models the price table lacks) and `prices_as_of`.
  A lead row also carries `window`, the part of the lead session it covers.

## `gate`: one gate result

Appended by `flow ledger gate <target>` after each `flow gate`.

- `commit`, `branch`, `verdict` (`pass`, `red`, `flagged`).
- `check_exit`, `check_s`, `journeys_exit`, `journeys_s`.
- `protected_hits`: the number of protected-change flags. `protected_kinds`: the count per flag kind.
- `protected_accepted`: the lead's reason when the flags were accepted, else null.

A flagged row followed by a pass row with `protected_accepted` is an accepted hit.
A flagged row with no such row after it went back to Build.

## `rec` and `decision`: client decisions

- `rec`: `round` and `lead_rec`, the lead's recommendation for a design round. It is appended, committed and pushed before the client sees the options.
- `decision`: `id` (`<iteration>-d<n>`), `decision` (the gist), `basis` (`text`, `prototype`, `live-data`), `link` (the client's answer on the tracker).
- A decision that undoes an earlier one carries `reverses` (that decision's `id` or `link`) and `reverses_basis`.
- A design decision also carries `options_offered`, `pick` (`as-offered`, `mixed`, `redo`), `round` (per spec, from 1) and `lead_rec`, copied from the sealed `rec` row. A changed pick is a new decision row.

## `scan`: the Audit scanner pass

One row per Audit, with `commit` and `measures`:
`unused_code`, `duplication_source_pct`, `duplication_tests_pct`, `dependency_violations`, `suppressions`, `tests`, `test_seconds`, `source_lines`, `test_lines`.
A project adds the measures of its own scanners under further names.

## `bug`: an escaped defect

Appended by `flow ledger bug <owner>/<repo>#<bug> --origin <spec>` when a bug ticket's origin spec is set at triage.

- `bug`, `origin` (the origin spec, or `unknown` for a cause that predates the flow), `area` (`authorization`, `money`, `data-integrity` or null).
- `origin_released`, `origin_iteration`: the origin spec's Release row. `found`, and `days` between the two.

A bug found before its spec's Release row is a Review or QA finding and gets no row.
Rows with origin `unknown` stay out of the per-spec rate.

## Cost

`flow cost <session id>` reads the session's transcript and the transcripts of its subagents on the run host, and prices the tokens at API list prices from [`prices.json`](prices.json).

- Prices are per million tokens. A key matches its model id exactly or followed by a release date.
- A model the table lacks is listed under `unpriced` and left out of `usd`. Add its price, then run `flow ledger fill`.
- `flow ledger fill` is the one command that rewrites rows: it fills the cost of rows appended while the transcript or a price was missing.
- Codex input above 272,000 tokens per request has a higher list price; the table holds the short-context price, which is what a Codex session's context window allows.

The price pages under `sources` in `prices.json` are Readiness sources.

## Rollup and the Retro triggers

- `flow ledger rollup <owner>/<repo>` prints the Retro report's ledger sections as Markdown: per stage and per spec against the previous iteration, the gate, escaped defects per spec within 7 and 30 days, decisions and reversals by basis, design decisions, and the scanner pass.
- `flow ledger bug` exits 2 when the bug has an `area` and its origin spec was released in the open iteration.
- `flow ledger check <owner>/<repo>#<spec>`, run after the spec's Release row, compares its build runs, review runs, blocking findings, red gates, conflict exits, cost and wall time with the ten specs released before it, and exits 2 when one is above their highest value. The comparison starts once five earlier specs exist.

On exit 2 the lead runs a Retro, or records on the iteration map why not.
