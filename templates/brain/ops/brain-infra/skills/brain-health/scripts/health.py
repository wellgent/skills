#!/usr/bin/env python3
"""Brain health workflow steps, each a command routine under brain-routines.

  health.py nightly   the derived-maintenance dream phases
  health.py purge     hard-delete pages soft-deleted more than 72 h ago
  health.py doctor    timeline repair, the full doctor, schema pack, writer roster, entity lint, brain checks, deadman, reconciler rollup

A step reports through $ROUTINE_RUN_DIR/result.json. A finding it cannot settle is a journal
problem: the run ends partial and the runner pages #ops-alerts. A step that cannot run exits 1.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True  # routines write nothing into the published copy
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR.parent / 'brain-routines' / 'scripts'))
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402
import routine as runner  # noqa: E402

ARCHIVE_RULE = ('is valid only inside', 'need status:')  # the entity lint's two archive status messages


class Step:
    def __init__(self):
        self.cfg = lib.config()
        self.hc = lib.read_json(SKILL_DIR / 'config.json')
        self.rc = lib.read_json(SKILL_DIR.parent / 'gbrain-host-reconciler' / 'config.json')
        self.meta = lib.current_run(self.cfg)
        self.dir = lib.run_dir(self.cfg, self.meta['run_id'])
        self.published = Path(self.cfg['published_repo'])
        self.problems, self.counts = [], {}

    def note(self, text):
        lib.journal(self.cfg, self.meta['run_id'], 'note', text=text)

    def problem(self, short, text=None):
        self.problems.append(short)
        lib.journal(self.cfg, self.meta['run_id'], 'problem', text=text or short)

    def gbrain_json(self, argv, timeout, env=None, name=None):
        code, out, err = lib.run([self.rc['gbrain_bin'], *argv], cwd=self.dir, env=env, timeout=timeout, check=False)
        if name:
            (self.dir / f'{name}.json').write_text(out)
        start = next((i for i, line in enumerate(out.splitlines()) if line.lstrip().startswith('{')), None)
        try:
            return code, json.loads('\n'.join(out.splitlines()[start:])) if start is not None else None, err
        except json.JSONDecodeError:
            return code, None, err

    def finish(self, summary, status=None):
        lib.atomic(self.dir / 'result.json', {'status': status or ('partial' if self.problems else 'ok'),
                                              'summary': summary, 'counts': self.counts})


# nightly

def nightly(s):
    done = []
    for phase in s.hc['nightly_phases']:
        code, report, err = s.gbrain_json(['dream', '--source', s.rc['source_id'], '--dir', str(s.published), '--phase', phase, '--json'],
                                          timeout=3000, name=f'dream-{phase}')
        entry = next((p for p in (report or {}).get('phases', []) if p.get('phase') == phase), None)
        # Only the phase's own "ok" passes: a degraded run exits 0 with the cycle reading "clean".
        if code or not entry or entry.get('status') != 'ok':
            reason = entry.get('status') if entry else f'exit {code}, no phase report: {(err or "").strip()[-200:]}'
            s.finish(f'phase {phase} failed after {", ".join(done) or "no phase"}', 'failed')
            raise Failed(f'dream phase {phase}: {reason}')
        d = entry.get('details') or {}
        if phase == 'sync':
            s.counts['pages synced'] = sum(d.get(k, 0) for k in ('added', 'modified', 'deleted', 'renamed'))
            done.append(f'sync +{d.get("added", 0)} ~{d.get("modified", 0)} -{d.get("deleted", 0)}')
        elif phase == 'extract':
            s.counts['links created'] = d.get('linksCreated', 0) + d.get('mention_links_created', 0)
            s.counts['timeline entries created'] = d.get('timelineCreated', 0)
            done.append(f'extract {d.get("pages_processed", 0)} pages')
        elif phase == 'embed':
            s.counts['chunks embedded'] = d.get('embedded', 0)
            done.append(f'embed {d.get("embedded", 0)} chunks')
        elif phase == 'orphans':
            done.append(f'{d.get("total_orphans", 0)} orphans of {d.get("total_linkable", 0)} linkable pages')
        else:
            done.append(phase)
    s.finish(', '.join(done))


# purge

def purge(s):
    code, report, err = s.gbrain_json(['pages', 'purge-deleted', '--yes', '--json'], timeout=1200, name='purge')
    if code or report is None:
        raise Failed(f'purge-deleted failed (exit {code}): {(err or "").strip()[-300:]}')
    count = report.get('count', len(report.get('slugs', [])))
    s.counts['soft-deleted pages purged'] = count
    s.finish(f'{count} soft-deleted page(s) past 72 h purged')


# doctor

def timeline_repair(s):
    """Drop database-only timeline rows: markdown is the record, so a row with no bullet in its page goes."""
    env = dict(os.environ, GBRAIN_SRC=s.rc['gbrain_src'], HEALTH_SOURCE=s.rc['source_id'])
    script = SKILL_DIR / 'scripts' / 'timeline-db-only.ts'
    listed = json.loads(lib.run([s.rc['bun_bin'], script, 'list'], cwd=s.dir, env=env, timeout=600).splitlines()[-1])
    rows = listed['rows']
    if not rows:
        return 'timeline clean'
    memory_path = lib.state_dir(s.cfg) / 'health' / 'timeline-dropped.json'
    memory = lib.read_json(memory_path, {})
    fp = lambda r: hashlib.sha256(f'{r["slug"]}\0{r["date"]}\0{r["summary"]}'.encode()).hexdigest()[:16]
    back = [r for r in rows if fp(r) in memory]
    drop = [r for r in rows if fp(r) not in memory]
    if back:
        s.problem(f'{len(back)} dropped timeline row(s) came back',
                  f'{len(back)} DB-only timeline row(s) came back after an earlier drop, so a writer regenerates them and dropping is not the fix; '
                  f'kept: ' + ', '.join(f'`{r["slug"]}` {r["date"]}' for r in back[:5]))
    if len(drop) > s.hc['timeline_max_rows']:
        s.problem(f'{len(drop)} DB-only timeline rows, over the {s.hc["timeline_max_rows"]} cap',
                  f'{len(drop)} DB-only timeline rows exceed the cap of {s.hc["timeline_max_rows"]} per run; none dropped. Preview: `gbrain repair timeline`.')
        return f'{len(drop)} DB-only timeline rows held at the cap'
    if not drop:
        return f'{len(back)} DB-only timeline row(s) kept'
    lib.atomic(s.dir / 'timeline-dropped.json', drop)
    ids_file = s.dir / 'timeline-ids.json'
    ids_file.write_text(json.dumps([r['id'] for r in drop]))
    result = json.loads(lib.run([s.rc['bun_bin'], script, 'drop', ids_file], cwd=s.dir, env=env, timeout=300).splitlines()[-1])
    stamp = lib.iso()
    memory.update({fp(r): stamp for r in drop})
    cutoff = lib.iso(lib.now() - s.hc['timeline_memory_days'] * lib.DAY)
    lib.atomic(memory_path, {k: v for k, v in memory.items() if v >= cutoff})
    s.counts['DB-only timeline rows dropped'] = result['deleted']
    if listed['expected'] != len(rows):
        s.note(f'Timeline classifier: {len(rows)} rows one at a time, {listed["expected"]} by page total.')
    return f'{result["deleted"]} DB-only timeline row(s) dropped'


def run_doctor(s):
    env = dict(os.environ, GBRAIN_SKILLS_DIR=str(s.published / 'skills'), **s.hc['doctor']['env'])
    # --budget-ms 0: a non-interactive doctor otherwise stops at 90 s and reports the rest as unknown.
    code, report, err = s.gbrain_json(['doctor', '--json', '--budget-ms', '0'], timeout=1200, env=env, name='doctor')
    if report is None:
        s.problem('doctor gave no JSON', f'`gbrain doctor` produced no JSON (exit {code}): {(err or "").strip()[-200:]}')
        return 'doctor gave no JSON'
    ignore, page = set(s.hc['doctor']['ignore']), set(s.hc['doctor']['page'])
    checks = [c for c in report.get('checks', []) if c.get('name') not in ignore]
    unknown = lambda c: (c.get('details') or {}).get('health') == 'unknown'
    paged = [c for c in checks if c.get('status') == 'fail' or (c.get('name') in page and c.get('status') != 'ok') or unknown(c)]
    for c in paged:
        why = 'unknown at the entry budget' if unknown(c) and c.get('status') != 'fail' else c.get('status')
        s.problem(f'doctor `{c["name"]}` {why}', f'The engine doctor reports `{c["name"]}` as {why}: {(c.get("message") or "")[:300]}')
    warns = [c for c in checks if c.get('status') == 'warn' and c not in paged]
    if warns:
        s.note('Doctor warnings: ' + ', '.join(f'`{c["name"]}`' for c in warns) + '.')
    new_warnings(s, warns)
    return f'doctor {len(warns)} warn' + (f', {len(paged)} paged' if paged else '')


def warning_keys(c):
    """One key per doctor warning, except one per undeclared page type, so a second new type is not hidden behind the first."""
    if c['name'] != 'schema_pack_consistency':
        return {c['name']: (c.get('message') or 'no message').strip()[:400]}
    keys = {}
    for src in (c.get('details') or {}).get('per_source', []):
        for t in src.get('undeclared_types', []):
            keys[f'{c["name"]}:{t["type"]}'] = (f'Source `{src["source_id"]}`: {t["count"]} page(s) use type `{t["type"]}`, which pack `{src["pack"]}` '
                                                f'neither declares nor aliases. Declare it in `ops/schema-packs/{src["pack"]}/pack.json` or retype the pages.')
    return keys or {c['name']: (c.get('message') or 'no message').strip()[:400]}


def new_warnings(s, warns):
    """A doctor warning speaks once, when it is new: one needs-attention issue, closed again when it clears.

    The known warnings live in <state_dir>/health/doctor-warnings.json; the first run records what it finds without filing."""
    path = lib.state_dir(s.cfg) / 'health' / 'doctor-warnings.json'
    known = lib.read_json(path)
    current = {k: m for c in warns for k, m in warning_keys(c).items()}
    if known is not None:
        for name in sorted(set(current) - set(known)):
            message = current[name]
            s.counts['new doctor warnings'] = s.counts.get('new doctor warnings', 0) + 1
            lib.file_attention(
                s.cfg, s.meta, f'health-doctor:warn:{name}', f'{s.cfg["brain"]} health: the engine doctor has a new warning, {name}',
                f'The engine doctor started warning on `{name}`: {message}',
                'A warning is not a failure, so the health check cannot tell whether it needs a fix or is expected for this brain.',
                [f'`gbrain doctor` on {lib.iso()[:10]}: `{name}` warn, "{message}"'],
                [{'label': 'Accept it', 'detail': 'the health check stays quiet about it while it lasts, and raises it again if it clears and comes back',
                  'action': {'type': 'close'}},
                 {'label': 'Look into it by hand', 'detail': 'close this issue once it is settled', 'action': {'type': 'close'}}],
                2, 'a new warning usually means something changed in the brain or the engine')
        cleared = set(known) - set(current)
        if cleared:
            for issue in lib.open_attention(s.cfg, 'health'):
                fp = lib._parse_comment('fingerprint', issue['body'])
                if isinstance(fp, str) and fp.startswith('health-doctor:warn:') and fp.split(':', 2)[2] in cleared:
                    lib.gh(s.cfg, 'issue', 'comment', str(issue['number']), '--repo', s.cfg['github_repo'], '--body-file', '-',
                           input=f'The warning cleared on {lib.iso()[:10]}, so this issue closes.\n\n{lib.MARKER}')
                    lib.gh(s.cfg, 'issue', 'close', str(issue['number']), '--repo', s.cfg['github_repo'], '--reason', 'completed')
                    lib.journal(s.cfg, s.meta['run_id'], 'note', text=f'Closed <{issue["url"]}>: the warning cleared.')
    lib.atomic(path, {name: (known or {}).get(name, lib.iso()) for name in current})


def schema_pack(s):
    """The engine loads the brain's pack from the published copy, so a pushed pack change reaches it on fast-forward."""
    code, report, err = s.gbrain_json(['schema', 'active', '--json'], timeout=120)
    pack = (report or {}).get('pack')
    if not pack:
        s.problem('schema pack unresolved', f'`gbrain schema active` named no pack (exit {code}): {(err or "").strip()[-200:]}')
        return 'schema pack unresolved'
    installed = Path(os.environ.get('GBRAIN_HOME') or Path.home()) / '.gbrain' / 'schema-packs' / pack
    tracked = s.published / 'ops' / 'schema-packs' / pack
    if not tracked.is_dir():
        s.problem(f'schema pack `{pack}` is not in the brain', f'The engine runs schema pack `{pack}`, which the brain does not carry at '
                  f'`ops/schema-packs/{pack}/`, so its page types are not the ones the brain writes.')
    elif installed.resolve() != tracked.resolve():
        s.problem(f'schema pack `{pack}` is not the published copy', f'The engine loads schema pack `{pack}` from `{installed}`, which is not a link to '
                  f'`{tracked}`, so pack changes pushed to the brain do not reach it. Move the directory aside and run `ln -s {tracked} {installed}`.')
    else:
        return f'schema pack {pack} {report.get("version", "")}'.strip()
    return f'schema pack {pack} off'


def roster(s):
    script = s.published / 'ops/brain-infra/skills/brain-transport/scripts/writer-roster-check'
    code, out, err = lib.run([s.cfg['python_bin'], script], cwd=s.dir, timeout=300, check=False)
    if code == 0:
        return 'roster ok'
    for line in (out or err).strip().splitlines()[:10]:
        s.problem(f'writer roster: {line[:120]}', f'Writer roster: {line}')
    return 'roster findings'


def entity_lint(s):
    code, out, err = lib.run([s.rc['bun_bin'], s.published / s.hc['entity_lint']], cwd=s.published, timeout=300, check=False)
    if code == 0:
        return 'entity lint ok'
    lines = [line for line in (err or out).strip().splitlines() if ': ' in line]
    archive = [line for line in lines if any(k in line for k in ARCHIVE_RULE)]
    other = [line for line in lines if line not in archive]
    if archive:
        # Archive moves are relevance-workflow work: report the count, never page it.
        s.note(f'Entity lint: {len(archive)} page(s) break the archive status rule, left to the relevance workflow.')
    for line in other[:10]:
        s.problem(f'entity lint: {line[:120]}', f'Entity lint: {line}')
    if not lines:
        s.problem('entity lint failed', f'Entity lint exited {code}: {(err or out).strip()[-200:]}')
    return f'entity lint {len(archive)} archive status' + (f', {len(other)} other' if other else '')


def brain_checks(s):
    """The brain's own checks, `checks` in config.json: each runs from the published copy, and a non-zero exit pages every line it prints."""
    if not s.hc['checks']:
        return None
    failed = 0
    for check in s.hc['checks']:
        script = s.published / check['argv'][0]
        argv = ([s.cfg['python_bin']] if script.suffix == '.py' else []) + [script, *check['argv'][1:]]
        code, out, err = lib.run(argv, cwd=s.published, timeout=300, check=False)
        if code == 0:
            continue
        failed += 1
        for line in [line for line in (out or err).strip().splitlines() if line.strip()][:10] or [f'exit {code}']:
            s.problem(f'{check["name"]}: {line[:120]}', f'{check["name"]}: {line}')
    return f'{len(s.hc["checks"])} brain check(s) ' + (f'{failed} failed' if failed else 'ok')


def cron_sets(expr):
    fields = expr.split()
    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
    sets = []
    for part, (lo, hi) in zip(fields, bounds):
        values = set()
        for item in part.split(','):
            span, _, step = item.partition('/')
            step = int(step) if step else 1
            if span == '*':
                a, b = lo, hi
            elif '-' in span:
                a, b = map(int, span.split('-'))
            else:
                a = int(span)
                b = hi if step > 1 else a
            values.update(range(a, b + 1, step))
        sets.append(values)
    sets[4] = {d % 7 for d in sets[4]}
    return sets, fields[2] == '*' or fields[4] == '*'


def last_fire(expr, tz, before):
    """The latest time at or before `before` (epoch seconds) when the cron expression fires in `tz`."""
    (minutes, hours, dom, months, dow), either_star = cron_sets(expr)
    zone = ZoneInfo(tz)
    t = int(before // 60) * 60
    for _ in range(40 * 24 * 60):
        local = dt.datetime.fromtimestamp(t, zone)
        if local.minute in minutes and local.hour in hours and local.month in months:
            day, week = local.day in dom, local.isoweekday() % 7 in dow
            if (day and week) if either_star else (day or week):
                return t
        t -= 60
    return None


def deadman(s):
    """Every routine's heartbeat is newer than its last scheduled run that should have finished."""
    m = lib.manifest(s.cfg)
    o = s.cfg['openclaw']
    try:
        jobs = {j['declarationKey']: j for j in json.loads(lib.run([o['bin'], 'cron', 'list', '--all', '--json'], timeout=90)).get('jobs', [])
                if j.get('declarationKey')}
    except (Failed, json.JSONDecodeError) as error:
        s.problem('cron list failed', f'Deadman could not list the crons: {error}')
        jobs = None
    late = 0
    for r in m['routines']:
        if r['id'] == s.meta['routine'] or not r.get('enabled', True):
            continue
        job = jobs.get(runner.declaration_key(s.cfg, r['id'])) if jobs is not None else {}
        if job is None:
            s.problem(f'`{r["id"]}` has no cron', f'{runner.title(s.cfg, r["id"])} (`{r["id"]}`) has no cron, so it does not run.')
            late += 1
            continue
        timeout = r.get('timeout_seconds', s.cfg['timing']['default_timeout_seconds'])
        settle = timeout + s.cfg['timing']['lease_wait_seconds'] + s.hc['deadman_grace_seconds']
        due = last_fire(r['schedule'], m['timezone'], lib.now() - settle)
        if due is None or due < job.get('createdAtMs', 0) / 1000:
            continue  # not due since the cron was registered
        beat = lib.state_dir(s.cfg) / 'heartbeats' / r['id']
        at = beat.stat().st_mtime if beat.exists() else None
        if at is None or at < due:
            late += 1
            disabled = ', its cron is disabled' if job and not job.get('enabled', True) else ''
            s.problem(f'`{r["id"]}` missed its run', f'{runner.title(s.cfg, r["id"])} (`{r["id"]}`) missed its run due {lib.iso(due)}; '
                      + (f'it last finished {lib.iso(at)}' if at else 'it has never finished') + disabled + '.')
    return 'deadman ok' if not late else f'deadman {late} late'


def reconciler(s):
    state = lib.read_json(Path(s.rc['state_dir']) / 'state.json', {})
    beat = state.get('heartbeat_at')
    age = lib.now() - dt.datetime.fromisoformat(beat.replace('Z', '+00:00')).timestamp() if beat else None
    if age is None or age > s.hc['reconciler_stale_seconds']:
        s.problem('reconciler heartbeat stale', 'The reconciler, which publishes and indexes pushed commits, '
                  + ('has no heartbeat' if age is None else f'last reported {int(age // 60)} minutes ago')
                  + f', so it may have stopped; check `systemctl --user status {s.rc["unit"]}`.')
    script = s.published / 'ops/brain-infra/skills/gbrain-host-reconciler/scripts/reconciler.py'
    try:
        r = json.loads(lib.run([s.rc['python_bin'], script, 'rollup', '--hours', '24'], cwd=s.dir, timeout=120))
    except (Failed, json.JSONDecodeError) as error:
        s.problem('reconciler rollup failed', f'Reconciler rollup failed: {error}')
        return 'reconciler rollup failed'
    rescues = ', '.join(f'`{e["branch"]}` <{e["issue"]}>' if e.get('issue') else f'`{e["branch"]}`' for e in r['rescues'])
    s.note(f'Reconciler 24 h: {r["publishes"]} publishes, {r["imports"]} imports (max {r["import_seconds_max"] or 0} s), '
           f'{r["embeds"]} embeds, {r["embed_pending"]} embed pending, {r["blocked_ticks"]} blocked ticks, {len(r["alerts"])} alerts, '
           f'{len(r["rescues"])} rescues{": " + rescues if rescues else ""}, {r["restarts"]} restarts; '
           f'published `{(r["published_head"] or "")[:8]}`, heartbeat {int(age or 0)} s old.')
    if r['alert_send_failures']:
        s.problem('reconciler alert sends failed', f'Reconciler alert sends failed: {len(r["alert_send_failures"])}, last '
                  + str(r['alert_send_failures'][-1].get('error', ''))[:200])
    return 'reconciler ok' if age is not None and age <= s.hc['reconciler_stale_seconds'] else 'reconciler stale'


def doctor(s):
    parts = []
    for check in (timeline_repair, run_doctor, schema_pack, roster, entity_lint, brain_checks, deadman, reconciler):
        try:
            parts.append(check(s))
        except Failed as error:
            s.problem(f'{check.__name__} failed', f'{check.__name__.replace("_", " ")} failed: {error}')
    s.finish('; '.join(s.problems) if s.problems else ', '.join(p for p in parts if p))


def main():
    steps = {'nightly': nightly, 'purge': purge, 'doctor': doctor}
    if len(sys.argv) != 2 or sys.argv[1] not in steps:
        print(__doc__, file=sys.stderr)
        return 2
    steps[sys.argv[1]](Step())
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
