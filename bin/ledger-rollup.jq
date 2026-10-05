# flow ledger rollup: the Retro report's ledger sections as Markdown.
# Input: every row of the project as one array. $iteration: the iteration to report.
include "ledger";

def usd: if . == null then "-" else "$" + (. * 100 | round / 100 | tostring) end;
def hours: if . == null then "-" else (. / 360 | round / 10 | tostring) + " h" end;
def total(f): map(f) | map(select(. != null)) | if length == 0 then null else add end;
def stage_names: ["readiness", "shape", "ux-design", "system-design", "plan", "build", "review", "qa",
                  "release", "audit", "retro", "lead"];

def stage_stats:
  . as $rows
  | [stage_names[] as $s
     | ($rows | map(select(.kind == "run" and .stage == $s))) as $r
     | {key: $s, value: {
         runs: ($r | map(select(.outcome != "skipped")) | length),
         skipped: ($r | map(select(.outcome == "skipped")) | length),
         specs: ($r | map(.spec) | map(select(. != null)) | unique | length),
         blocking: ($r | total(.measures.blocking?)),
         usd: ($r | total(.cost.usd?)),
         wall_s: ($r | total(.wall_s?))}}]
  | from_entries;

# "current (previous)" when a previous iteration exists.
def versus($prev; f): (f | tostring) + (if $prev == null then "" else " (" + ($prev | f | tostring) + ")" end);

def spec_rollup:
  . as $rows
  | [$rows[] | select(.spec != null) | .spec] | unique
  | map(. as $spec | ($rows | map(select(.spec == $spec))) as $r
      | {spec: $spec,
         build_runs: ($r | map(select(.kind == "run" and .stage == "build")) | length),
         review_runs: ($r | map(select(.kind == "run" and .stage == "review" and .outcome != "skipped")) | length),
         blocking: ($r | total(.measures.blocking?) // 0),
         usd: ($r | total(.cost.usd?)),
         wall_s: ($r | total(.wall_s?))});

($iteration | tonumber? // .) as $it
| . as $all
| ([$all[].iteration] | unique | map(select(type == ($it | type) and . < $it)) | max) as $prev_it
| ($all | map(select(.iteration == $it))) as $rows
| (if $prev_it == null then null else $all | map(select(.iteration == $prev_it)) end) as $prev_rows
| ($rows | stage_stats) as $now
| (if $prev_rows == null then null else $prev_rows | stage_stats end) as $prev
| ($rows | map(select(.kind == "gate"))) as $gates
| ($rows | map(select(.kind == "decision"))) as $decisions
| ($rows | [.[] | select(.kind == "run" and .stage == "release" and .outcome != "skipped" and .spec != null) | .spec] | unique) as $released
| ($all | map(select(.kind == "bug"))) as $bugs

| "### Ledger rollup per stage",
  "",
  "Iteration \($it)" + (if $prev_it == null then ", the first on the flow." else ", previous iteration \($prev_it) in brackets." end),
  "",
  "| Stage | Runs | Skipped | Specs | Blocking findings | Cost | Wall time |",
  "| --- | --- | --- | --- | --- | --- | --- |",
  (stage_names[] as $s | $now[$s] | select(.runs + .skipped > 0) | ($prev[$s]? // null) as $p
   | "| \($s) | \(versus($p; .runs)) | \(versus($p; .skipped)) | \(versus($p; .specs)) | \(versus($p; .blocking // "-")) | \(versus($p; .usd | usd)) | \(versus($p; .wall_s | hours)) |"),
  ($now | "| total | | | | | \(versus($prev; [.[].usd] | total(.) | usd)) | \(versus($prev; [.[].wall_s] | total(.) | hours)) |"),
  "",
  ($rows | map(select(.kind == "run" and .session != null and (.cost == null or (.cost.unpriced | length) > 0))) | length
   | select(. > 0) | "\(.) rows have no full cost; run `flow ledger fill`.", ""),

  "### Gate",
  "",
  "- Results: \($gates | length) (pass \($gates | map(select(.verdict == "pass")) | length), red \($gates | map(select(.verdict == "red")) | length), flagged \($gates | map(select(.verdict == "flagged")) | length))",
  "- Protected-change hits: accepted on \($gates | map(select(.protected_hits > 0 and .protected_accepted != null)) | length) results, sent back or open on \($gates | map(select(.verdict == "flagged")) | length)",
  "- Conflict exits: \($rows | total(.conflict_exits?) // 0), questions to the lead: \($rows | total(.asks?) // 0)",
  "",

  "### Per spec",
  "",
  "| Spec | Build runs | Review runs | Blocking findings | Cost | Wall time |",
  "| --- | --- | --- | --- | --- | --- |",
  ($rows | spec_rollup[] | "| #\(.spec) | \(.build_runs) | \(.review_runs) | \(.blocking) | \(.usd | usd) | \(.wall_s | hours) |"),
  "",
  "Transcripts to sample: " + ($rows | spec_rollup
    | [(max_by(.build_runs) | select(. != null) | "most build runs #\(.spec)"),
       (max_by(.blocking) | select(. != null) | "most blocking findings #\(.spec)"),
       (max_by(.usd // 0) | select(. != null) | "highest cost #\(.spec)")]
    | if length == 0 then "none" else join(", ") end),
  "",

  "### Escaped defects",
  "",
  "| Spec | Within 7 days | Within 30 days |",
  "| --- | --- | --- |",
  ($released[] as $s | ($bugs | map(select(.origin == $s))) as $b
   | "| #\($s) | \($b | map(select(.days <= 7)) | length) | \($b | map(select(.days <= 30)) | length) |"),
  "",
  ($bugs | map(select(.origin_iteration == $it))[]
   | "- #\(.bug): origin spec #\(.origin), found after \(.days) days" + (if .area then ", touches \(.area)" else "" end)),
  "- Origin unknown, outside the rate: \($bugs | map(select(.iteration == $it and .origin == "unknown")) | length)",
  (if $prev_it == null then empty else
    ($bugs | map(select(.origin_iteration == $prev_it and .days <= 30))) as $late
    | "- Previous iteration \($prev_it): \($late | length) escaped within 30 days, \($late | map(select(.iteration == $it)) | length) of them recorded in this iteration" end),
  "",

  "### Client decisions",
  "",
  (["text", "prototype", "live-data"][] as $b
   | "- \($b): \($decisions | map(select(.basis == $b)) | length) decisions"),
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

  (($rows | map(select(.kind == "scan")) | last) as $scan
   | ($prev_rows // [] | map(select(.kind == "scan")) | last) as $before
   | if $scan == null then empty else
       "### Scanner pass",
       "",
       "Commit \($scan.commit[0:12])" + (if $before == null then "." else ", previous iteration in brackets." end),
       "",
       ($scan.measures | to_entries[] | "- \(.key): \(.value)" + (if $before.measures[.key]? == null then "" else " (\($before.measures[.key]))" end)),
       "" end)
