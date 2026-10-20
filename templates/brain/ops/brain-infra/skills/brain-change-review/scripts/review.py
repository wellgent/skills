#!/usr/bin/env python3
"""The daily change review: the queue of changed pages, batch packets, the review guards and the run summary.

The review-daily agent turn runs, in order:

  routine.py begin review-daily                  the run id (brain-routines)
  review.py prep --run <run_id>                  queue the changed pages, oldest change first
  review.py next --run <run_id>                  the next batch packet, or {"done": true} at the page cap
  review.py apply --run <run_id> <verdicts>      the batch's verdicts through the review guards and apply.py
  ... next and apply until done ...
  review.py finish --run <run_id>                judge misses, then routine.py end

Owner replies to needs-attention issues run `apply-option <proposal>` and `hold --on|--off`.
Everything zero-LLM: Git in the maintenance clone, `gbrain lint` and `gbrain query`.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True  # routines write nothing into the published copy
SCRIPTS = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS.parent
FRAMEWORK = SKILL_DIR.parent / 'brain-routines' / 'scripts'
sys.path[:0] = [str(FRAMEWORK), str(SCRIPTS)]
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402
import apply as applylib  # noqa: E402
import judge_misses  # noqa: E402

CONF = json.loads((SKILL_DIR / 'config.json').read_text())
RID = CONF['routine']
CMD = f'{sys.executable} {SCRIPTS / "review.py"}'
FRONTMATTER_KEY = re.compile(r'^\s*(updated|created|status|tags|aliases|related|title|type|last_verified):')
WORD = re.compile(r"[\w][\w.,:/'-]*\w|\w")
DATE = re.compile(r'\*\*(\d{4}-\d{2}-\d{2})\*\*')
STOP = {'about', 'after', 'again', 'their', 'there', 'these', 'those', 'which', 'while', 'where', 'would', 'should',
        'could', 'other', 'being', 'under', 'between', 'through', 'source', 'jaros'}


# state

def review_dir(cfg):
    path = lib.state_dir(cfg) / 'review'
    path.mkdir(exist_ok=True, mode=0o700)
    return path


def load_state(cfg):
    return lib.read_json(review_dir(cfg) / 'state.json', {'cursor': None, 'queue': {}, 'held': False})


def save_state(cfg, state):
    lib.atomic(review_dir(cfg) / 'state.json', state)


def run_record(cfg, run_id):
    return lib.read_json(lib.run_dir(cfg, run_id) / 'review.json', {'batches': [], 'ops': {}, 'review_rejected': [],
                                                                    'dropped': [], 'deferred': 0, 'new': 0, 'lint': 0})


def save_run(cfg, run_id, rec):
    lib.atomic(lib.run_dir(cfg, run_id) / 'review.json', rec)


def git(cfg, *args, **kw):
    return lib.clone_git(cfg, *args, **kw)


def maintenance_author(cfg):
    return git(cfg, 'config', 'user.name')


# pages

def area_class(path):
    """editable, records, context, or None for ledger areas and repo-control files."""
    parts = path.split('/')
    if len(parts) < 2 or parts[-1] == 'README.md' or not path.endswith('.md'):
        return None
    for cls in ('editable', 'records', 'context'):
        if parts[0] in CONF['areas'][cls]:
            return cls
    return None


def read(repo, path):
    try:
        return (repo / path).read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return None


def split_frontmatter(text):
    if text.startswith('---\n'):
        close = text.find('\n---', 4)
        if close > 0:
            end = text.find('\n', close + 4)
            return text[4:close], text[end + 1 if end > 0 else len(text):]
    return '', text


def title_and_lede(text):
    fm, body = split_frontmatter(text)
    m = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', fm, re.M)
    title = m.group(1) if m else ''
    lede = ''
    for para in re.split(r'\n\s*\n', body):
        para = para.strip()
        if not para:
            continue
        if para.startswith('# ') and not title:
            title = para[2:].splitlines()[0].strip()
            continue
        if para.startswith(('#', '<!--', '|', '```')):
            continue
        lede = ' '.join(para.split())
        break
    return title, lede[:400]


def related(text):
    fm, _ = split_frontmatter(text)
    m = re.search(r'^related:\s*\n((?:\s+-\s+.*\n?)+)', fm, re.M)
    if not m:
        return []
    return [line.split('-', 1)[1].strip().strip('"\'') + '.md' for line in m.group(1).splitlines() if '-' in line]


class LinkIndex:
    """Outbound and inbound links among the pages the review reads."""

    def __init__(self, repo, pages):
        self.out, self.inbound = {}, {}
        for path in pages:
            text = read(repo, path) or ''
            targets = set()
            for m in applylib.LINK.finditer(text):
                resolved, _ = applylib.link_target(path, m.group(2))
                if resolved and resolved != path:
                    targets.add(resolved)
            targets.update(r for r in related(text) if r != path)
            self.out[path] = targets
            for t in targets:
                self.inbound.setdefault(t, set()).add(path)


# the queue

def changed_pages(cfg, base, head, author):
    """Pages changed in base..head by any writer but the maintenance writer, oldest change first: {path: [authors]}."""
    raw = git(cfg, 'log', '--reverse', '--no-merges', '-M', '--name-status', '--format=%x01%an', f'{base}..{head}', timeout=120)
    pages = {}
    for chunk in raw.split('\x01'):
        if not chunk.strip():
            continue
        who, _, files = chunk.partition('\n')
        if who == author:
            continue
        for line in files.splitlines():
            parts = line.split('\t')
            if len(parts) < 2 or parts[0].startswith('D'):
                continue
            pages.setdefault(parts[-1], set()).add(who)
    return {p: sorted(a) for p, a in pages.items()}


def cooldown(cfg, author):
    raw = git(cfg, 'log', f'--since={CONF["cooldown_days"]} days ago', f'--author=^{re.escape(author)} <', '--name-only', '--format=', timeout=60)
    return {p for p in raw.splitlines() if p}


def cmd_prep(cfg, args):
    meta = lib.current_run(cfg, args.run)
    lib.reset_clone(cfg)
    repo = Path(cfg['maintenance_repo'])
    head = git(cfg, 'rev-parse', 'HEAD')
    state = load_state(cfg)
    base = state.get('cursor')
    if not base or git(cfg, 'merge-base', '--is-ancestor', base, head, check=False)[0] != 0:
        before = f'--before={CONF["first_run_hours"]} hours ago'
        base = git(cfg, 'rev-list', '-1', before, head) or git(cfg, 'rev-list', '--max-parents=0', head).splitlines()[0]
    author = maintenance_author(cfg)
    changed = {p: a for p, a in changed_pages(cfg, base, head, author).items()
               if area_class(p) in ('editable', 'records') and (repo / p).is_file()}
    queue = state.setdefault('queue', {})
    for path, authors in changed.items():
        entry = queue.setdefault(path, {'base': base, 'queued_at': lib.iso(), 'reason': 'changed', 'attempts': 0, 'context': []})
        entry['reason'] = 'changed'
        entry['authors'] = sorted(set(entry.get('authors', [])) | set(authors))
    state['cursor'] = head
    save_state(cfg, state)
    rec = run_record(cfg, meta['run_id'])
    rec.update(new=len(changed), carried=len(queue) - len(changed), base=base, head=head)
    save_run(cfg, meta['run_id'], rec)
    print(json.dumps({'queued': len(queue), 'changed_since_last_run': len(changed), 'carried_over': len(queue) - len(changed),
                      'batches_estimate': math.ceil(min(len(queue), CONF['max_pages']) / CONF['batch_size']), 'held': bool(state.get('held')),
                      'next': f'{CMD} next --run {meta["run_id"]}'}, indent=2))
    return 0


# the batch packet

def lint(cfg, paths, run_dir):
    """gbrain lint findings on the given pages, minus the rules this review leaves to other workflows."""
    try:
        code, out, _ = lib.run(['gbrain', 'lint', cfg['maintenance_repo']], cwd=run_dir, timeout=180, check=False)
    except (Failed, OSError) as error:
        return None, str(error)
    found, current = {}, None
    for line in out.splitlines():
        if line and not line.startswith(' ') and line.endswith(':'):
            current = line[:-1]
            continue
        m = re.match(r'^\s+L(\d+) ([\w-]+): (.*)$', line)
        if m and current in paths and m.group(2) not in CONF['lint_ignore']:
            found.setdefault(current, []).append({'line': int(m.group(1)), 'rule': m.group(2), 'message': m.group(3)[:200]})
    return found, None


def stale_compiled_truth(cfg, repo, path):
    """Timeline evidence newer than the compiled truth above the `<!-- timeline -->` marker, or None."""
    text = read(repo, path) or ''
    lines = text.splitlines()
    marker = next((i for i, line in enumerate(lines) if line.strip() == '<!-- timeline -->'), None)
    if marker is None:
        return None
    dates = DATE.findall('\n'.join(lines[marker:]))
    if not dates:
        return None
    newest = max(dates)
    fm_end = 0
    if text.startswith('---\n'):
        fm_end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == '---'), 0) + 1
    if marker <= fm_end:
        return None
    code, blame, _ = git(cfg, 'blame', '--line-porcelain', '-L', f'{fm_end + 1},{marker}', 'HEAD', '--', path, check=False, timeout=60)
    if code:
        return None
    times = [int(t) for t in re.findall(r'^author-time (\d+)$', blame, re.M)]
    if not times:
        return None
    compiled = lib.iso(max(times))[:10]
    return {'compiled_truth_changed': compiled, 'newest_timeline_entry': newest} if newest > compiled else None


def page_diff(cfg, base, path):
    code, out, _ = git(cfg, 'diff', '--no-color', '-U2', base, 'HEAD', '--', path, check=False, timeout=60)
    out = out if code == 0 else ''
    if len(out) > CONF['diff_chars']:
        out = out[:CONF['diff_chars']] + '\n[diff truncated]'
    return out


def old_claims(diff):
    """Phrases around values the diff replaced: a few words of context on each side of a removed token."""
    removed = [line[1:] for line in diff.splitlines() if line.startswith('-') and not line.startswith('---')]
    added = [line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')]
    added_words = {w.lower() for line in added for w in WORD.findall(line)}
    phrases = []
    for line in removed:
        if FRONTMATTER_KEY.match(line):
            continue
        words = WORD.findall(line)
        for i, w in enumerate(words):
            lw = w.lower()
            distinctive = any(ch.isdigit() for ch in lw) or (len(lw) >= 5 and lw not in STOP)
            if lw in added_words or not distinctive:
                continue
            window = words[max(0, i - 2):i + 3]
            if len(window) >= 3:
                phrases.append(window)
        if len(phrases) >= 6:
            break
    return phrases[:6]


def propagation(cfg, path, diff, scope_dirs):
    """Other pages that still carry a phrase the diff replaced."""
    out = []
    for words in old_claims(diff):
        pattern = r'[^[:alnum:]]+'.join(re.escape(w).replace('\\-', '-') for w in words)
        code, hits, _ = git(cfg, 'grep', '-i', '-l', '-E', '-e', pattern, 'HEAD', '--', *scope_dirs, check=False, timeout=60)
        files = [h.split(':', 1)[1] for h in hits.splitlines() if ':' in h]
        files = [f for f in files if f != path and area_class(f) in ('editable', 'records')][:8]
        if files:
            out.append({'old_phrase': ' '.join(words), 'still_on': files})
    return out


def semantic(cfg, repo, query, exclude):
    """Top semantic hits on the page's title and lede: [(path, snippet)], or None when search failed."""
    try:
        code, out, err = lib.run(['gbrain', 'query', query, '--limit', str(CONF['semantic_hits'] + 10), '--json'], timeout=90, check=False)
    except (Failed, OSError):
        return None
    start = out.find('[')
    if code or start < 0:
        return None
    try:
        rows = json.loads(out[start:])
    except json.JSONDecodeError:
        return None
    hits, seen = [], set(exclude)
    for row in rows:
        path = (row.get('slug') or '') + '.md'
        if path in seen or area_class(path) not in ('editable', 'records') or not (repo / path).is_file():
            continue
        seen.add(path)
        hits.append((path, ' '.join((row.get('chunk_text') or '').split())[:700]))
        if len(hits) >= CONF['semantic_hits']:
            break
    return hits


def cmd_next(cfg, args):
    meta = lib.current_run(cfg, args.run)
    run_id = meta['run_id']
    rec = run_record(cfg, run_id)
    state = load_state(cfg)
    queue = state.get('queue', {})
    elapsed = lib.now() - meta['started_at']
    if elapsed > CONF['budget_seconds']:
        print(json.dumps({'done': True, 'reason': f'time budget of {CONF["budget_seconds"]}s used; the rest rolls to the next run',
                          'left': len(queue), 'finish': f'{CMD} finish --run {run_id}'}))
        return 0
    room = CONF['max_pages'] - sum(len(b['targets']) for b in rec['batches'])
    if room <= 0:
        print(json.dumps({'done': True, 'reason': f'page cap of {CONF["max_pages"]} reached; the rest carries to the next run',
                          'left': len(queue), 'finish': f'{CMD} finish --run {run_id}'}))
        return 0
    lib.reset_clone(cfg)
    repo = Path(cfg['maintenance_repo'])
    author = maintenance_author(cfg)
    cooling = cooldown(cfg, author)
    targets = []
    for path, entry in sorted(queue.items(), key=lambda kv: kv[1].get('queued_at', '')):
        if not (repo / path).is_file():
            queue.pop(path)
            continue
        if path in cooling:
            continue
        if entry.get('attempts', 0) >= CONF['max_attempts']:
            queue.pop(path)
            rec['dropped'].append(path)
            lib.journal(cfg, run_id, 'problem', text=f'`{path}` dropped from the review queue after {CONF["max_attempts"]} batches without an apply.')
            continue
        entry['attempts'] = entry.get('attempts', 0) + 1
        targets.append(path)
        if len(targets) >= min(CONF['batch_size'], room):
            break
    save_state(cfg, state)
    if not targets:
        save_run(cfg, run_id, rec)
        waiting = sum(1 for p in queue if p in cooling)
        print(json.dumps({'done': True, 'reason': 'queue empty' if not queue else f'{waiting} queued page(s) wait out the maintenance cooldown',
                          'left': len(queue), 'finish': f'{CMD} finish --run {run_id}'}))
        return 0

    scope = [p for p in git(cfg, 'ls-files', '--', '*.md').splitlines() if area_class(p)]
    links = LinkIndex(repo, scope)
    scope_dirs = sorted(CONF['areas']['editable'] + CONF['areas']['records'])
    findings, lint_error = lint(cfg, set(targets), lib.run_dir(cfg, run_id))
    if lint_error:
        lib.journal(cfg, run_id, 'note', text=f'gbrain lint unavailable: {lint_error[:200]}')
    pages, entries, semantic_failed = {}, [], False

    def add_page(path, why, snippet=None, target=False):
        cls = area_class(path)
        if not cls or not (repo / path).is_file():
            return False
        page = pages.get(path)
        if not page:
            text = read(repo, path) or ''
            title, lede = title_and_lede(text)
            page = pages[path] = {'path': path, 'title': title, 'class': cls, 'sha256': lib.sha256(repo / path),
                                  'editable': (cls == 'editable' or (cls == 'records' and target)) and path not in cooling,
                                  'why': [], 'snippet': snippet or lede}
        if target:
            page['editable'] = path not in cooling
        if snippet and not page['snippet']:
            page['snippet'] = snippet
        for w in why:
            if w not in page['why']:
                page['why'].append(w)
        return True

    for path in targets:
        entry = queue[path]
        add_page(path, [], target=True)
        text = read(repo, path) or ''
        title, lede = title_and_lede(text)
        diff = page_diff(cfg, entry['base'], path)
        item = {'path': path, 'title': title, 'class': area_class(path), 'sha256': pages[path]['sha256'],
                'reason': entry.get('reason', 'changed'), 'authors': entry.get('authors', []),
                'new_page': diff.startswith('diff --git') and '\nnew file mode' in diff[:300],
                'diff': diff, 'lint': (findings or {}).get(path, []),
                'stale_compiled_truth': stale_compiled_truth(cfg, repo, path),
                'propagation': propagation(cfg, path, diff, scope_dirs) if diff else [], 'neighbours': []}
        hits = semantic(cfg, repo, f'{title}. {lede}'.strip(), [path])
        if hits is None:
            semantic_failed = True
            hits = []
        # most telling first: claims to propagate, same-topic pages, then one-hop links, editable before records and context
        rank = {'editable': 0, 'records': 1, 'context': 2}
        near = [(p, f'still carries "{prop["old_phrase"]}"', None) for prop in item['propagation'] for p in prop['still_on']]
        near += [(p, f'semantic neighbour of {path}', snip) for p, snip in hits]
        near += [(c, f'context for deferred alignment of {path}', None) for c in entry.get('context', [])]
        hop = [(t, f'linked from {path}', None) for t in links.out.get(path, ())]
        hop += [(s, f'links to {path}', None) for s in links.inbound.get(path, ())]
        near += sorted(hop, key=lambda h: (rank.get(area_class(h[0]), 3), h[0]))
        for other, why, snip in near:
            if len(item['neighbours']) >= CONF['neighbour_cap']:
                break
            if other != path and add_page(other, [why], snip) and other not in item['neighbours']:
                item['neighbours'].append(other)
        rec['lint'] = rec.get('lint', 0) + len(item['lint'])
        entries.append(item)
    if semantic_failed:
        lib.journal(cfg, run_id, 'problem', text='gbrain query failed for at least one page, so its semantic neighbours are missing.')

    number = len(rec['batches']) + 1
    packet = {
        'run_id': run_id, 'batch': number, 'repo': cfg['maintenance_repo'], 'rubric': str(SKILL_DIR / 'rubric.md'),
        'verdicts_file': str(lib.run_dir(cfg, run_id) / f'verdicts-{number}.json'),
        'apply': f'{CMD} apply --run {run_id} --batch {number} {lib.run_dir(cfg, run_id) / f"verdicts-{number}.json"}',
        'targets': entries, 'pages': pages,
    }
    path = lib.run_dir(cfg, run_id) / f'batch-{number}.json'
    lib.atomic(path, packet)
    rec['batches'].append({'batch': number, 'targets': targets, 'applied': False})
    save_run(cfg, run_id, rec)
    print(json.dumps({'batch': number, 'packet': str(path), 'targets': targets, 'pages': len(pages),
                      'verdicts_file': packet['verdicts_file'], 'apply': packet['apply']}, indent=2))
    return 0


# the review guards, then apply.py

def proposal_action(cfg, run_id, fingerprint, n, verdict):
    key = hashlib.sha1(fingerprint.encode()).hexdigest()[:12]
    path = review_dir(cfg) / 'proposals' / f'{key}-{n}.json'
    lib.atomic(path, verdict)
    return {'type': 'command', 'argv': ['scripts/review.py', 'apply-option', str(path)]}


def check_verdict(v, packet, targets, cooling, seen):
    """The review's own guards on one verdict; return the reason it is refused, or None."""
    op = v.get('op')
    if op == 'NOOP':
        return None
    if op == 'FLAG':
        return None if v.get('fingerprint') and v.get('options') else 'a FLAG needs a fingerprint and options'
    if op not in ('UPDATE', 'ADD', 'DELETE'):
        return f'{op} is not a review op; page moves belong to the relevance routine'
    if op == 'DELETE' and not v.get('old'):
        return 'whole-page deletion belongs to the relevance routine; FLAG it instead'
    path = os.path.normpath(v.get('path') or '')
    page = packet['pages'].get(path)
    if not page:
        return f'{path} is not in this batch packet'
    if path in seen:
        return f'second verdict on {path} in one batch'
    if path in cooling:
        return 'cooldown: the maintenance writer edited this page in the last few days'
    if not page['editable'] and not (page['class'] == 'records' and path in targets):
        return f'{path} is read-only for the review ({page["class"]})'
    if page['class'] == 'records' and path not in targets:
        return f'{path} is a record and only its own lint is repaired'
    return None


def cmd_apply(cfg, args):
    meta = lib.current_run(cfg, args.run)
    run_id = meta['run_id']
    packet = lib.read_json(lib.run_dir(cfg, run_id) / f'batch-{args.batch}.json')
    if not packet:
        raise Failed(f'batch {args.batch} has no packet in run {run_id}')
    data = json.loads(Path(args.verdicts).read_text())
    verdicts = data['verdicts'] if isinstance(data, dict) else data
    rec = run_record(cfg, run_id)
    state = load_state(cfg)
    targets = [t['path'] for t in packet['targets']]
    cooling = cooldown(cfg, maintenance_author(cfg))
    passed, refused, seen = [], [], set()
    for v in verdicts:
        reason = check_verdict(v, packet, targets, cooling, seen)
        op = v.get('op')
        if reason:
            refused.append({'verdict': v, 'reason': reason})
            if reason.startswith('cooldown') and op in ('UPDATE', 'ADD', 'DELETE'):
                entry = state['queue'].setdefault(os.path.normpath(v['path']), {
                    'base': git(cfg, 'rev-parse', 'HEAD'), 'queued_at': lib.iso(), 'reason': 'deferred', 'attempts': 0, 'context': []})
                entry['context'] = sorted(set(entry.get('context', [])) | set(targets))
                rec['deferred'] += 1
            continue
        if op in ('UPDATE', 'ADD', 'DELETE'):
            v['path'] = os.path.normpath(v['path'])
            v['sha256'] = v.get('sha256') or packet['pages'][v['path']]['sha256']
            seen.add(v['path'])
        if op == 'FLAG':
            fp = v['fingerprint'] if v['fingerprint'].startswith(RID + ':') else f'{RID}:{v["fingerprint"]}'
            v = dict(v, fingerprint=fp, evidence=[e if isinstance(e, str) else f'`{e.get("path")}`: "{e.get("quote")}"' for e in v.get('evidence') or []], options=[
                {'label': o['label'], 'detail': o.get('detail', ''),
                 'action': proposal_action(cfg, run_id, fp, n, o['verdict']) if o.get('verdict') else {'type': 'close'}}
                for n, o in enumerate(v['options'], 1)])
        passed.append(v)
    writes = [v for v in passed if v.get('op') in ('UPDATE', 'ADD', 'DELETE')]
    if state.get('held') and writes:
        lib.journal(cfg, run_id, 'note', text=f'Batch {args.batch}: writes are held, so {len(writes)} edit verdict(s) were judged and not applied.')
        passed = [v for v in passed if v not in writes]
        for v in writes:
            refused.append({'verdict': v, 'reason': 'held: review writes are held by the owner'})
    result = applylib.Applier(cfg, meta).apply(passed) if passed else {'applied': [], 'rejected': [], 'flagged': [], 'noop': 0}
    for path in targets:
        state['queue'].pop(path, None)
    save_state(cfg, state)
    for v in verdicts:
        op = v.get('op', '?')
        rec['ops'][op] = rec['ops'].get(op, 0) + 1
    rec['review_rejected'] += [{'path': r['verdict'].get('path'), 'op': r['verdict'].get('op'), 'reason': r['reason']} for r in refused]
    for b in rec['batches']:
        if b['batch'] == args.batch:
            b.update(applied=True, commits=len(result['applied']), rejected=len(result['rejected']) + len(refused), flagged=len(result['flagged']))
    save_run(cfg, run_id, rec)
    if refused:
        reasons = {}
        for r in refused:
            key = r['reason'].split(':', 1)[0]
            reasons[key] = reasons.get(key, 0) + 1
        lib.journal(cfg, run_id, 'note', text=f'Batch {args.batch}: {len(refused)} verdict(s) refused by the review guards: '
                    + '; '.join(f'{k} ({n})' for k, n in reasons.items()) + '.')
    print(json.dumps({'batch': args.batch, 'applied': result['applied'], 'flagged': result['flagged'], 'noop': result['noop'],
                      'rejected': [{'path': r['verdict'].get('path'), 'op': r['verdict'].get('op'), 'reason': r['reason']}
                                   for r in result['rejected'] + refused],
                      'next': f'{CMD} next --run {run_id}'}, ensure_ascii=False, indent=2))
    return 0


# owner replies

def cmd_apply_option(cfg, args):
    """The owner chose an option that carries an edit: apply it against the page as it is now."""
    meta = lib.current_run(cfg)
    verdict = lib.read_json(args.proposal)
    if not verdict:
        raise Failed(f'proposal {args.proposal} is missing')
    lib.reset_clone(cfg)
    path = os.path.normpath(verdict['path'])
    if not (Path(cfg['maintenance_repo']) / path).is_file():
        raise Failed(f'{path} no longer exists')
    verdict = dict(verdict, path=path, sha256=lib.sha256(Path(cfg['maintenance_repo']) / path),
                   reason=f'Owner chose option {os.environ.get("ATTENTION_OPTION", "?")} on {os.environ.get("ATTENTION_ISSUE", "a needs-attention issue")}. '
                          + (verdict.get('reason') or ''))
    result = applylib.Applier(cfg, meta).apply([verdict])
    if not result['applied']:
        reason = result['rejected'][0]['reason'] if result['rejected'] else 'nothing applied'
        if reason.startswith('not pushed'):
            raise Failed(reason)  # transient: the reply loop retries on the next run
        Path(args.proposal).unlink(missing_ok=True)
        print(json.dumps({'note': f'The chosen edit no longer applies to `{path}` ({reason}); the page changed since the issue was filed, '
                                  'and the next review judges it again.'}))
        return 0
    Path(args.proposal).unlink(missing_ok=True)
    print(json.dumps({'note': f'Applied the chosen edit to `{path}`.', 'commits': [a['url'] for a in result['applied']]}))
    return 0


def cmd_hold(cfg, args):
    state = load_state(cfg)
    state['held'] = args.on
    save_state(cfg, state)
    print(json.dumps({'note': 'Review writes are held: verdicts are judged and reported, nothing is applied.' if args.on
                      else 'Review writes are released: the next run applies verdicts again.'}))
    return 0


# the run summary

def miss_check(cfg, meta, report):
    wf = report['workflows'].get(meta['workflow'])
    if not wf or not wf['misses'] or wf['rate'] <= CONF['judge_miss']['threshold']:
        return
    misses = [m for m in report['misses'] if m['workflow'] == meta['workflow']]
    key = hashlib.sha1(' '.join(sorted(m['commit'] for m in misses)).encode()).hexdigest()[:12]
    lib.file_attention(
        cfg, meta, f'{RID}:judge-miss:{key}',
        f'{cfg["brain"]} daily change review: judge-miss rate {wf["rate"]:.0%} over {wf["edits"]} edits',
        f'{wf["misses"]} of the {wf["edits"]} edits the review made in the last {report["lookback_days"]} days were reverted or rewritten '
        f'by another writer within {report["window_days"]} days, over the {CONF["judge_miss"]["threshold"]:.0%} threshold.',
        'A miss means the judge got a page wrong in a way a person or agent had to correct; only the owner can say whether the rubric or the evidence rule needs to change.',
        [f'{m["op"]} `{m["path"]}` {m["url"]} - {m["by_author"]} {m["how"]} in {m["by_url"]}' for m in misses[:20]],
        [{'label': 'Keep the routine as it is', 'detail': 'the misses are isolated corrections', 'action': {'type': 'close'}},
         {'label': 'Hold the review writes', 'detail': 'runs keep judging and reporting but apply nothing until released',
          'action': {'type': 'command', 'argv': ['scripts/review.py', 'hold', '--on']}}],
        1 if wf['misses'] < 3 else 2,
        'a single miss in a small sample is noise' if wf['misses'] < 3 else 'repeated misses point at the rubric')


def cmd_finish(cfg, args):
    meta = lib.current_run(cfg, args.run)
    run_id = meta['run_id']
    rec = run_record(cfg, run_id)
    state = load_state(cfg)
    try:
        report = judge_misses.compute(cfg, CONF)
        wf = report['workflows'].get(meta['workflow'], {'edits': 0, 'misses': 0, 'open': 0, 'rate': 0.0})
        lib.journal(cfg, run_id, 'note', text=f'Judge misses, last {report["lookback_days"]} days: {wf["misses"]} of {wf["edits"]} review edits '
                    f'({wf["rate"]:.0%}), {wf["open"]} still inside the {report["window_days"]}-day window.')
        miss_check(cfg, meta, report)
    except Failed as error:
        lib.journal(cfg, run_id, 'problem', text=f'Judge-miss check failed: {error}')
    if state.get('held'):
        lib.file_attention(
            cfg, meta, f'{RID}:held', f'{cfg["brain"]} daily change review writes are held',
            'The daily change review judges and reports, but applies no edit.',
            'The owner chose to hold the review writes; only the owner releases them.',
            ['The hold was set through a judge-miss needs-attention option.'],
            [{'label': 'Release the hold', 'detail': 'the next run applies verdicts again',
              'action': {'type': 'command', 'argv': ['scripts/review.py', 'hold', '--off']}}], 1)
    judged = sum(len(b['targets']) for b in rec['batches'] if b.get('applied'))
    applied = sum(b.get('commits', 0) for b in rec['batches'])
    rejected = sum(b.get('rejected', 0) for b in rec['batches'])
    flagged = sum(b.get('flagged', 0) for b in rec['batches'])
    left = len(state.get('queue', {}))
    if left and sum(len(b['targets']) for b in rec['batches']) >= CONF['max_pages']:
        lib.journal(cfg, run_id, 'note', text=f'Page cap: the run judged its {CONF["max_pages"]} pages, and {left} page(s) carry over to the next run, oldest first.')
    summary = args.summary or (f'{judged} changed page(s) judged in {len(rec["batches"])} batch(es): {applied} edit(s) applied, '
                               f'{rejected} refused, {flagged} flagged, {left} carried over to the next run')
    counts = {'pages judged': judged, 'lint findings': rec.get('lint', 0), 'noop': rec['ops'].get('NOOP', 0),
              'deferred by cooldown': rec['deferred']}
    status = args.status
    if status == 'ok' and any(not b.get('applied') for b in rec['batches']):
        lib.journal(cfg, run_id, 'problem', text='A batch packet was built but never applied; its pages are retried next run.')
    sys.path.insert(0, str(FRAMEWORK))
    import routine as rt
    rt.end(cfg, meta, status, summary, {k: v for k, v in counts.items() if v})
    print(json.dumps({'ended': run_id, 'status': status, 'summary': summary}, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('prep', 'next'):
        sub.add_parser(name).add_argument('--run', required=True)
    c = sub.add_parser('apply')
    c.add_argument('--run', required=True)
    c.add_argument('--batch', type=int, required=True)
    c.add_argument('verdicts')
    c = sub.add_parser('finish')
    c.add_argument('--run', required=True)
    c.add_argument('--status', choices=('ok', 'partial', 'failed'), default='ok')
    c.add_argument('--summary', default='')
    c = sub.add_parser('apply-option')
    c.add_argument('proposal')
    c = sub.add_parser('hold')
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument('--on', dest='on', action='store_true')
    g.add_argument('--off', dest='on', action='store_false')
    args = p.parse_args()
    cfg = lib.config()
    return {'prep': cmd_prep, 'next': cmd_next, 'apply': cmd_apply, 'finish': cmd_finish,
            'apply-option': cmd_apply_option, 'hold': cmd_hold}[args.command](cfg, args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
