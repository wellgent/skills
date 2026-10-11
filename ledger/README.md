# The ledger

The append-only record of stage runs, gates, health checks and client decisions.
JSONL files per project in the driving brain, `ledger/<repo>/`: one file per iteration, `<iteration>.jsonl`, named by the iteration map's issue number, and one file per month, `<YYYY-MM>.jsonl`, for every row outside a map (tickets, batches, health checks, the pool triage, the occasional flows).
`flow ledger` writes to the iteration named by `--iteration <id>` or by `projects["<owner>/<repo>"].iteration` in the flow config, and to the month's file when neither names one.
The lead appends every row with `flow ledger` and commits the file; `flow help` and `flow ledger help` list the commands.

Rows hold observed facts: the spawn record, the run-end report, the gate result, the transcript, the tracker.
A count the lead passes as a measure is read from the stage's artifact, never estimated.

## Fields on every row

- `kind`: `run`, `gate`, `rec`, `decision`, `scan`, `health`, `triage` or `bug`.
- `time`: when the row was appended, UTC. A gate row carries the gate's own time.
- `iteration` (the iteration map's issue number, null outside a map), `project` (`<owner>/<repo>`), `spec` (the target's issue number: the spec, the ticket or the batch; null for project-level rows).

## `run`: one stage run

Appended by `flow ledger run '<run-end line>'` for a spawned session (it then closes the session's herdr tab, since the transcript keeps the session; `--keep` leaves the tab open), `flow ledger stage` for a stage the lead ran or skipped, and `flow ledger lead` for a lead session.

- `stage`: one of the eleven stages, or `lead`. `step`: the spawned step, null for a lead-run stage.
- `role`: `designer`, `architect`, `groomer`, `implementer`, `reviewer`, `qa`, `auditor`, `retro` or `lead`.
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

The step `retro` runs the Retro over the ledger and gets stage `retro`, role `retro`.
The audit steps (`audit`, `audit-second`, `audit-architecture`) get stage `audit`, role `auditor`.

### Lead rows

`flow ledger lead <owner>/<repo> <session id>` appends the lead session's own row: role `lead`, no step, `start`, `end` and `wall_s` from the transcript, and `window`, the part of the session the row covers.
The window runs from the end of the session's previous lead row (or from the session's first transcript entry) until now, so a long-lived session is costed once however often it is ledgered.
Every lead session appends its row before it ends:

- the delivery lead with stage `lead`;
- an audit lead session with `--stage audit`, a retro lead session with `--stage retro`, so an occasional flow's cost includes its lead's part.

Lead-run stage rows (`flow ledger stage`) carry no cost of their own.

## `gate`: one gate result

Appended by `flow ledger gate <target>` after each `flow gate`.

- `commit`, `branch`, `verdict` (`pass`, `red`, `flagged`), `diff_class` (`prose-only`, `no-surface-path`, `surface-path`).
- `check_exit`, `check_s`, `journeys_exit`, `journeys_s`.
- `protected_hits`: the number of protected-change flags. `protected_kinds`: the count per flag kind.
- `protected_open`: flags not yet accepted. `protected_carried`: flags accepted on an earlier commit of the target.
- `protected_accepted`: the lead's reason when this result's open flags were accepted, else null.

A flagged row followed by a pass row with `protected_accepted` is an accepted hit.
A flagged row with no such row after it went back to Build.
A pass row with `protected_carried` above zero passed on flags judged earlier for the target.

## `rec` and `decision`: client decisions

- `rec`: `round` and `lead_rec`, the lead's recommendation for a design round. It is appended, committed and pushed before the client sees the options.
- `decision`: `id` (`<file>-d<n>`: `653-d4` in a map, `2026-10-d4` outside one), `decision` (the gist), `basis` (`text`, `prototype`, `live-data`), `link` (the client's answer on the tracker).
- A decision that undoes an earlier one carries `reverses` (that decision's `id` or `link`) and `reverses_basis`.
- A design decision also carries `options_offered`, `pick` (`as-offered`, `mixed`, `redo`), `round` (per spec, from 1) and `lead_rec`, copied from the sealed `rec` row. A changed pick is a new decision row.

## `scan` and `health`: the scanner pass

`scan` is the Audit's scanner pass, appended by the audit lead with `flow ledger scan`; `health` is the health check row `flow land` appends at every landing with `flow ledger health`.
Both carry `commit` and `measures`:
`unused_code`, `duplication_source_pct`, `duplication_tests_pct`, `dependency_violations`, `suppressions`, `tests`, `test_seconds`, `source_lines`, `test_lines`.
A project adds the measures of its own scanners under further names.
The health rows in time order are the trend Readiness, the Audit and the Retro read.

## `triage`: the pool triage report

Appended by `flow ledger triage <owner>/<repo> --link <report url> batch=<n> spec=<n> decide=<n> drop=<n>` when the triage report is posted.

- `link`: the report comment on the pool's lead-input issue.
- `measures`: the counts per class, plus any further count the report gives (for example `scope`, the issues read).

## `bug`: an escaped defect

Appended by `flow ledger bug <owner>/<repo>#<bug> --origin <spec>` when a bug ticket's origin spec is set at triage.

- `bug`, `origin` (the origin spec, or `unknown` for a cause that predates the flow), `area` (`authorization`, `money`, `data-integrity` or null).
- `origin_released`, `origin_iteration`: the origin spec's Release row. `found` (`--found <date>` is read as midnight UTC), and `days` between the two.

A bug found before its spec's Release row is a Review or QA finding and gets no row.
Rows with origin `unknown` stay out of the per-spec rate.

The command exits 2 when the bug has an `area`.
That exit is a signal and starts nothing: it is the number behind the advise line of the lead's next session start report, where the client decides whether a Retro runs.

## Cost

`flow cost <session id>` reads the session's transcript and the transcripts of its subagents on the run host, and prices the tokens at API list prices from [`prices.json`](prices.json).

- Prices are per million tokens. A key matches its model id exactly or followed by a release date.
- A model the table lacks is listed under `unpriced` and left out of `usd`. Add its price, then run `flow ledger fill`.
- `flow ledger fill` is the one command that rewrites rows: it fills the cost of rows appended while the transcript or a price was missing.
- Codex input above 272,000 tokens per request has a higher list price; the table holds the short-context price, which is what a Codex session's context window allows.

The price pages under `sources` in `prices.json` are Readiness sources.

## The Retro window and the rollup

The **Retro window** is every row of the project, across its files, after the last Retro row; with no Retro row yet it is every row.
The **Retro row** is the retro lead's own row (`run`, stage `retro`, role `lead`), appended as the Retro's last row, so the `retro` step's row and the Retro's decision rows fall inside the window it closes.
The window before it, between the two most recent Retro rows, is the comparison.

`flow ledger rollup <owner>/<repo>` prints the Retro report's ledger sections as Markdown over the window, the previous window in brackets: the window line (landings, specs, maps), per stage, the gate with its diff classes, per container (spec, ticket or batch), escaped defects per origin spec within 7 and 30 days, decisions and reversals by basis, design decisions, and the health check trend from the window's first to its last row.
A target counts as a spec when it has a Shape, System design or Plan row; otherwise it is a ticket or a batch.
Landings are the health rows of the window, or its Release rows when it has no health row.

## The status view

`flow status <owner>/<repo>` prints the read-only status view from the ledger, the spawn records and herdr on the host, and the tracker: the open iteration or batches, each target in flight (rows but no Release row) with its latest stage and live session, the live sessions with what they wait on, the open request issues with their age, and the ledgered cost of the window split into steps and lead.
With an iteration set in the flow config the window is that iteration's rows; otherwise it is the Retro window.
