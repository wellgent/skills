#!/usr/bin/env python3
"""The weekly brain summary: code gathers and renders every fact, the agent writes the change narrative.

The summary-weekly agent turn runs, in order:

  routine.py begin summary-weekly             the run id (brain-routines)
  summary.py gather --run <run_id>            the packet of the week's facts, zero LLM
  ... the agent writes the narrative file the packet names ...
  summary.py post --run <run_id> --dry-run    check the narrative and print the rendered summary
  summary.py post --run <run_id>              post it to the summary channel, then end the run

`post --fallback` renders the changes from commit subjects instead of a narrative.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True  # routines write nothing into the published copy
SCRIPTS = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS.parent
SKILLS = SKILL_DIR.parent
sys.path[:0] = [str(SKILLS / 'brain-routines' / 'scripts'), str(SKILLS / 'brain-health' / 'scripts'),
                str(SKILLS / 'brain-change-review' / 'scripts')]
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402
import routine as runner  # noqa: E402
from health import cron_sets  # noqa: E402
import judge_misses  # noqa: E402

CONF = json.loads((SKILL_DIR / 'config.json').read_text())
NARR = CONF['narrative']
LIMIT = 1900
SHA_TOKEN = re.compile(r'\{([0-9a-f]{7,40})\}')
ISSUE_TOKEN = re.compile(r'\{#(\d+)\}')
OPTION = re.compile(r'^(\d+)\.\s+\*\*(.+?)\*\*(?:\s+-\s+(.*))?$', re.M)
RECOMMENDED = re.compile(r'^\*\*Recommended:?\*\*:?\s*(?:option\s*)?(\d+)\b[,.:]?\s*(.*)$', re.M | re.I)
FINDING = re.compile(r'^\*\*Finding\.?\*\*\s*(.+)$', re.M)
URL = re.compile(r'https?://')
KIND_ORDER = ['archive move', 'restore', 'page deletion', 'span deletion', 'filing move', 'edit', 'other']


# helpers

def git(cfg, *args, timeout=180):
    return lib.clone_git(cfg, *args, timeout=timeout)


def rev(cfg):
    return f'origin/{cfg.get("branch", "main")}'


def local(ts, tz, with_time=False):
    d = dt.datetime.fromtimestamp(ts, ZoneInfo(tz))
    return d.strftime('%a %-d %b' + (' %H:%M' if with_time else ''))


def clip(text, n):
    text = ' '.join((text or '').split())
    if len(text) <= n:
        return text
    cut = text[:n]
    stop = cut.rfind('. ')
    return cut[:stop + 1] if stop > n // 2 else cut.rstrip() + '...'


def tokens(n):
    n = n or 0
    return f'{n / 1e6:.1f}M' if n >= 1e6 else f'{n / 1e3:.0f}k' if n >= 1e3 else str(n)


def fires(expr, tz, start, end):
    """How many times the cron expression fires in [start, end), in tz."""
    (minutes, hours, dom, months, dow), either_star = cron_sets(expr)
    zone = ZoneInfo(tz)
    count, t = 0, -(-int(start) // 60) * 60
    while t < end:
        d = dt.datetime.fromtimestamp(t, zone)
        if d.minute in minutes and d.hour in hours and d.month in months:
            day, week = d.day in dom, d.isoweekday() % 7 in dow
            if (day and week) if either_star else (day or week):
                count += 1
        t += 60
    return count


# gather

def page_counts(cfg, ref):
    counts = {}
    if not ref:
        return counts
    for path in git(cfg, 'ls-tree', '-r', '--name-only', ref).splitlines():
        if path.endswith('.md') and '/' in path:
            area = path.split('/', 1)[0]
            counts[area] = counts.get(area, 0) + 1
    return counts


def brain(cfg, start, end):
    """Pages per area now and at the window start, commits per writer, and the ledger areas."""
    since, until = f'--since={lib.iso(start)}', f'--until={lib.iso(end)}'
    before = git(cfg, 'rev-list', '-1', f'--before={lib.iso(start)}', rev(cfg)) or None
    now, then = page_counts(cfg, rev(cfg)), page_counts(cfg, before)
    known = set(CONF['areas']) | set(CONF['ledger']) | set(CONF['not_areas'])
    areas = [{'area': a, 'pages': now.get(a, 0), 'change': now.get(a, 0) - then.get(a, 0)}
             for a in CONF['areas'] + sorted(a for a in set(now) | set(then) if a not in known)]
    writers = {}
    for name in git(cfg, 'log', since, until, '--format=%an', rev(cfg)).splitlines():
        writers[name] = writers.get(name, 0) + 1
    ledger = []
    for area in CONF['ledger']:
        by = {}
        for name in git(cfg, 'log', since, until, '--format=%an', rev(cfg), '--', f'{area}/').splitlines():
            by[name] = by.get(name, 0) + 1
        last = git(cfg, 'log', '-1', '--format=%ct%x02%an%x02%s', rev(cfg), '--', f'{area}/')
        ct, who, subject = last.split('\x02', 2) if last else (0, '', '')
        ledger.append({'area': area, 'pages': now.get(area, 0), 'change': now.get(area, 0) - then.get(area, 0),
                       'commits': sum(by.values()), 'by': by, 'last_at': int(ct), 'last_by': who, 'last_subject': subject})
    return {'areas': areas, 'total': sum(r['pages'] for r in areas), 'total_change': sum(r['change'] for r in areas),
            'writers': dict(sorted(writers.items(), key=lambda kv: -kv[1])), 'ledger': ledger}


def classify(op, path, files):
    if not op:
        return 'other'
    if op in ('UPDATE', 'ADD'):
        return 'edit'
    if op == 'DELETE':
        return 'page deletion' if files.get(path, ('',))[0] == 'D' else 'span deletion'
    if op == 'MOVE':
        to = files.get(path, ('', None))[1] or next((p for p, (s, _) in files.items() if s == 'A'), '')
        if to.startswith('archive/'):
            return 'archive move'
        if path.startswith('archive/'):
            return 'restore'
        return 'filing move'
    return 'other'


def changes(cfg, start, end):
    """The maintenance writer's commits in the window, by workflow, oldest first."""
    author = git(cfg, 'config', 'user.name')
    raw = git(cfg, 'log', f'--since={lib.iso(start)}', f'--until={lib.iso(end)}', f'--author=^{re.escape(author)} <',
              '-M', '--name-status', '--format=%x01%H%x02%ct%x02%B%x03', rev(cfg))
    out = {}
    for chunk in raw.split('\x01'):
        if not chunk.strip():
            continue
        sha, ct, rest = chunk.split('\x02', 2)
        body, _, names = rest.partition('\x03')
        files = {}
        for line in names.strip().splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                files[parts[1]] = (parts[0][0], parts[2] if len(parts) > 2 else None)
                if len(parts) > 2:
                    files.setdefault(parts[2], ('A', None))
        routine = re.search(r'^Routine: (\S+)', body, re.M)
        op = re.search(r'^Op: (\w+) (\S+)', body, re.M)
        reason = re.search(r'^Reason: (.+)$', body, re.M)
        path = op.group(2) if op else None
        rid = routine.group(1) if routine else None
        workflow = judge_misses.workflow_of(cfg, rid) if rid else 'other'
        out.setdefault(workflow, []).append({
            'sha': sha[:7], 'url': lib.commit_url(cfg, sha), 'at': int(ct), 'routine': rid,
            'op': op.group(1) if op else None, 'path': path, 'kind': classify(op and op.group(1), path, files),
            'subject': body.splitlines()[0] if body.strip() else '',
            'reason': clip(reason.group(1), 400) if reason else '',
            'owner_choice': bool(reason and reason.group(1).startswith('Owner chose')),
        })
    for items in out.values():
        items.reverse()
    return out


def cron_runs(cfg, job_id, start, end):
    o = cfg['openclaw']
    try:
        raw = lib.run([o['bin'], 'cron', 'runs', '--id', job_id, '--limit', '200', '--json'], timeout=90)
        entries = json.loads(raw[raw.find('{'):]).get('entries', [])
    except (Failed, ValueError):
        return None
    return [e for e in entries if start * 1000 <= (e.get('runAtMs') or 0) < end * 1000]


def run_status(cfg, d, meta, state):
    if meta.get('status'):
        return meta['status']
    if state.get('last_run_id') == meta['run_id'] and state.get('running'):
        return 'running'
    return 'partial' if any(e['kind'] == 'problem' for e in lib.read_journal(cfg, meta['run_id'])) else 'ok'


def routines(cfg, start, end):
    """The routine health grid and the token use of every agent cron in the window."""
    m = lib.manifest(cfg)
    jobs = runner.find_jobs(cfg)
    grid, load_rows, problems = [], {}, []
    runs_dir = lib.state_dir(cfg) / 'runs'
    for r in m['routines']:
        rid = r['id']
        job = jobs.get(runner.declaration_key(cfg, rid))
        state = lib.read_json(lib.state_dir(cfg) / 'routines' / f'{rid}.json', {})
        enabled = bool(job) and job.get('enabled', True) and r.get('enabled', True)
        due = fires(r['schedule'], m['timezone'], max(start, (job or {}).get('createdAtMs', 0) / 1000), end) if enabled else 0
        entries = cron_runs(cfg, job['id'], start, end) if job else []
        if entries is None:
            problems.append(f'cron runs of `{rid}` unreadable')
            entries = []
        statuses, gated = [], 0
        for d in sorted(runs_dir.glob(f'{rid}-*')):
            meta = lib.read_json(d / 'run.json')
            if meta and re.fullmatch(rf'{re.escape(rid)}-\d{{8}}T\d{{6}}Z-[0-9a-f]+', meta.get('run_id', '')) \
                    and start <= meta.get('started_at', 0) < end:
                statuses.append(run_status(cfg, d, meta, state))
                gated += statuses[-1] == 'deferred' and not meta.get('forced')  # a scheduled fire the guard held back
        scheduled = sum(1 for e in entries if not str(e.get('runId', '')).startswith('manual:'))
        cron_errors = sum(1 for e in entries if e.get('status') not in ('ok', None))
        grid.append({'routine': rid, 'workflow': r['workflow'], 'enabled': enabled, 'cron': bool(job), 'due': due,
                     'scheduled_runs': scheduled, 'missed': max(0, due - scheduled - gated),
                     'runs': len(statuses) - statuses.count('deferred'), 'deferred': statuses.count('deferred'),
                     'ok': statuses.count('ok'), 'partial': statuses.count('partial'),
                     'failed': max(statuses.count('failed'), cron_errors), 'running': statuses.count('running'),
                     'last_status': state.get('status'), 'last_at': state.get('finished_at')})
        if r['kind'] == 'agentTurn':
            load_rows[rid] = usage_of(entries)
    other = {'runs': 0, 'input': 0, 'cached': 0, 'output': 0}
    raw = lib.run([cfg['openclaw']['bin'], 'cron', 'list', '--all', '--json'], timeout=90)
    for job in json.loads(raw[raw.find('{'):]).get('jobs', []):
        if (job.get('declarationKey') or '').startswith(runner.declaration_key(cfg, '')) or (job.get('payload') or {}).get('kind') != 'agentTurn':
            continue
        entries = cron_runs(cfg, job['id'], start, end) or []
        for k, v in usage_of(entries).items():
            other[k] += v
    return grid, load_rows, other, problems


def usage_of(entries):
    out = {'runs': len(entries), 'input': 0, 'cached': 0, 'output': 0}
    for e in entries:
        u = e.get('usage') or {}
        out['input'] += u.get('input_tokens') or 0
        out['cached'] += u.get('cache_read_tokens') or 0
        out['output'] += u.get('output_tokens') or 0
    return out


def engine_usage(cfg, run_dir):
    """The engine's own chat calls over the window, which ride the engine's chat subscription."""
    rc = lib.read_json(SKILLS / 'gbrain-host-reconciler' / 'config.json')
    try:
        out = lib.run([rc['gbrain_bin'], 'call', 'get_usage', json.dumps({'days': CONF['window_days']})], cwd=run_dir, timeout=120)
        totals = json.loads(out[out.find('{'):]).get('totals', {})
    except (Failed, ValueError):
        return None
    return {'calls': totals.get('calls', 0), 'input': totals.get('input_tokens', 0), 'output': totals.get('output_tokens', 0)}


def window_reading(cfg):
    """The subscription windows now, or the last reading an agentTurn logged."""
    snap = lib.usage(cfg)
    if snap:
        return snap, lib.iso()
    path = lib.state_dir(cfg) / 'load.jsonl'
    if path.exists():
        for line in reversed(path.read_text().splitlines()):
            rec = json.loads(line)
            if rec.get('end'):
                return rec['end'], rec.get('at')
    return None, None


def eval_trend(cfg, start):
    path = lib.state_dir(cfg) / 'eval' / 'history.jsonl'
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            rec = json.loads(line)
            results = [r for r in rec.get('results', {}).values() if 'error' not in r]
            critical = [r for r in results if r.get('critical')]
            rows.append({'run_id': rec.get('run_id'), 'at': rec.get('at'), 'set_version': rec.get('set_version'),
                         'complete': rec.get('complete'), 'gate': rec.get('gate'), 'cases': len(results),
                         'recall': round(sum(r['recall'] for r in results) / len(results), 2) if results else None,
                         'top1': round(sum(r['hit1'] for r in results) / len(results), 2) if results else None,
                         'critical_pass': sum(1 for r in critical if r.get('top1', r.get('hit1')) == 1), 'critical': len(critical)})
    rows = rows[-CONF['eval_runs']:]
    this_week = any(dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00')).timestamp() >= start for r in rows if r.get('at'))
    return {'runs': rows, 'this_week': this_week}


def judge_report(cfg):
    path = lib.state_dir(cfg) / judge_misses.REPORT
    report = lib.read_json(path)
    fresh = report and (lib.now() - dt.datetime.fromisoformat(report['computed_at'].replace('Z', '+00:00')).timestamp()
                        < CONF['judge_miss_max_age_hours'] * 3600)
    if not fresh:
        try:
            report = judge_misses.compute(cfg, json.loads((SKILLS / 'brain-change-review' / 'config.json').read_text()))
        except Failed as error:
            if not report:
                raise
            report['stale_reason'] = str(error)
    return report


def attention(cfg):
    raw = lib.gh(cfg, 'issue', 'list', '--repo', cfg['github_repo'], '--state', 'open', '--label', 'needs-attention',
                 '--json', 'number,title,url,body,createdAt,labels', '--limit', '200')
    items = []
    for i in json.loads(raw or '[]'):
        body = i.get('body') or ''
        options = {int(n): {'label': label.strip(), 'detail': (detail or '').strip()} for n, label, detail in OPTION.findall(body)}
        rec = RECOMMENDED.search(body)
        number = int(rec.group(1)) if rec else None
        finding = FINDING.search(body)
        created = dt.datetime.fromisoformat(i['createdAt'].replace('Z', '+00:00')).timestamp()
        items.append({
            'number': i['number'], 'title': i['title'], 'url': i['url'], 'created_at': i['createdAt'],
            'age_days': int((lib.now() - created) // lib.DAY),
            'workflow': next((lab['name'].split(':', 1)[1] for lab in i.get('labels', []) if lab['name'].startswith('workflow:')), None),
            'finding': clip(finding.group(1), 600) if finding else clip(body, 600),
            'options': options, 'recommended': number,
            'recommended_label': options.get(number, {}).get('label') if number else None,
            'recommended_reason': clip(rec.group(2).rstrip('.'), 220) if rec and rec.group(2) else '',
        })
    return sorted(items, key=lambda x: x['created_at'])


def cmd_gather(cfg, args):
    meta = lib.current_run(cfg, args.run)
    m = lib.manifest(cfg)
    end = meta['started_at']
    start = end - CONF['window_days'] * lib.DAY
    d = lib.run_dir(cfg, meta['run_id'])
    problems = []
    packet = {'run_id': meta['run_id'], 'repo': cfg['github_repo'], 'timezone': m['timezone'],
              'window': {'start': start, 'end': end, 'start_iso': lib.iso(start), 'end_iso': lib.iso(end)},
              'narrative_file': str(d / 'narrative.json')}

    def part(name, fn, *a):
        try:
            packet[name] = fn(*a)
        except (Failed, OSError, ValueError, KeyError) as error:
            problems.append(f'{name}: {error}')
            packet[name] = None

    part('changes', changes, cfg, start, end)
    part('brain', brain, cfg, start, end)
    part('attention', attention, cfg)
    part('eval', eval_trend, cfg, start)
    part('judge_misses', judge_report, cfg)
    try:
        grid, load_rows, other, grid_problems = routines(cfg, start, end)
        problems += grid_problems
        snap, read_at = window_reading(cfg)
        packet['routines'] = grid
        packet['load'] = {'windows': snap, 'read_at': read_at, 'maintenance': lib.window_deltas(cfg, start, end), 'routines': load_rows,
                          'other_agent_crons': other, 'engine_chat': engine_usage(cfg, d)}
    except (Failed, OSError, ValueError, KeyError) as error:
        problems.append(f'routines: {error}')
        packet['routines'] = packet['load'] = None
    packet['problems'] = problems
    for p in problems:
        lib.journal(cfg, meta['run_id'], 'problem', text=f'Summary data: {p}')
    lib.atomic(d / 'packet.json', packet)
    ch = packet['changes'] or {}
    print(json.dumps({
        'packet': str(d / 'packet.json'), 'narrative_file': packet['narrative_file'],
        'workflows': {wf: len(items) for wf, items in ch.items()},
        'must_cite': must_cite(ch),
        'attention': [i['number'] for i in packet['attention'] or []],
        'problems': problems,
    }, ensure_ascii=False, indent=2))
    return 0


def must_cite(ch):
    """Commits the narrative has to link: every archive move and restore, and page deletions of a small week."""
    out = []
    for items in ch.values():
        out += [c['sha'] for c in items if c['kind'] in ('archive move', 'restore')]
        deletions = [c['sha'] for c in items if c['kind'] == 'page deletion']
        if len(deletions) <= NARR['cite_all_deletions_up_to']:
            out += deletions
    return out


# render

def check(p, n):
    """Problems with the agent's narrative; an empty list means it renders."""
    errors = []
    ch = p.get('changes') or {}
    shas = {c['sha'] for items in ch.values() for c in items}
    issues = {str(i['number']) for i in p.get('attention') or []}
    if not isinstance(n, dict):
        return ['the narrative is not a JSON object']
    head = n.get('headline') or ''
    if not head.strip() or len(head) > NARR['headline_chars']:
        errors.append(f'headline must be 1 to {NARR["headline_chars"]} characters')
    workflows = n.get('workflows') or {}
    for wf in ch:
        if not workflows.get(wf):
            errors.append(f'workflow `{wf}` has {len(ch[wf])} commits and no bullets')
    cited = set()
    for wf, bullets in workflows.items():
        if wf not in ch:
            errors.append(f'workflow `{wf}` has no commits this week')
            continue
        if not isinstance(bullets, list) or len(bullets) > NARR['bullets_per_workflow']:
            errors.append(f'workflow `{wf}` needs a list of at most {NARR["bullets_per_workflow"]} bullets')
            continue
        for b in bullets:
            text = SHA_TOKEN.sub('', ISSUE_TOKEN.sub('', b))
            if len(text) > NARR['bullet_chars']:
                errors.append(f'a `{wf}` bullet is longer than {NARR["bullet_chars"]} characters without its links')
            if len(SHA_TOKEN.findall(b)) > NARR['links_per_bullet']:
                errors.append(f'a `{wf}` bullet cites more than {NARR["links_per_bullet"]} commits')
            if URL.search(b):
                errors.append(f'a `{wf}` bullet carries a raw URL; cite commits as {{sha}} and issues as {{#n}}')
            for s in SHA_TOKEN.findall(b):
                match = [x for x in shas if x.startswith(s[:7])]
                if not match:
                    errors.append(f'{{{s}}} is not a commit of this week')
                cited.update(match)
            for num in ISSUE_TOKEN.findall(b):
                if num not in issues:
                    errors.append(f'{{#{num}}} is not an open needs-attention issue')
    missing = [s for s in must_cite(ch) if s not in cited]
    if missing:
        errors.append('cite every archive move, restore and listed page deletion; missing: ' + ', '.join(missing))
    for num, gist in (n.get('attention') or {}).items():
        if str(num) not in issues:
            errors.append(f'attention gist for #{num}, which is not an open needs-attention issue')
        elif len(gist or '') > NARR['gist_chars']:
            errors.append(f'attention gist for #{num} is longer than {NARR["gist_chars"]} characters')
    return errors


def fallback(p):
    """A narrative from commit subjects, for when the agent's narrative is missing or invalid."""
    ch = p.get('changes') or {}
    workflows = {}
    for wf, items in ch.items():
        bullets = []
        for kind in KIND_ORDER:
            group = [c for c in items if c['kind'] == kind]
            if not group:
                continue
            if len(group) <= 3:
                bullets += [f'{c["subject"]} {{{c["sha"]}}}' for c in group]
            else:
                links = ' '.join(f'{{{c["sha"]}}}' for c in group[:NARR['links_per_bullet']])
                more = f' and {len(group) - NARR["links_per_bullet"]} more' if len(group) > NARR['links_per_bullet'] else ''
                bullets.append(f'{len(group)} {kind}s, for example "{group[0]["subject"]}": {links}{more}')
        workflows[wf] = bullets[:NARR['bullets_per_workflow']]
    total = sum(len(v) for v in ch.values())
    return {'headline': f'{total} maintenance commits and {len(p.get("attention") or [])} open needs-attention items this week.',
            'workflows': workflows, 'attention': {}}


def links(p, text):
    by_sha = {c['sha']: c['url'] for items in (p.get('changes') or {}).values() for c in items}
    issues = {str(i['number']): i['url'] for i in p.get('attention') or []}

    def sha(m):
        s = m.group(1)[:7]
        return f'[{s}](<{by_sha[s]}>)' if s in by_sha else s

    text = SHA_TOKEN.sub(sha, text)
    return ISSUE_TOKEN.sub(lambda m: f'[#{m.group(1)}](<{issues[m.group(1)]}>)' if m.group(1) in issues else f'#{m.group(1)}', text)


def count_line(items):
    kinds = {}
    for c in items:
        kinds[c['kind']] = kinds.get(c['kind'], 0) + 1
    parts = [f'{kinds[k]} {k}{"s" if kinds[k] != 1 else ""}' for k in KIND_ORDER if kinds.get(k)]
    owner = sum(1 for c in items if c['owner_choice'])
    return f'{len(items)} commit{"s" if len(items) != 1 else ""}: ' + ', '.join(parts) + (f'; {owner} from your replies' if owner else '')


def render(cfg, p, n):
    tz = p['timezone']
    w = p['window']
    blocks = []
    head = [f'# {cfg["brain"]} weekly summary', f'-# {local(w["start"], tz, True)} to {local(w["end"], tz, True)} · run `{p["run_id"]}`', '',
            links(p, n['headline'])]
    if p.get('problems'):
        head.append('-# Missing data: ' + '; '.join(p['problems']))
    blocks.append('\n'.join(head))

    att = p.get('attention')
    if att is None:
        blocks.append('## Needs you\nThe needs-attention issues could not be read this week.')
    elif not att:
        blocks.append('## Needs you\nNo open needs-attention issue.')
    else:
        blocks.append(f'## Needs you: {len(att)} open\nReply on each issue with the option number; the workflow\'s next run applies it.')
        for i in att:
            lines = []
            age = 'today' if i['age_days'] == 0 else f'{i["age_days"]} day{"s" if i["age_days"] != 1 else ""} old'
            lines.append(f'- **[#{i["number"]}](<{i["url"]}>) {i["title"]}** ({i["workflow"] or "no workflow"}, {age})')
            gist = (n.get('attention') or {}).get(str(i['number']))
            if gist:
                lines.append(f'  - {gist}')
            if i['recommended_label']:
                lines.append(f'  - Recommended **{i["recommended"]}. {i["recommended_label"]}**' + (f': {i["recommended_reason"]}' if i['recommended_reason'] else ''))
            else:
                lines.append('  - No recommended option in the issue.')
            blocks.append('\n'.join(lines))

    grid = p.get('routines')
    if grid is not None:
        rows = [f'{"routine":<17} {"due":>3} {"runs":>4} {"ok":>3} {"part":>4} {"fail":>4} {"def":>3} {"miss":>4}  last']
        for g in grid:
            last = f'{g["last_status"] or "-"} {local(dt.datetime.fromisoformat(g["last_at"].replace("Z", "+00:00")).timestamp(), tz, True)}' \
                if g.get('last_at') else 'never'
            if not g['cron']:
                last = 'NO CRON'
            elif not g['enabled']:
                last = 'disabled'
            rows.append(f'{g["routine"]:<17} {g["due"]:>3} {g["runs"]:>4} {g["ok"]:>3} {g["partial"]:>4} {g["failed"]:>4} {g["deferred"]:>3} {g["missed"]:>4}  {last}')
        lines = ['## Routines', '```', *rows, '```']
        red = [g['routine'] for g in grid if g['partial'] or g['failed'] or g['missed'] or not g['cron']]
        lines.append('All routines green.' if not red else 'Not green: ' + ', '.join(f'`{r}`' for r in red) + '. Their run updates and `#ops-alerts` carry the detail.')
        lines.append('-# due = scheduled runs in the window, runs = every started run including forced ones, def = runs the subscription guard deferred, '
                     'miss = due runs the cron never started.')
        lines.append(load_line(cfg, p))
        blocks.append('\n'.join(lines))

    ch = p.get('changes')
    if ch is None:
        blocks.append('## Changes by workflow\nThe maintenance commits could not be read this week.')
    elif not ch:
        blocks.append('## Changes by workflow\nNo maintenance commit this week.')
    else:
        blocks.append('## Changes by workflow')
        for wf in sorted(ch, key=lambda k: -len(ch[k])):
            blocks.append(f'**{wf}** · {count_line(ch[wf])}')
            blocks += [f'- {links(p, b)}' for b in (n.get('workflows') or {}).get(wf, [])]

    b = p.get('brain')
    if b:
        width = max(len(r['area']) for r in b['areas']) + 1
        rows = [f'{"area":<{width}} {"pages":>6} {"week":>6}']
        rows += [f'{r["area"]:<{width}} {r["pages"]:>6} {r["change"]:>+6}' for r in b['areas'] if r['pages'] or r['change']]
        rows.append(f'{"total":<{width}} {b["total"]:>6} {b["total_change"]:>+6}')
        lines = ['## Brain', '```', *rows, '```', 'Ledger areas, kept by their own loops:']
        for led in b['ledger']:
            by = ', '.join(f'{k} {v}' for k, v in sorted(led['by'].items(), key=lambda kv: -kv[1]))
            last = f'last change {local(led["last_at"], tz)} by {led["last_by"]}: "{clip(led["last_subject"], 90)}"' if led['last_at'] else 'no commit yet'
            lines.append(f'- **{led["area"]}/** {led["pages"]} pages ({led["change"]:+}), '
                         + (f'{led["commits"]} commits this week ({by})' if led['commits'] else 'no commit this week') + f'; {last}')
        lines.append('Commits this week by writer: ' + ', '.join(f'{k} {v}' for k, v in b['writers'].items()) + '.')
        blocks.append('\n'.join(lines))

    lines = ['## Search and judges']
    ev = p.get('eval')
    if ev and ev['runs']:
        lines += ['```', f'{"run":<11} {"set":>3} {"cases":>5} {"recall@10":>9} {"top-1":>5} {"critical":>8}  gate']
        for r in ev['runs']:
            at = local(dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00')).timestamp(), tz) if r.get('at') else '-'
            lines.append(f'{at:<11} {"v" + str(r["set_version"]):>3} {r["cases"]:>5} {r["recall"]:>9.2f} {r["top1"]:>5.2f} '
                         f'{str(r["critical_pass"]) + "/" + str(r["critical"]):>8}  {r["gate"]}{"" if r["complete"] else " (incomplete)"}')
        lines.append('```')
        if not ev['this_week']:
            lines.append('No retrieval eval ran this week.')
    else:
        lines.append('No retrieval eval run on record.')
    jm = p.get('judge_misses')
    if jm:
        wfs = jm.get('workflows') or {}
        parts = [f'{wf} {s["misses"]} of {s["edits"]} edits ({s["rate"]:.0%}), {s["open"]} still in the window' for wf, s in sorted(wfs.items())]
        lines.append(f'Judge misses over {jm["lookback_days"]} days, each edit watched {jm["window_days"]} days, '
                     f'threshold {jm["threshold"]:.0%}: ' + ('; '.join(parts) if parts else 'no maintenance edit yet') + '.')
        for miss in (jm.get('misses') or [])[:5]:
            lines.append(f'- {miss["workflow"]} {miss["op"]} `{miss["path"]}` [edit](<{miss["url"]}>): {miss["by_author"]} {miss["how"]} [here](<{miss["by_url"]}>)')
    else:
        lines.append('Judge misses could not be read this week.')
    blocks.append('\n'.join(lines))
    return blocks


def load_line(cfg, p):
    ld = p.get('load') or {}
    parts = []
    for provider, s in (ld.get('windows') or {}).items():
        for label, used in (s.get('windows') or {}).items():
            parts.append(f'{provider} {label.lower()} window {used}% used')
            moved = (ld.get('maintenance') or {}).get(f'{provider} {label.lower()}')
            if moved:
                parts.append(f'maintenance turns moved it {sum(moved.values()):g} points this week ('
                             + ', '.join(f'{rid} {pts:g}' for rid, pts in sorted(moved.items(), key=lambda kv: -kv[1])) + ')')
    rows = ld.get('routines') or {}
    total = {k: sum(r[k] for r in rows.values()) for k in ('runs', 'input', 'cached', 'output')}
    if total['runs']:
        per = ', '.join(f'{rid} {tokens(r["input"])}' for rid, r in sorted(rows.items(), key=lambda kv: -kv[1]['input']) if r['runs'])
        parts.append(f'maintenance turns {total["runs"]} runs, {tokens(total["input"])} input ({tokens(total["cached"])} cached) '
                     f'and {tokens(total["output"])} output tokens ({per})')
    other = ld.get('other_agent_crons') or {}
    if other.get('runs'):
        parts.append(f'other agent crons {other["runs"]} runs, {tokens(other["input"])} input')
    engine = ld.get('engine_chat')
    if engine and engine['calls']:
        parts.append(f'engine chat on its own subscription {engine["calls"]} calls, {tokens(engine["input"])} input and {tokens(engine["output"])} output tokens')
    issue = f'https://github.com/{cfg["github_repo"]}/issues/{CONF["budget_issue"]}'
    return ('**Subscription load:** ' + '; '.join(parts) + '.' if parts else '**Subscription load:** no usage reported.') + \
        f' The agent\'s chat shares its window. The budget rules are in [#{CONF["budget_issue"]}](<{issue}>).'


def pack(blocks):
    """Discord messages under the limit, never splitting a block unless it alone is too long."""
    messages, current = [], ''
    for block in blocks:
        pieces = [block] if len(block) <= LIMIT else split(block)
        for piece in pieces:
            if current and len(current) + len(piece) + 2 > LIMIT:
                messages.append(current)
                current = ''
            sep = '\n' if piece.startswith('- ') else '\n\n'  # a list item continues the list above it
            current = f'{current}{sep}{piece}' if current else piece
    if current:
        messages.append(current)
    return messages


def split(block):
    out, current, fence = [], '', False
    for line in block.splitlines():
        line = line[:LIMIT - 10]
        if current and len(current) + len(line) + 5 > LIMIT:
            out.append(current + ('\n```' if fence else ''))
            current = '```' if fence else ''
        current = f'{current}\n{line}' if current else line
        if line.startswith('```'):
            fence = not fence
    if current:
        out.append(current)
    return out


def cmd_post(cfg, args):
    if args.dry_run:
        meta = lib.read_json(lib.run_dir(cfg, args.run) / 'run.json')
        if not meta:
            raise Failed(f'unknown run {args.run}')
    else:
        meta = lib.current_run(cfg, args.run)
    d = lib.run_dir(cfg, meta['run_id'])
    p = lib.read_json(d / 'packet.json')
    if not p:
        raise Failed(f'run {meta["run_id"]} has no packet; run gather first')
    used_fallback = args.fallback
    if args.fallback:
        n = fallback(p)
    else:
        n = lib.read_json(Path(p['narrative_file']))
        errors = check(p, n) if n is not None else [f'no narrative at {p["narrative_file"]}']
        if errors:
            print(json.dumps({'errors': errors}, ensure_ascii=False, indent=2))
            return 1
    messages = pack(render(cfg, p, n))
    text = '\n\n'.join(messages)
    if args.dry_run:
        print(text)
        print(json.dumps({'messages': len(messages), 'characters': len(text)}), file=sys.stderr)
        return 0
    (d / 'summary.md').write_text(text + '\n')
    channel = cfg['channels']['summary']
    error = None
    for k, msg in enumerate(messages):
        error = lib.post(cfg, channel, msg, silent=k > 0)
        if error:
            break
    if error:
        lib.journal(cfg, meta['run_id'], 'problem', text=f'Posting the summary failed: {error}')
    if used_fallback:
        lib.journal(cfg, meta['run_id'], 'note', text='The change narrative was rendered from commit subjects.')
    w, ch = p['window'], p.get('changes') or {}
    summary = (f'posted the summary of {local(w["start"], p["timezone"])} to {local(w["end"], p["timezone"])} in {len(messages)} messages: '
               f'{sum(len(v) for v in ch.values())} maintenance commits, {len(p.get("attention") or [])} open needs-attention items')
    runner.end(cfg, meta, 'partial' if error else 'ok', summary, {})
    print(json.dumps({'ended': meta['run_id'], 'posted': not error, 'messages': len(messages), 'error': error}, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('gather').add_argument('--run', required=True)
    c = sub.add_parser('post')
    c.add_argument('--run', required=True)
    c.add_argument('--dry-run', action='store_true', help='check and print the rendered summary; post nothing, end nothing')
    c.add_argument('--fallback', action='store_true', help='render the changes from commit subjects instead of the narrative')
    args = p.parse_args()
    cfg = lib.config()
    return {'gather': cmd_gather, 'post': cmd_post}[args.command](cfg, args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
