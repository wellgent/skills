# flow ledger rollup: the Retro report's ledger sections as Markdown over the Retro window.
# Input: every row of the project as one array. The window is every row after the last Retro row
# (a run row of stage retro); the previous window ends there and starts at the Retro row before it.
include "ledger";

def usd: if . == null then "-" else "$" + (. * 100 | round / 100 | tostring) end;
def hours: if . == null then "-" else (. / 360 | round / 10 | tostring) + " h" end;
def total(f): map(f) | map(select(. != null)) | if length == 0 then null else add end;
def stage_names: ["readiness", "shape", "ux-design", "system-design", "plan", "build", "review", "qa",
                  "release", "audit", "retro", "lead"];
def short: if . == null then "-" else .[0:12] end;

def stage_stats:
  . as $rows
  | [stage_names[] as $s
     | ($rows | map(select(.kind == "run" and .stage == $s))) as $r
     | {key: $s, value: {
         runs: ($r | map(select(.outcome != "skipped")) | length),
         skipped: ($r | map(select(.outcome == "skipped")) | length),
         targets: ($r | map(.spec) | map(select(. != null)) | unique | length),
         blocking: ($r | total(.measures.blocking?)),
         usd: ($r | total(.cost.usd?)),
         wall_s: ($r | total(.wall_s?))}}]
  | from_entries;

# "current (previous)" when a previous window exists.
def versus($prev; f): (f | tostring) + (if $prev == null then "" else " (" + ($prev | f | tostring) + ")" end);

# A target is a spec when it was shaped or designed; otherwise a ticket or a batch.
def container_rollup:
  . as $rows
  | [$rows[] | select(.spec != null) | .spec] | unique
  | map(. as $spec | ($rows | map(select(.spec == $spec))) as $r
      | {spec: $spec,
         kind: (if ($r | map(select(.kind == "run" and (.stage == "shape" or .stage == "system-design" or .stage == "plan"))) | length) > 0
                then "spec" else "ticket" end),
         build_runs: ($r | map(select(.kind == "run" and .stage == "build")) | length),
         review_runs: ($r | map(select(.kind == "run" and .stage == "review" and .outcome != "skipped")) | length),
         qa_runs: ($r | map(select(.kind == "run" and .stage == "qa" and .outcome != "skipped")) | length),
         blocking: ($r | total(.measures.blocking?) // 0),
         usd: ($r | total(.cost.usd?)),
         wall_s: ($r | total(.wall_s?))});

def landings: (map(select(.kind == "health")) | length) as $h
  | if $h > 0 then $h else map(select(.kind == "run" and .stage == "release" and .outcome != "skipped")) | length end;

. as $all
| ([$all[] | select(.kind == "run" and .stage == "retro")] | sort_by(.time) | map(.time)) as $retros
| ($retros | last) as $from
| (if ($retros | length) > 1 then $retros[-2] else null end) as $prev_from
| ($all | map(select($from == null or .time > $from))) as $rows
| (if $from == null then null else $all | map(select(.time <= $from and ($prev_from == null or .time > $prev_from))) end) as $prev_rows
| ($rows | stage_stats) as $now
| (if $prev_rows == null then null else $prev_rows | stage_stats end) as $prev
| ($rows | map(select(.kind == "gate"))) as $gates
| ($rows | map(select(.kind == "decision"))) as $decisions
| ($rows | map(select(.kind == "bug"))) as $bugs
| ($rows | container_rollup) as $containers

| "**Window:** since " + (if $from == null then "the first ledger row" else "the Retro row of \($from)" end)
  + ": \($rows | landings) landings, \($containers | map(select(.kind == "spec")) | length) specs, \($rows | map(.iteration) | map(select(. != null)) | unique | length) maps"
  + (if $prev_from == null and $from == null then "" else "; previous window in brackets" end),
  "",

  "### Ledger rollup per stage",
  "",
  "| Stage | Runs | Skipped | Targets | Blocking findings | Cost | Wall time |",
  "| --- | --- | --- | --- | --- | --- | --- |",
  (stage_names[] as $s | $now[$s] | select(.runs + .skipped > 0) | ($prev[$s]? // null) as $p
   | "| \($s) | \(versus($p; .runs)) | \(versus($p; .skipped)) | \(versus($p; .targets)) | \(versus($p; .blocking // "-")) | \(versus($p; .usd | usd)) | \(versus($p; .wall_s | hours)) |"),
  ($now | "| total | | | | | \(versus($prev; [.[].usd] | total(.) | usd)) | \(versus($prev; [.[].wall_s] | total(.) | hours)) |"),
  "",
  ($rows | map(select(.kind == "run" and .session != null and (.cost == null or (.cost.unpriced | length) > 0))) | length
   | select(. > 0) | "\(.) rows have no full cost; run `flow ledger fill`.", ""),

  "### Gate",
  "",
  "- Results: \($gates | length) (pass \($gates | map(select(.verdict == "pass")) | length), red \($gates | map(select(.verdict == "red")) | length), flagged \($gates | map(select(.verdict == "flagged")) | length))",
  "- Diff classes: " + ($gates | group_by(.diff_class) | map("\(.[0].diff_class // "unclassified") \(length)") | if length == 0 then "none" else join(", ") end),
  "- Protected-change hits: accepted on \($gates | map(select(.protected_hits > 0 and .protected_accepted != null)) | length) results, sent back or open on \($gates | map(select(.verdict == "flagged")) | length)",
  "- Conflict exits: \($rows | total(.conflict_exits?) // 0), questions to the lead: \($rows | total(.asks?) // 0)",
  "",

  "### Per container",
  "",
  "| Target | Kind | Build runs | Review runs | QA runs | Blocking findings | Cost | Wall time |",
  "| --- | --- | --- | --- | --- | --- | --- | --- |",
  ($containers[] | "| #\(.spec) | \(.kind) | \(.build_runs) | \(.review_runs) | \(.qa_runs) | \(.blocking) | \(.usd | usd) | \(.wall_s | hours) |"),
  "",
  "Transcripts to sample: " + ($containers
    | [(max_by(.build_runs) | select(. != null) | "most build runs #\(.spec)"),
       (max_by(.blocking) | select(. != null) | "most blocking findings #\(.spec)"),
       (max_by(.usd // 0) | select(. != null) | "highest cost #\(.spec)")]
    | if length == 0 then "none" else join(", ") end),
  "",

  "### Escaped defects",
  "",
  (($bugs | map(select(.origin != "unknown")) | group_by(.origin)) as $per_origin
   | if ($per_origin | length) == 0 then "- none recorded in the window" else
       "| Origin spec | Within 7 days | Within 30 days | Later |",
       "| --- | --- | --- | --- |",
       ($per_origin[] | "| #\(.[0].origin) | \(map(select(.days <= 7)) | length) | \(map(select(.days <= 30)) | length) | \(map(select(.days > 30)) | length) |"),
       "",
       ($bugs[] | select(.origin != "unknown")
        | "- #\(.bug): origin spec #\(.origin), found after \(.days) days" + (if .area then ", touches \(.area)" else "" end))
     end),
  "- Origin unknown, outside the rate: \($bugs | map(select(.origin == "unknown")) | length)",
  (if $prev_rows == null then empty else
    "- Previous window: \($prev_rows | map(select(.kind == "bug" and .origin != "unknown")) | length) escaped defects recorded" end),
  "",

  "### Client decisions",
  "",
  (["text", "prototype", "live-data"][] as $b
   | "- \($b): \($decisions | map(select(.basis == $b)) | length) decisions"
     + (if $prev_rows == null then "" else " (\($prev_rows | map(select(.kind == "decision" and .basis == $b)) | length))" end)),
  "",
  "### Reversals by basis",
  "",
  (($decisions | map(select(.reverses != null))) as $rev
   | if ($rev | length) == 0 then "- none"
     else ($rev | group_by(.reverses_basis)[] | "- \(.[0].reverses_basis): \(length) (\(map(.reverses) | join(", ")))") end),
  "",
  (($decisions | map(select(.pick != null))) as $design
   | if ($design | length) == 0 then empty else
       "### Design decisions",
       "",
       "- Picks: as offered \($design | map(select(.pick == "as-offered")) | length), mixed \($design | map(select(.pick == "mixed")) | length), redo \($design | map(select(.pick == "redo")) | length)",
       "- Rounds to a pick, per spec: \($design | group_by(.spec) | map("#\(.[0].spec) \(map(.round) | max)") | join(", "))",
       "- Options offered per round: \($design | map(.options_offered) | add / length | . * 10 | round / 10) on average",
       "- Sealed recommendations, to compare with the picks: \($design | map("#\(.spec) round \(.round): \(.lead_rec)") | join("; "))",
       "" end),

  (($rows | map(select(.kind == "health" or .kind == "scan")) | sort_by(.time)) as $checks
   | ($prev_rows // [] | map(select(.kind == "health" or .kind == "scan")) | sort_by(.time) | last) as $before
   | if ($checks | length) == 0 then "### Health check", "", "- no health check or scanner row in the window", "" else
       ($checks | first) as $first | ($checks | last) as $last
       | "### Health check",
         "",
         "\($checks | length) rows, from \($first.commit | short) to \($last.commit | short)"
         + (if $before == null then "." else "; the previous window's last row in brackets." end),
         "",
         ($last.measures | keys[] as $k
          | "- \($k): \($first.measures[$k] // "-") -> \($last.measures[$k])"
            + (if $before == null or $before.measures[$k]? == null then "" else " (\($before.measures[$k]))" end)),
         "" end)
