#!/usr/bin/env python3
"""The daily digest in #brain-review: code gathers and renders every fact, the agent writes the plain sentences.

The digest-daily agent turn runs, in order:

  routine.py begin digest-daily              the run id (brain-routines)
  digest.py gather --run <run_id>            the packet of the window's facts, zero LLM; "news": false ends quietly
  ... the agent writes the narrative file the packet names ...
  digest.py post --run <run_id> --dry-run    check the narrative and print the rendered digest
  digest.py post --run <run_id>              post it to #brain-review, then end the run

`post --fallback` renders the sentences from the facts instead of a narrative.
`post --quiet` ends a run with nothing to report without posting.
The owner's answers come back through `answer`, from the channel or a chat session; `items` lists the last digest's items,
`edition weekly` makes the next run the weekly edition, and `preview` prints what a run starting now would post.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True  # routines write nothing into the published copy
SCRIPTS = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS.parent
SKILLS = SKILL_DIR.parent
sys.path[:0] = [str(SKILLS / 'brain-routines' / 'scripts')]
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402
import routine as runner  # noqa: E402

CONF = json.loads((SKILL_DIR / 'config.json').read_text())
NARR = CONF['narrative']
WATCH = CONF['watch']
LIMIT = 1900
SHA = re.compile(r'^[0-9a-f]{7,40}$')
OPTION = re.compile(r'^(\d+)\.\s+\*\*(.+?)\*\*(?:\s+-\s+(.*))?$', re.M)
RECOMMENDED = re.compile(r'^\*\*Recommended:?\*\*:?\s*(?:option\s*)?(\d+)\b[,.:]?\s*(.*)$', re.M | re.I)
FINDING = re.compile(r'^\*\*Finding\.?\*\*\s*(.+)$', re.M)
RAW = [(re.compile(r'https?://'), 'a raw URL'), (re.compile(r'\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b'), 'a commit id'),
       (re.compile(r'\b[\w.-]+/[\w./-]+\.(?:md|json|py)\b'), 'a file path'), (re.compile(r'\brevert\b', re.I), 'a revert instruction'),
       (re.compile(r'[{}`]'), 'markup')]
YES = re.compile(r'^\W*(yes|y|ok|okay|sure|agreed|approve[d]?|go ahead|do it|recommended|fine)\b', re.I)
KIND_WORDS = {'archive move': 'Moved to the archive', 'restore': 'Restored from the archive', 'page deletion': 'Deleted',
              'span deletion': 'Removed text from', 'filing move': 'Refiled', 'edit': 'Edited', 'other': 'Changed'}
# How upstream's changelog marks a release: in its bold headline, or in the lead paragraph.
RELEASE = re.compile(r'^## \[([^\]]+)\](?:[^\n\d]*(\d{4}-\d{2}-\d{2}))?[^\n]*\n(.*?)(?=^## \[|\Z)', re.M | re.S)
SECURITY_HEADLINE = re.compile(r'\bsecurity\b|vulnerab|\bCVE-\d|\badvisor(?:y|ies)\b|escalation'
                               r'|(?:leak|print|expos|reveal)\w*\b[^.]{0,60}\b(?:secret|token|credential|password)s?\b', re.I)
SECURITY_LEAD = re.compile(r'\bsecurity (?:fix|hardening|pass|advisor|issue|upgrade|priority)|vulnerab|\bCVE-\d', re.I)
DEFAULT_ON = re.compile(r'\b(?:on|enabled) by default\b|\bdefault-on\b', re.I)


# helpers

def git(cfg, *args, timeout=180):
    return lib.clone_git(cfg, *args, timeout=timeout)


def rev(cfg):
    return f'origin/{cfg.get("branch", "main")}'


def local(ts, tz, fmt='%a %-d %b'):
    return dt.datetime.fromtimestamp(ts, ZoneInfo(tz)).strftime(fmt)


def parse_iso(text):
    return dt.datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()


def clip(text, n):
    text = ' '.join((text or '').split())
    if len(text) <= n:
        return text
    cut = text[:n]
    stop = cut.rfind('. ')
    return cut[:stop + 1] if stop > n // 2 else cut.rstrip() + '...'


def digest_dir(cfg):
    path = lib.state_dir(cfg) / 'digest'
    path.mkdir(exist_ok=True, mode=0o700)
    return path


def load_state(cfg):
    return lib.read_json(digest_dir(cfg) / 'state.json', {})


def save_state(cfg, state):
    lib.atomic(digest_dir(cfg) / 'state.json', state)


def manifest_routines(cfg):
    return {r['id']: r for r in lib.manifest(cfg)['routines']}


def workflow_of(cfg, rid):
    """The workflow of a commit's routine id."""
    r = manifest_routines(cfg).get(rid)
    return r['workflow'] if r else rid.split('-', 1)[0]


# gather

def page_title(cfg, ref, path):
    """A page's title at a commit: its frontmatter title, else its first heading, else its file name."""
    code, text, _ = lib.clone_git(cfg, 'show', f'{ref}:{path}', check=False)
    if code == 0 and path.endswith('.md'):
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.M) or re.search(r'^#\s+(.+)$', text, re.M)
        if m:
            return m.group(1).strip()
    return Path(path).stem.replace('-', ' ') if path.endswith('.md') else path


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
    """The maintenance writer's commits in the window, oldest first, each with the page it touched and its link."""
    author = git(cfg, 'config', 'user.name')
    raw = git(cfg, 'log', f'--since={lib.iso(start)}', f'--until={lib.iso(end)}', f'--author=^{re.escape(author)} <',
              '-M', '--name-status', '--format=%x01%H%x02%P%x02%ct%x02%B%x03', rev(cfg))
    web = f'https://github.com/{cfg["github_repo"]}/blob'
    out = []
    for chunk in raw.split('\x01'):
        if not chunk.strip():
            continue
        sha, parents, ct, rest = chunk.split('\x02', 3)
        body, _, names = rest.partition('\x03')
        files = {}
        for line in names.strip().splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                files[parts[1]] = (parts[0][0], parts[2] if len(parts) > 2 else None)
        routine = re.search(r'^Routine: (\S+)', body, re.M)
        op = re.search(r'^Op: (\w+) (\S+)', body, re.M)
        reason = re.search(r'^Reason: (.+)$', body, re.M)
        rid = routine.group(1) if routine else None
        path = op.group(2) if op else next(iter(files), '')
        kind = classify(op and op.group(1), path, files)
        to = (files.get(path, ('', None))[1] or next((p for p, (s, _) in files.items() if s == 'A'), path)) if kind in ('archive move', 'restore', 'filing move') else path
        parent = parents.split()[0] if parents.strip() else sha
        if kind == 'page deletion':
            link, title = f'{web}/{parent}/{path}', page_title(cfg, parent, path)
        else:
            link, title = f'{web}/{cfg.get("branch", "main")}/{to}', page_title(cfg, sha, to)
        out.append({'sha': sha[:7], 'at': int(ct), 'routine': rid, 'workflow': workflow_of(cfg, rid) if rid else 'other',
                    'kind': kind, 'path': path, 'to': to if to != path else None, 'title': title, 'link': link,
                    'subject': body.splitlines()[0] if body.strip() else '',
                    'reason': clip(reason.group(1), 400) if reason else '',
                    'owner_choice': bool(reason and reason.group(1).startswith('Owner chose')),
                    'files': len(files)})
    out.reverse()
    return out


def runs_in(cfg, start, end):
    """Every routine run that started in the window, with its record and journal."""
    out = []
    for d in sorted((lib.state_dir(cfg) / 'runs').glob('*')):
        meta = lib.read_json(d / 'run.json')
        if meta and start <= meta.get('started_at', 0) < end:
            out.append((meta, lib.read_journal(cfg, meta['run_id'])))
    return out


def outside_changes(cfg, runs):
    """Changes runs journaled in other repositories (the agent workspace, the shared core): no brain commit carries them."""
    prefix = f'https://github.com/{cfg["github_repo"]}/'
    workspace = Path(cfg['openclaw']['workspace_skills']).parent.name + '/'  # brain-core labels workspace files with it
    out = []
    for meta, entries in runs:
        for e in entries:
            url = e.get('url') or ''
            if e['kind'] == 'change' and url and not url.startswith(prefix) and '/commit/' in url:
                repo, sha = url.split('/commit/', 1)
                label = re.search(r'`([^`]+)`', e.get('text', ''))
                label = label.group(1) if label else ''
                path = label[len(workspace):] if label.startswith(workspace) else label
                out.append({'sha': sha[:7], 'at': parse_iso(e['at']), 'routine': meta['routine'], 'workflow': meta['workflow'],
                            'kind': 'other', 'path': path, 'to': None,
                            'title': label or repo.rsplit('/', 1)[-1], 'subject': e.get('text', ''),
                            'link': f'{repo}/blob/{sha}/{path}' if path else repo, 'reason': '', 'owner_choice': False, 'files': 1})
    return out


def attention(cfg, start):
    raw = lib.gh(cfg, 'issue', 'list', '--repo', cfg['github_repo'], '--state', 'open', '--label', 'needs-attention',
                 '--json', 'number,title,url,body,createdAt,labels', '--limit', '200')
    items = []
    for i in sorted(json.loads(raw or '[]'), key=lambda x: x['createdAt']):
        body = i.get('body') or ''
        options = {int(n): label.strip() for n, label, _ in OPTION.findall(body)}
        rec = RECOMMENDED.search(body)
        number = int(rec.group(1)) if rec else None
        finding = FINDING.search(body)
        items.append({
            'item': len(items) + 1, 'number': i['number'], 'title': i['title'], 'url': i['url'],
            'workflow': next((lab['name'].split(':', 1)[1] for lab in i.get('labels', []) if lab['name'].startswith('workflow:')), None),
            'new': parse_iso(i['createdAt']) >= start,
            'finding': clip(finding.group(1), 600) if finding else clip(body, 600),
            'options': options, 'recommended': number,
            'recommended_label': options.get(number) if number else None,
            'recommended_reason': clip(rec.group(2).rstrip('.'), 220) if rec and rec.group(2) else '',
        })
    return items


def done(runs):
    """Answers the workflows applied in the window."""
    out = []
    for meta, entries in runs:
        for e in entries:
            if e['kind'] == 'resolved':
                out.append({'number': int(e['url'].rstrip('/').rsplit('/', 1)[-1]), 'url': e['url'], 'title': e['title'],
                            'option': e['option'], 'label': e['label'], 'workflow': meta['workflow']})
    return out


def health(cfg, runs, start, own):
    """Anything off in the window: runs that failed or ran partly, deferrals, alerts that could not be sent."""
    routines = manifest_routines(cfg)
    facts = []
    for meta, entries in runs:
        if meta['routine'] == own or meta.get('status') in (None, 'ok') or meta.get('forced'):
            continue  # a forced or test run speaks only through the content it changed
        r = routines.get(meta['routine'], {})
        problems = [clip(e['text'], 240) for e in entries if e['kind'] == 'problem'][:2]
        facts.append({'routine': meta['routine'], 'title': r.get('title', meta['routine']), 'status': meta['status'],
                      'at': meta['started_at'], 'summary': clip(meta.get('summary', ''), 240), 'problems': problems,
                      'forced': bool(meta.get('forced'))})
    for f in lib.load_state(cfg).get('send_failures', []):
        if parse_iso(f['at']) >= start:
            facts.append({'routine': f.get('routine'), 'title': 'an alert', 'status': 'not sent', 'at': parse_iso(f['at']),
                          'summary': f'an alert to {f["target"]} could not be sent: {clip(f["error"], 160)}', 'problems': [], 'forced': False})
    return facts


def page_counts(cfg, ref):
    counts = {}
    if not ref:
        return counts
    for path in git(cfg, 'ls-tree', '-r', '--name-only', ref).splitlines():
        if path.endswith('.md') and '/' in path:
            area = path.split('/', 1)[0]
            counts[area] = counts.get(area, 0) + 1
    return counts


def version_key(version):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r'[.-]', version))


def releases(changelog):
    """The releases in an upstream changelog range, oldest first, each flagged as a security fix or a new default-on feature."""
    out = []
    for version, date, body in RELEASE.findall(changelog or ''):
        lead = body.strip().split('\n\n', 1)[0]
        bold = re.match(r'^(?:#+\s*)?\*\*(.+?)\*\*', lead, re.S)
        headline = ' '.join(re.sub(r'[`*#]', '', bold.group(1) if bold else lead).split())
        out.append({'version': version, 'date': date or None, 'headline': headline,
                    'security': bool(SECURITY_HEADLINE.search(headline) or SECURITY_LEAD.search(lead)),
                    'default_on': bool(DEFAULT_ON.search(lead))})
    return sorted(out, key=lambda r: version_key(r['version']))


def engine(cfg):
    """This brain's GBrain against upstream's latest stable release, from the engine's own update check."""
    rc = json.loads((SKILLS / 'gbrain-host-reconciler' / 'config.json').read_text())
    env = dict(os.environ, PATH=rc['path'], GBRAIN_SKIP_STARTUP_HOOKS='1')
    out = lib.run([rc['gbrain_bin'], 'check-update', '--json'], env=env, timeout=120)
    check = json.loads(out[out.index('{'):])
    if check.get('error'):
        raise Failed(f'the update check failed: {check["error"]}')
    found = releases(check.get('changelog_diff')) if check.get('update_available') else []
    behind = [r for r in found if version_key(r['version']) > version_key(check['current_version'])]
    facts = {'running': check['current_version'], 'latest': check.get('latest_version') or check['current_version'],
             'behind': len(behind), 'since': behind[0]['date'] if behind else None, 'far_at': WATCH['engine_far_releases'],
             'security': [{k: r[k] for k in ('version', 'headline')} for r in behind if r['security']],
             'default_on': [{k: r[k] for k in ('version', 'headline')} for r in behind if r['default_on']]}
    facts['shown'] = bool(facts['security'] or facts['behind'] >= facts['far_at'])
    facts['why'] = (f'{facts["behind"]} releases behind (shown from {facts["far_at"]})'
                    + (f', {len(facts["security"])} security fixes in the range' if facts['security'] else ', no security fix in the range'))
    return facts


def engine_line(f):
    def gist(headline):
        text = clip(re.sub(r'^security:\s*', '', headline, flags=re.I), 80)
        return text[:-1] if text.endswith('.') and not text.endswith('...') else text

    def named(items):
        text = '; '.join(f'{r["version"]} ({gist(r["headline"])})' for r in items[:2])
        return text + (f'; and {len(items) - 2} more' if len(items) > 2 else '')

    since = dt.date.fromisoformat(f['since']).strftime('%-d %b') if f['since'] else None
    line = (f'GBrain is {f["behind"]} releases behind upstream ({f["running"]} here, latest stable {f["latest"]}'
            + (f', behind since {since}' if since else '') + ').')
    if f['security']:
        line += f' Security fixes in that range: {named(f["security"])}.'
    if f['default_on']:
        line += f' New default-on features to decide: {named(f["default_on"])}.'
    return line + ' Upgrade through the GBrain lane when you have time.'


def watch(cfg, start):
    """The weekly edition's watch lines, each only when it moves; a line that cannot be read becomes a problem.

    Returns the lines, the problems and the facts behind the engine line, which the packet keeps so a quiet line shows why."""
    lines, problems, facts = [], [], {}
    # the engine against upstream
    try:
        facts['engine'] = engine(cfg)
        if facts['engine']['shown']:
            lines.append(engine_line(facts['engine']))
    except (Failed, OSError, ValueError, KeyError) as error:
        problems.append(f'GBrain version: {error}')
    # search quality
    try:
        rows = []
        path = lib.state_dir(cfg) / 'eval' / 'history.jsonl'
        for line in (path.read_text().splitlines() if path.exists() else []):
            rec = json.loads(line)
            results = [r for r in rec.get('results', {}).values() if 'error' not in r]
            if results:
                critical = [r for r in results if r.get('critical')]
                rows.append({'at': parse_iso(rec['at']), 'gate': rec.get('gate'), 'complete': rec.get('complete'),
                             'recall': sum(r['recall'] for r in results) / len(results), 'top1': sum(r['hit1'] for r in results) / len(results),
                             'critical_fail': sum(1 for r in critical if r.get('top1', r.get('hit1')) != 1)})
        week = [r for r in rows if r['at'] >= start]
        if not week:
            lines.append('The weekly search check did not run this week.')
        else:
            now, before = week[-1], ([r for r in rows if r['at'] < week[-1]['at']] or [None])[-1]
            if now['gate'] != 'pass' or now['critical_fail'] or not now['complete']:
                lines.append('Search quality failed its weekly check' + (', and a critical lookup no longer comes first' if now['critical_fail'] else '') + '.')
            elif before and (abs(now['top1'] - before['top1']) >= WATCH['eval_move'] or abs(now['recall'] - before['recall']) >= WATCH['eval_move']):
                lines.append(f'Search quality moved: the right page came first in {now["top1"]:.0%} of lookups (was {before["top1"]:.0%}), '
                             f'and in the top ten in {now["recall"]:.0%} (was {before["recall"]:.0%}).')
    except (OSError, ValueError, KeyError) as error:
        problems.append(f'eval history: {error}')
    # subscription use
    snap = lib.usage(cfg)
    if snap is None:
        problems.append('the subscription windows could not be read')
    else:
        near = cfg['window_guard']['defer_at'] - WATCH['window_near_points']
        for provider, s in snap.items():
            for label, used in (s.get('windows') or {}).items():
                if used is not None and used >= near:
                    lines.append(f'Subscription use is near the maintenance threshold: the {provider} {label.lower()} window is {used:g}% used, '
                                 f'and the deferrable routines wait from {cfg["window_guard"]["defer_at"]}%.')
    # pages per area
    try:
        before_ref = git(cfg, 'rev-list', '-1', f'--before={lib.iso(start)}', rev(cfg)) or None
        now_c, then_c = page_counts(cfg, rev(cfg)), page_counts(cfg, before_ref)
        moved = []
        for area in CONF['areas'] + CONF['ledger']:
            change = now_c.get(area, 0) - then_c.get(area, 0)
            if abs(change) >= WATCH['area_change_pages'] and abs(change) >= WATCH['area_change_share'] * max(then_c.get(area, 0), 1):
                moved.append(f'{area} {now_c.get(area, 0)} ({change:+})')
        if moved:
            lines.append('Pages per area moved this week: ' + ', '.join(moved) + '.')
    except (Failed, OSError) as error:
        problems.append(f'page counts: {error}')
    return lines, problems, facts


def window(cfg, state, end, edition):
    if edition == 'weekly':
        return end - 7 * lib.DAY
    last = state.get('last_ok_started_at')
    if not last:
        return end - CONF['first_window_hours'] * 3600
    return max(last, end - CONF['max_window_days'] * lib.DAY)


def build(cfg, run_id, own, end, edition=None):
    """The packet of the window ending at `end`: every fact the digest reports, gathered with zero LLM calls."""
    tz = lib.manifest(cfg)['timezone']
    state = load_state(cfg)
    monday = dt.datetime.fromtimestamp(end, ZoneInfo(tz)).isoweekday() == CONF['weekly_day']
    edition = edition or state.get('next_edition') or ('weekly' if monday else 'daily')
    start = window(cfg, state, end, edition)
    problems = []
    packet = {'run_id': run_id, 'brain': cfg['brain'], 'edition': edition, 'timezone': tz,
              'window': {'start': start, 'end': end, 'start_iso': lib.iso(start), 'end_iso': lib.iso(end)},
              'narrative_file': str(lib.run_dir(cfg, run_id) / 'narrative.json') if run_id else None}

    def part(name, fn, *a):
        try:
            packet[name] = fn(*a)
        except (Failed, OSError, ValueError, KeyError) as error:
            problems.append(f'{name}: {error}')
            packet[name] = None

    runs = runs_in(cfg, start, end)
    part('changes', changes, cfg, start, end)
    packet['changes'] = (packet['changes'] or []) + outside_changes(cfg, runs)
    part('needs_you', attention, cfg, start)
    packet['done'] = done(runs)
    packet['health'] = health(cfg, runs, start, own)
    packet['watch'], packet['watch_facts'] = [], {}
    if edition == 'weekly':
        packet['watch'], watch_problems, packet['watch_facts'] = watch(cfg, start)
        problems += watch_problems
    packet['problems'] = problems
    needs = packet['needs_you'] or []
    packet['news'] = bool(edition == 'weekly' or packet['changes'] or packet['done'] or packet['health']
                          or any(i['new'] for i in needs) or packet['needs_you'] is None)
    return packet


def cmd_gather(cfg, args):
    meta = lib.current_run(cfg, args.run)
    packet = build(cfg, meta['run_id'], meta['routine'], meta['started_at'])
    for p in packet['problems']:
        lib.journal(cfg, meta['run_id'], 'problem', text=f'Digest data: {p}')
    d = lib.run_dir(cfg, meta['run_id'])
    lib.atomic(d / 'packet.json', packet)
    needs = packet['needs_you'] or []
    print(json.dumps({
        'packet': str(d / 'packet.json'), 'narrative_file': packet['narrative_file'], 'edition': packet['edition'], 'news': packet['news'],
        'changes': len(packet['changes']), 'needs_you': [i['number'] for i in needs], 'done': [x['number'] for x in packet['done']],
        'health': len(packet['health']), 'watch': len(packet['watch']), 'problems': packet['problems'],
        'next': f'{sys.executable} {Path(__file__)} post --run {meta["run_id"]}' + ('' if packet['news'] else ' --quiet'),
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_preview(cfg, args):
    """The digest a run starting now would post, in the sentences built from the facts; it posts nothing and keeps no digest state."""
    packet = build(cfg, None, CONF['routine'], lib.now(), args.edition)
    print('\n\n'.join(pack(render(packet, fallback(packet)))))
    print(json.dumps({'edition': packet['edition'], 'news': packet['news'], 'window': packet['window'],
                      'watch_facts': packet['watch_facts'], 'problems': packet['problems']}, ensure_ascii=False, indent=2), file=sys.stderr)
    return 0


# render

def check(p, n):
    """Problems with the agent's narrative; an empty list means it renders."""
    if not isinstance(n, dict):
        return ['the narrative is not a JSON object']
    errors = []

    def plain(where, text, limit):
        if not isinstance(text, str) or not text.strip():
            errors.append(f'{where} needs a sentence')
            return
        if len(text) > limit:
            errors.append(f'{where} is longer than {limit} characters')
        for pattern, what in RAW:
            if pattern.search(text):
                errors.append(f'{where} carries {what}; name pages by title and leave links to the render')

    needs = {str(i['number']): i for i in p.get('needs_you') or []}
    gists = n.get('needs_you') or {}
    for num in needs:
        plain(f'needs_you {num}', gists.get(num), NARR['gist_chars'])
    errors += [f'needs_you {num} is not an open needs-attention issue' for num in gists if num not in needs]
    shas = {c['sha'] for c in p.get('changes') or []}
    items = n.get('changed') or []
    cap = NARR['items_weekly' if p['edition'] == 'weekly' else 'items_daily']
    if not isinstance(items, list) or len(items) > cap:
        errors.append(f'changed needs a list of at most {cap} items')
        items = []
    covered = set()
    for k, item in enumerate(items, 1):
        if not isinstance(item, dict):
            errors.append(f'changed item {k} is not an object')
            continue
        plain(f'changed item {k}', item.get('text'), NARR['item_chars'])
        cited = [s[:7] for s in item.get('commits') or []]
        if not cited:
            errors.append(f'changed item {k} cites no commits')
        unknown = [s for s in cited if s not in shas]
        if unknown:
            errors.append(f'changed item {k} cites commits outside the window: ' + ', '.join(unknown))
        if (item.get('link') or '')[:7] not in cited:
            errors.append(f'changed item {k} needs a link that is one of its commits')
        covered.update(cited)
    missing = sorted(shas - covered)
    if missing:
        errors.append('every change in the window belongs to one item; missing: ' + ', '.join(missing[:30]) + (' ...' if len(missing) > 30 else ''))
    answers = {str(x['number']) for x in p.get('done') or []}
    for num in answers:
        plain(f'done {num}', (n.get('done') or {}).get(num), NARR['gist_chars'])
    if p.get('health'):
        plain('health', n.get('health'), NARR['health_chars'])
    elif n.get('health'):
        errors.append('health is empty when nothing is off')
    if not errors and p['edition'] == 'weekly':
        size = sum(len(m) for m in pack(render(p, n)))
        if size > NARR['screen_chars']:
            errors.append(f'the weekly edition renders to {size} characters; fit it on one screen ({NARR["screen_chars"]}) with fewer, shorter items')
    return errors


def fallback(p):
    """Sentences from the facts, for when the agent's narrative is missing or invalid."""
    groups = {}
    for c in p.get('changes') or []:
        groups.setdefault((c['workflow'], c['kind']), []).append(c)
    changed = []
    for (wf, kind), group in groups.items():
        titles = ', '.join(dict.fromkeys(c['title'] for c in group))
        changed.append({'text': clip(f'{KIND_WORDS[kind]} by the {wf} workflow: {titles}.', NARR['item_chars']),
                        'commits': [c['sha'] for c in group], 'link': group[0]['sha']})
    cap = NARR['items_weekly' if p['edition'] == 'weekly' else 'items_daily']
    if len(changed) > cap:
        rest = [c for item in changed[cap - 1:] for c in item['commits']]
        changed = changed[:cap - 1] + [{'text': 'Other maintenance changes.', 'commits': rest, 'link': rest[0]}]
    verbs = {'partial': 'ran only partly', 'failed': 'failed', 'deferred': 'was deferred'}
    health = '; '.join(f'{f["title"]} {verbs.get(f["status"], f["status"])}' + (f': {f["problems"][0]}' if f['problems'] else f': {f["summary"]}' if f['summary'] else '')
                       for f in p.get('health') or [])
    return {'needs_you': {str(i['number']): clip(i['finding'], NARR['gist_chars']) for i in p.get('needs_you') or []},
            'changed': changed, 'done': {str(x['number']): f'You chose {x["label"].lower()}.' for x in p.get('done') or []},
            'health': clip(health[0].upper() + health[1:], NARR['health_chars']) if health else ''}


def render(p, n):
    tz, w = p['timezone'], p['window']
    blocks = []
    if p['edition'] == 'weekly':
        blocks.append(f'**{p["brain"]} weekly** · {local(w["start"], tz)} to {local(w["end"], tz)}')
    else:
        blocks.append(f'**{p["brain"]} digest** · {local(w["end"], tz)}')
    if p.get('problems'):
        blocks.append('-# Some facts could not be read: ' + '; '.join(p['problems']))
    needs = p.get('needs_you')
    if needs is None:
        blocks.append('**Needs you**\nThe needs-attention issues could not be read.')
    elif needs:
        lines = ['**Needs you**']
        for i in needs:
            rec = f' Recommended: **{i["recommended_label"]}**.' if i['recommended_label'] else ''
            lines.append(f'{i["item"]}. {(n.get("needs_you") or {}).get(str(i["number"]), "")}{rec} [#{i["number"]}](<{i["url"]}>)')
        lines.append('-# Reply here with the item and your answer: `1: yes` takes the recommended option, `2: option 3` another one.')
        blocks.append('\n'.join(lines))
    by_sha = {c['sha']: c for c in p.get('changes') or []}
    if n.get('changed'):
        lines = ['**Changed**']
        for item in n['changed']:
            c = by_sha.get((item.get('link') or '')[:7])
            lines.append(f'- {item["text"]}' + (f' [{clip(c["title"], 60)}](<{c["link"]}>)' if c else ''))
        blocks.append('\n'.join(lines))
    if p.get('done'):
        lines = ['**Done**']
        lines += [f'- {(n.get("done") or {}).get(str(x["number"]), "")} [#{x["number"]}](<{x["url"]}>)' for x in p['done']]
        blocks.append('\n'.join(lines))
    if n.get('health'):
        blocks.append(f'**Health:** {n["health"]}')
    if p.get('watch'):
        blocks.append('\n'.join(['**Watch**', *[f'- {line}' for line in p['watch']]]))
    return blocks


def pack(blocks):
    """Discord messages under the limit, never splitting a block unless it alone is too long."""
    messages, current = [], ''
    for block in blocks:
        pieces = [block] if len(block) <= LIMIT else split(block)
        for piece in pieces:
            if current and len(current) + len(piece) + 2 > LIMIT:
                messages.append(current)
                current = ''
            current = f'{current}\n\n{piece}' if current else piece
    if current:
        messages.append(current)
    return messages


def split(block):
    out, current = [], ''
    for line in block.splitlines():
        line = line[:LIMIT - 10]
        if current and len(current) + len(line) + 1 > LIMIT:
            out.append(current)
            current = ''
        current = f'{current}\n{line}' if current else line
    if current:
        out.append(current)
    return out


def remember(cfg, meta, p, posted):
    """Keep the run's window and, for a posted digest, its numbered items for the owner's answers."""
    state = load_state(cfg)
    state['last_ok_started_at'] = meta['started_at']
    state.pop('next_edition', None)
    if posted:
        items = {str(i['item']): {'number': i['number'], 'url': i['url'], 'title': i['title'], 'workflow': i['workflow'],
                                  'options': {str(k): v for k, v in i['options'].items()}, 'recommended': i['recommended']}
                 for i in p.get('needs_you') or []}
        state['last_digest'] = {'run_id': meta['run_id'], 'posted_at': lib.iso(), 'edition': p['edition'], 'items': items}
    save_state(cfg, state)


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
    if args.quiet:
        if p['news']:
            raise Failed('the packet has news; write the narrative and post it')
        if not args.dry_run:
            remember(cfg, meta, p, posted=False)
            runner.end(cfg, meta, 'ok', 'nothing to report, so no digest posted', {})
        print(json.dumps({'ended': meta['run_id'], 'posted': False}))
        return 0
    if args.fallback:
        n = fallback(p)
    else:
        n = lib.read_json(Path(p['narrative_file']))
        errors = check(p, n) if n is not None else [f'no narrative at {p["narrative_file"]}']
        if errors:
            print(json.dumps({'errors': errors}, ensure_ascii=False, indent=2))
            return 1
    messages = pack(render(p, n))
    text = '\n\n'.join(messages)
    if args.dry_run:
        print(text)
        print(json.dumps({'messages': len(messages), 'characters': len(text)}), file=sys.stderr)
        return 0
    (d / 'digest.md').write_text(text + '\n')
    error = None
    for k, msg in enumerate(messages):
        error = lib.post(cfg, cfg['channels']['brain-review'], msg, silent=k > 0)
        if error:
            break
    if error:
        lib.journal(cfg, meta['run_id'], 'problem', text=f'Posting the digest failed: {error}')
    if args.fallback:
        lib.journal(cfg, meta['run_id'], 'note', text='The digest sentences were rendered from the facts.')
    remember(cfg, meta, p, posted=not error)
    if not error:
        state = lib.load_state(cfg)
        state['send_failures'] = [f for f in state.get('send_failures', []) if parse_iso(f['at']) >= p['window']['end']]
        lib.save_state(cfg, state)
    summary = (f'posted the {p["edition"]} digest in {len(messages)} message(s): {len(p.get("changes") or [])} changes, '
               f'{len(p.get("needs_you") or [])} open needs-attention items, {len(p.get("done") or [])} answers applied')
    runner.end(cfg, meta, 'partial' if error else 'ok', summary, {})
    print(json.dumps({'ended': meta['run_id'], 'posted': not error, 'messages': len(messages), 'error': error}, indent=2))
    return 0


# the owner's answers

def choice(reply, options, recommended):
    """The option an answer names: yes and its kin take the recommended one, a number or "option N" another."""
    body = re.sub(r'^\s*\d+\s*[:.)-]\s*', '', reply or '', count=1)  # "1: yes" -> "yes"
    m = re.search(r'\boption\s*#?(\d+)\b', body, re.I) or re.match(r'^\W*#?(\d+)\b', body)
    if m and str(int(m.group(1))) in options:
        return int(m.group(1))
    if YES.match(body) and recommended:
        return recommended
    return None


def cmd_answer(cfg, args):
    """Record the owner's answer on its needs-attention issue; the owning workflow's next run applies it."""
    state = load_state(cfg)
    if args.issue:
        issue = json.loads(lib.gh(cfg, 'issue', 'view', str(args.issue), '--repo', cfg['github_repo'], '--json', 'number,title,url,body,labels,state'))
        body = issue.get('body') or ''
        rec = RECOMMENDED.search(body)
        target = {'number': issue['number'], 'url': issue['url'], 'title': issue['title'], 'state': issue['state'],
                  'workflow': next((lab['name'].split(':', 1)[1] for lab in issue['labels'] if lab['name'].startswith('workflow:')), None),
                  'options': {n: label.strip() for n, label, _ in OPTION.findall(body)}, 'recommended': int(rec.group(1)) if rec else None}
    else:
        items = (state.get('last_digest') or {}).get('items') or {}
        if str(args.item) not in items:
            raise Failed(f'the last digest has no item {args.item}; it has ' + (', '.join(items) or 'none') + '. Pass --issue <number> instead.')
        target = dict(items[str(args.item)])
        target['state'] = json.loads(lib.gh(cfg, 'issue', 'view', str(target['number']), '--repo', cfg['github_repo'], '--json', 'state'))['state']
    if target['state'] != 'OPEN':
        raise Failed(f'issue #{target["number"]} is already closed')
    option = choice(args.reply, target['options'], target['recommended'])
    if option is None:
        print(json.dumps({'error': 'the answer names no option', 'issue': target['number'],
                          'options': target['options'], 'recommended': target['recommended']}, ensure_ascii=False, indent=2))
        return 1
    label = target['options'][str(option)]
    where = args.where or '#brain-review'
    text = (f'Option {option}: **{label}**\n\n{args.who} answered in {where}: "{clip(args.reply, 300)}". '
            f'The next {target["workflow"] or "workflow"} run applies it and closes this issue.\n\n{lib.ANSWER}')
    lib.gh(cfg, 'issue', 'comment', str(target['number']), '--repo', cfg['github_repo'], '--body-file', '-', input=text)
    print(json.dumps({'recorded': target['number'], 'url': target['url'], 'option': option, 'label': label,
                      'applies': f'the next {target["workflow"]} run'}, ensure_ascii=False, indent=2))
    return 0


def cmd_items(cfg, args):
    """The last digest's numbered items, for answers and follow-up questions."""
    last = load_state(cfg).get('last_digest')
    if not last:
        print(json.dumps({'error': 'no digest posted yet'}))
        return 1
    packet = lib.read_json(lib.run_dir(cfg, last['run_id']) / 'packet.json') or {}
    findings = {i['number']: i['finding'] for i in packet.get('needs_you') or []}
    print(json.dumps({**last, 'items': {k: {**v, 'finding': findings.get(v['number'])} for k, v in last['items'].items()},
                      'digest': str(lib.run_dir(cfg, last['run_id']) / 'digest.md')}, ensure_ascii=False, indent=2))
    return 0


def cmd_edition(cfg, args):
    state = load_state(cfg)
    state['next_edition'] = args.edition
    save_state(cfg, state)
    print(json.dumps({'next_edition': args.edition}))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('gather').add_argument('--run', required=True)
    c = sub.add_parser('post')
    c.add_argument('--run', required=True)
    c.add_argument('--dry-run', action='store_true', help='check and print the rendered digest; post nothing, end nothing')
    c.add_argument('--fallback', action='store_true', help='render the sentences from the facts instead of the narrative')
    c.add_argument('--quiet', action='store_true', help='end a run with nothing to report without posting')
    c = sub.add_parser('answer', help="record the owner's answer on its needs-attention issue")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument('--item', type=int, help='the item number in the last digest')
    g.add_argument('--issue', type=int, help='the needs-attention issue number')
    c.add_argument('--reply', required=True, help="the owner's words, for example \"1: yes\" or \"option 2\"")
    c.add_argument('--who', default='The owner', help='who answered, by name')
    c.add_argument('--where', default='', help='where the answer was given, for example "#brain-review" or "a chat with Pulsy"')
    sub.add_parser('items', help="the last digest's numbered items")
    c = sub.add_parser('preview', help='print the digest a run starting now would post; posts and records nothing')
    c.add_argument('--edition', choices=('weekly', 'daily'), help='the edition to render; by default the one the next run takes')
    c = sub.add_parser('edition', help='set the edition of the next run')
    c.add_argument('edition', choices=('weekly', 'daily'))
    args = p.parse_args()
    cfg = lib.config()
    return {'gather': cmd_gather, 'post': cmd_post, 'answer': cmd_answer, 'items': cmd_items, 'edition': cmd_edition,
            'preview': cmd_preview}[args.command](cfg, args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
