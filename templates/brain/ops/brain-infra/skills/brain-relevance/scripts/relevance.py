#!/usr/bin/env python3
"""The relevance routine's code: candidate selection with zero LLM, the guards on the agent's
judgments, and the end of the run. The agent judges; apply.py from brain-routines writes.

  relevance.py prep --run <run_id> [--slice <name>]   build the work packet and the brief for one slice
  relevance.py apply --run <run_id> [<judgments>]     check judgments (default <run dir>/judgments.jsonl) and apply them
  relevance.py finish --run <run_id>                  end the run with its summary and advance the rotation
  relevance.py queue <slice>...                       judge these slices next, ahead of the rotation; a slice
                                                      may also be page paths, comma-separated
  relevance.py status                                 the rotation, the queue and the last slices
  relevance.py option <file>                          apply a needs-attention option the owner chose

A judgment is one JSON object per line:

  {"path", "verdict": "keep", "reason"}
  {"path", "verdict": "update", "old", "new", "evidence", "summary", "reason"}     or "after" instead of "old" to add
  {"path", "verdict": "archive" | "delete", "summary", "reason"}
  {"path", "verdict": "merge", "into", "same_subject", "summary", "reason", "update": {"old" | "after", "new", "evidence"}}
  {"path", "verdict": "restore", "status", "summary", "reason"}
  {"path", "verdict": "file", "to", "type", "status", "summary", "reason"}
  {"path", "verdict": "flag", "finding", "why", "options": [{"label", "detail", "judgment": {...}}], "recommended", "recommended_reason"}

evidence is [{"path", "quote"}], an exact quote from a brain page.
"""
import argparse
import collections
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True  # routines write nothing into the published copy
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR.parent / 'brain-routines' / 'scripts'))
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402
import apply as ap  # noqa: E402

APPLY = SKILL_DIR.parent / 'brain-routines' / 'scripts' / 'apply.py'
DATE = re.compile(r'\b(20\d\d-[01]\d-[0-3]\d)\b')
TIMELINE_ROW = re.compile(r'^- \*\*(20\d\d-[01]\d-[0-3]\d)\*\*', re.M)
SLUG_DATE = re.compile(r'(?:^|[/-])r?-?(20\d\d)-?([01]\d)-?([0-3]\d)')
TIME_WORDS = re.compile(r'\b(upcoming|scheduled|planned|next week|next month|tomorrow|due|deadline|until|expires?|pending|waiting for|will|this week|currently)\b', re.I)
VERDICTS = ('keep', 'update', 'archive', 'delete', 'merge', 'restore', 'file', 'flag')
SETTLED = ('applied', 'kept', 'flagged', 'held', 'rejected')


class Invalid(Exception):
    """A judgment breaks the relevance guards; nothing was applied for it."""


def rconfig():
    return lib.read_json(SKILL_DIR / 'config.json')


def today():
    return dt.date.today()


def days_since(date):
    try:
        return (today() - dt.date.fromisoformat(date)).days
    except (TypeError, ValueError):
        return None


def under(path, prefixes):
    return any(path == p or path.startswith(p) for p in prefixes)


def frontmatter(text):
    """Top-level scalars and lists of a page's YAML frontmatter as strings: enough for signals."""
    fm = {}
    if not text.startswith('---\n'):
        return fm
    close = text.find('\n---', 4)
    if close < 0:
        return fm
    key = None
    for line in text[4:close].split('\n'):
        m = re.match(r'^([A-Za-z_][\w-]*):\s*(.*)$', line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if value.startswith('[') and value.endswith(']'):
                fm[key] = [ap.unquote(x) for x in value[1:-1].split(',') if x.strip()]
            elif value == '':
                fm[key] = []
            else:
                fm[key] = ap.unquote(value)
        elif key and isinstance(fm.get(key), list) and re.match(r'^\s*-\s+', line):
            fm[key].append(ap.unquote(re.sub(r'^\s*-\s+', '', line)))
    return fm


def body_of(text):
    if text.startswith('---\n'):
        close = text.find('\n---', 4)
        if close >= 0:
            return text[close + 4:]
    return text


def compiled_truth(text):
    body = body_of(text)
    return body.split('<!-- timeline -->', 1)[0]


# state: the rotation and the queue

def state_path(cfg):
    return lib.state_dir(cfg) / 'relevance.json'


def load(cfg):
    return lib.read_json(state_path(cfg), {'queue': [], 'last': None, 'history': []})


def save(cfg, state):
    lib.atomic(state_path(cfg), state)


def next_slice(rc, state):
    """The slice the next run judges and where it came from: the queue first, then the rotation."""
    if state['queue']:
        return state['queue'][0], 'queue'
    last = state.get('last')
    order = rc['rotation']
    if not last or last['slice'] not in order:
        return order[0], 'rotation'
    if not last.get('complete'):
        return last['slice'], 'rotation'
    return order[(order.index(last['slice']) + 1) % len(order)], 'rotation'


def page_slice(name):
    """A slice named by its pages, comma-separated, for a review on request."""
    return [] if name in (None, '') or '/' not in name else [p.strip() for p in name.split(',') if p.strip()]


def slice_label(name):
    """A slice's name for the brief and the run record: a long page slice reads as its count and common directory."""
    pages = page_slice(name)
    if len(pages) <= 3:
        return name
    common = os.path.commonpath(pages)
    return f'{len(pages)} pages' + (f' under {common}/' if common else '')


# the brain as data

class Brain:
    def __init__(self, cfg, rc, repo=None):
        self.cfg, self.rc = cfg, rc
        self.repo = Path(repo or cfg['published_repo'])
        files = lib.run(['git', '-C', self.repo, 'ls-files', '--', '*.md'], timeout=60).splitlines()
        self.files = [f for f in files if f]
        self.fileset = set(self.files)
        self.text = {f: (self.repo / f).read_text(errors='replace') for f in self.files}
        self.fm = {f: frontmatter(t) for f, t in self.text.items()}
        self.inbound = collections.defaultdict(list)
        for src in self.files:
            self.scan_links(src)
        self.last_commit = self.commit_dates()

    def scan_links(self, src):
        text = self.text[src]
        close = text.find('\n---', 4) if text.startswith('---\n') else -1
        if close > 0:
            for line in text[4:close].split('\n'):
                if '://' in line:
                    continue
                for m in ap.REF.finditer(line):
                    target = ap.ref_target(src, m.group('p'))
                    if target != src:
                        self.inbound[target].append({'from': src, 'where': 'frontmatter', 'cite': False})
        for line in body_of(text).split('\n'):
            for m in ap.LINK.finditer(line):
                target, _ = ap.link_target(src, m.group(2))
                if target and target != src:
                    before = line[:m.start()]
                    cite = before.rfind('[Source') > before.rfind(']') or before.rstrip().endswith('(via')
                    self.inbound[target].append({'from': src, 'where': 'body', 'cite': cite})

    def commit_dates(self):
        out = lib.run(['git', '-C', self.repo, 'log', '--format=@%ad', '--date=short', '--name-only', '--', '*.md'], timeout=300)
        dates, current = {}, None
        for line in out.splitlines():
            if line.startswith('@'):
                current = line[1:]
            elif line and line not in dates:
                dates[line] = current
        return dates

    def kind(self, path):
        if path.startswith(self.rc['archive']):
            path = path[len(self.rc['archive']):]
        for prefix, kind in sorted(self.rc['kinds'].items(), key=lambda kv: -len(kv[0])):
            if path.startswith(prefix):
                return kind
        return 'knowledge'

    def live_source(self, src):
        rc = self.rc
        return not (src.startswith(rc['archive']) or under(src, rc['ledger']) or self.kind(src) == 'research'
                    or src in rc['not_live'] or src.endswith('/README.md'))

    def reviewable(self, path):
        rc = self.rc
        return not (path.startswith(rc['archive']) or under(path, rc['ledger']) or under(path, rc['unpruned'])
                    or under(path, rc['not_reviewed']) or path.endswith('README.md') or path in rc['not_live'])

    def page_date(self, path):
        """A record's own date: its slug, then meeting_date or created, then a Date line, then its first commit."""
        fm = self.fm[path]
        m = SLUG_DATE.search(os.path.basename(path))
        if m:
            return '-'.join(m.groups())
        for key in ('meeting_date', 'email_date', 'date', 'created'):
            if isinstance(fm.get(key), str) and DATE.match(fm[key]):
                return fm[key][:10]
        m = re.search(r'\*\*Date:\*\*\s*(20\d\d-\d\d-\d\d)', self.text[path])
        return m.group(1) if m else self.last_commit.get(path)

    def evidence(self, path):
        """The latest interaction evidence for a page: its own timeline rows and the linking records of the evidence kinds."""
        best = (None, None)
        rows = TIMELINE_ROW.findall(self.text[path])
        if rows:
            best = (max(rows), 'timeline row')
        archive = self.rc['archive']
        links = self.inbound.get(path, []) + (self.inbound.get(path[len(archive):], []) if path.startswith(archive) else [])
        for link in links:
            if self.kind(link['from']) in self.rc['evidence_kinds']:
                date = self.page_date(link['from'])
                if date and (best[0] is None or date > best[0]):
                    best = (date, link['from'])
        return {'date': best[0], 'from': best[1]}

    def sources(self, path):
        return [s for s in self.rc['tool_sources'] if self.fm[path].get(s)]

    def archived(self, path):
        """Archived: under archive/, or carrying status archived in place."""
        return path.startswith(self.rc['archive']) or self.fm.get(path, {}).get('status') == 'archived'

    def refs(self, src, keys):
        """The brain pages the frontmatter keys of page src name."""
        out = []
        for key in keys:
            value = self.fm[src].get(key) or []
            for ref in value if isinstance(value, list) else [value]:
                if ref and ref != 'null':
                    out.append(ap.ref_target(src, ref))
        return out

    def named_by(self, spec):
        """For spec {prefix: [keys]}: each page that the frontmatter keys of pages under the prefix name,
        mapped to the pages naming it."""
        names = collections.defaultdict(list)
        for src in self.files:
            for prefix, keys in spec.items():
                if src.startswith(prefix) and not src.endswith('README.md'):
                    for target in self.refs(src, keys):
                        names[target].append(src)
        return names

    def task_state(self, path):
        """A task's place in the task rule: closed past retention, with the pages naming it, or paused past
        its window; None for every other task and for a brain without the rule."""
        t, d = self.rc.get('tasks') or {}, self.rc['days']
        if not t:
            return None
        fm = self.fm[path]
        status = fm.get('status') if isinstance(fm.get('status'), str) else ''
        if status in t['closed']:
            done = fm.get(t['completed_key'])
            closed = days_since(done[:10]) if isinstance(done, str) and done else days_since(self.last_commit.get(path))
            if closed is not None and closed >= d['task_retention']:
                if not hasattr(self, '_task_names'):
                    self._task_names = self.named_by(t['named_by'])
                return {'state': 'closed', 'days': closed, 'named_by': sorted(set(self._task_names.get(path, [])))}
        elif status == t['paused']:
            updated = fm.get('updated') if isinstance(fm.get('updated'), str) else ''
            last = max(filter(None, [updated[:10], self.last_commit.get(path)]), default=None)
            quiet = days_since(last)
            if quiet is not None and quiet >= d['task_paused']:
                return {'state': 'paused', 'days': quiet, 'named_by': []}
        return None


def eval_refs(brain):
    """Pages a retrieval-eval case names: any brain page path or slug in the eval set; no set means none."""
    refs = set()
    qrels = brain.repo / brain.rc['eval_set']
    if not qrels.is_file():
        return refs
    for token in re.findall(r'[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)+', qrels.read_text(errors='replace')):
        path = token if token.endswith('.md') else token + '.md'
        if path in brain.fileset:
            refs.add(path)
    return refs


def open_issues(cfg):
    raw = lib.gh(cfg, 'issue', 'list', '--repo', cfg['github_repo'], '--state', 'open', '--limit', '500',
                 '--json', 'number,title,url,body,labels', timeout=120)
    return json.loads(raw or '[]')


def ticket_refs(issues, path):
    slug = path[:-3]
    hits = []
    for issue in issues:
        body = issue.get('body') or ''
        if re.search(rf'(?<![\w/-]){re.escape(slug)}(?:\.md)?(?![\w-])', body):
            hits.append(f'#{issue["number"]} {issue["title"]}')
    return hits


def pending_pages(issues):
    """Pages with an open relevance needs-attention issue: they wait for the owner, not the judge."""
    pages = set()
    for issue in issues:
        if any(label['name'] == 'needs-attention' for label in issue.get('labels', [])):
            m = re.search(r'<!-- fingerprint: relevance:(\S+) -->', issue.get('body') or '')
            if m:
                pages.add(m.group(1))
    return pages


# candidate selection

def triggers(brain, path):
    """Why the relevance model asks for a review of a live page in a slice; empty means no review."""
    rc, fm, kind = brain.rc, brain.fm[path], brain.kind(path)
    d = rc['days']
    status = fm.get('status') if isinstance(fm.get('status'), str) else ''
    out = []
    if status == 'archived' and kind not in rc['archived_in_place']:
        out.append('status archived outside archive/: archive or delete')
    live_in = [i for i in brain.inbound.get(path, []) if brain.live_source(i['from'])]
    ev = brain.evidence(path)
    quiet = days_since(ev['date'])
    if kind in ('person', 'company'):
        types = fm.get(rc['relationship_key']) or []
        types = types if isinstance(types, list) else [types]
        if status == 'dormant' and (quiet is None or quiet >= d['dormant_review']):
            out.append(f'dormant with no interaction evidence for {d["dormant_review"]}+ days: archive, or active again')
        elif kind == 'person' and status != 'archived' and (quiet is None or quiet >= d['person_quiet']):
            out.append(f'no interaction evidence for {d["person_quiet"]}+ days: dormant or archive unless a thread is open')
        elif kind == 'company' and types and set(types) <= set(rc['prospect_types']) and (quiet is None or quiet >= d['prospect_quiet']):
            out.append(f'prospect with no engagement for {d["prospect_quiet"]}+ days: archive unless a pending thread is visible')
        elif kind == 'company' and status != 'archived' and (quiet is None or quiet >= d['relationship_quiet']):
            out.append(f'no interaction evidence for {d["relationship_quiet"]}+ days: archive if the relationship ended')
        if not live_in:
            out.append('no inbound links from live pages: check admission')
    elif kind in ('project', 'program'):
        if status in rc['terminal_statuses'].get(kind, []):
            if kind in rc['archivable']:
                out.append(f'{status}: archive when nothing current depends on it')
        elif status != 'archived':
            last = max(filter(None, [ev['date'], brain.last_commit.get(path)]), default=None)
            limit = d['project_quiet' if kind == 'project' else 'program_quiet']
            if days_since(last) is not None and days_since(last) >= limit:
                out.append(f'{status or "no status"} with no activity for {limit}+ days: status review')
    elif kind == 'tool':
        if fm.get('stance') == 'retired':
            out.append('retired with no news sources: archive' if not brain.sources(path)
                       else 'retired and still watched: stays in tools/')
    elif kind == 'task':
        t = brain.task_state(path)
        if t and t['state'] == 'closed':
            out.append(f'closed {t["days"]} days ago and named by {", ".join(t["named_by"][:3])}'
                       + (f' and {len(t["named_by"]) - 3} more' if len(t['named_by']) > 3 else '') + ': archive'
                       if t['named_by'] else f'closed {t["days"]} days ago and no page names it: delete')
        elif t:
            out.append(f'paused with no update for {t["days"]} days: flag for the owner')
    elif kind in rc['follows_subjects']:
        subjects = record_subjects(brain, path)
        if subjects and all(s['archived'] for s in subjects):
            out.append('every linked subject is archived: archive')
    elif kind == 'knowledge':
        age = days_since(brain.last_commit.get(path))
        if not live_in and age is not None and age >= d['knowledge_quiet']:
            out.append(f'no inbound links from live pages and unchanged for {d["knowledge_quiet"]}+ days')
    return out


def record_subjects(brain, path, archived=()):
    """The subjects a record links in its frontmatter (pages in the record_subjects areas, live or archived),
    each with whether it is archived; pages in `archived` count as archived."""
    subjects = []
    for target in brain.refs(path, ('related_pages', 'related')):
        if target not in brain.fileset:
            continue
        area = target.split('/', 1)[0]
        if area in brain.rc['record_subjects'] or target.startswith(brain.rc['archive']):
            subjects.append({'path': target, 'archived': brain.archived(target) or target in archived})
    return subjects


def drift_score(brain, path):
    """How many sentences in the compiled truth pair a past date with time-sensitive wording."""
    score = 0
    for sentence in re.split(r'(?<=[.!?])\s+|\n', compiled_truth(brain.text[path])):
        dates = [x for x in DATE.findall(sentence) if (days_since(x) or 0) > 0]
        if dates and TIME_WORDS.search(sentence):
            score += 1
    return score


def allowed(brain, path, group):
    kind = brain.kind(path)
    rc = brain.rc
    if group == 'drift':
        return ['keep', 'update', 'flag']
    if group == 'restore':
        return ['keep', 'restore', 'flag']
    if group == 'inbox':
        return ['delete', 'file', 'flag']
    if group == 'research':
        return ['keep', 'delete', 'flag']
    if kind in rc['never_removed']:
        return ['keep', 'update', 'flag']
    if kind == 'task':
        t = brain.task_state(path)
        if not t:
            return ['keep', 'update', 'flag']
        if t['state'] == 'paused':
            return ['flag']
        return ['keep', 'archive', 'flag'] if t['named_by'] and 'task' in rc['archivable'] else ['keep', 'delete', 'flag']
    verbs = ['keep', 'update', 'delete', 'merge', 'flag']
    if kind in rc['follows_subjects']:
        verbs = ['keep', 'delete', 'merge', 'flag']
    if kind in rc['archivable']:
        verbs.insert(2, 'archive')
    return verbs


def option_verbs(brain, path, group):
    """The verdicts a flag's options may carry: the page's own, and keep or update for a long-paused task."""
    if group == 'slice' and brain.kind(path) == 'task' and (brain.task_state(path) or {}).get('state') == 'paused':
        return ['keep', 'update']
    return allowed(brain, path, group)


def entry(brain, path, group, why, issues, evals, names):
    fm, rc = brain.fm[path], brain.rc
    inbound = brain.inbound.get(path, [])
    by_area = collections.Counter(i['from'].split('/', 1)[0] if '/' in i['from'] else i['from'] for i in inbound)
    live = [i for i in inbound if brain.live_source(i['from'])]
    hard = []
    if path in evals:
        hard.append('eval: a retrieval-eval case names this page')
    cited = sorted({i['from'] for i in live if i['cite']})
    if cited:
        hard.append('cited: live pages cite it as a source: ' + ', '.join(cited[:5]))
    naming = sorted({src for src in names.get(path, []) if not brain.archived(src)})
    if naming:
        hard.append('named: live pages name it in a kept field: ' + ', '.join(naming[:5]))
    fields = {k: fm[k] for k in ('type', 'title', 'status', rc['relationship_key'], 'stance', 'created', 'updated', 'completed',
                                 'meeting_date', 'email_date')
              if fm.get(k) not in (None, [], '')}
    return {
        'path': path, 'group': group, 'kind': brain.kind(path), 'sha256': lib.sha256(brain.repo / path),
        'fields': fields, 'last_commit': brain.last_commit.get(path), 'evidence': brain.evidence(path),
        'record_date': brain.page_date(path) if group in ('inbox', 'research') else None,
        'inbound': {'total': len(inbound), 'live': len(live), 'by_area': dict(by_area.most_common()),
                    'live_from': sorted({i['from'] for i in live})[:10]},
        'sources': brain.sources(path) if brain.kind(path) == 'tool' else None,
        'triggers': why, 'hard_keeps': hard, 'tickets': ticket_refs(issues, path),
        'allowed': allowed(brain, path, group), 'option_verbs': option_verbs(brain, path, group),
    }


def build_packet(cfg, rc, meta, slice_name, brain=None, issues=None):
    requested = page_slice(slice_name)
    if slice_name not in rc['slices'] and not requested:
        raise Failed(f'unknown slice {slice_name}; slices: {", ".join(rc["slices"])}, or page paths')
    brain = brain or Brain(cfg, rc)
    for path in requested:
        if path not in brain.fileset or not brain.reviewable(path):
            raise Failed(f'{path} is not a page the relevance routine reviews')
    issues = open_issues(cfg) if issues is None else issues
    waiting = pending_pages(issues)
    evals = eval_refs(brain)
    names = brain.named_by(rc['named_keeps'])
    d = rc['days']
    pages, skipped = {}, []

    def add(path, group, why):
        if path in waiting:
            skipped.append(path)
        elif path not in pages:
            pages[path] = entry(brain, path, group, why, issues, evals, names)

    slice_pages = requested or [p for p in brain.files if under(p, rc['slices'][slice_name]) and brain.reviewable(p)]
    for path in slice_pages:
        if brain.kind(path) in ('inbox', 'research') and not requested:
            continue
        why = triggers(brain, path)
        if requested:
            add(path, 'slice', ['review requested'] + why)
        elif why and not why[0].startswith('retired and still watched'):
            add(path, 'slice', why)
    # the standing rules, every run
    for path in brain.files:
        kind = brain.kind(path)
        if path.endswith('README.md') or not brain.reviewable(path) and not path.startswith(rc['archive']):
            continue
        if kind == 'inbox' and not path.startswith(rc['archive']):
            age = days_since(brain.page_date(path))
            if age is not None and age > d['inbox']:
                add(path, 'inbox', [f'inbox item {age} days old: file or delete'])
        elif kind == 'research' and not path.startswith(rc['archive']):
            age = days_since(brain.page_date(path))
            if age is not None and age > d['research']:
                add(path, 'research', [f'research record {age} days old: delete unless a live page cites it for a decision in force'])
        elif path.startswith(rc['archive']) and kind in rc['restorable']:
            since = brain.last_commit.get(path)
            ev = brain.evidence(path)
            if ev['date'] and since and ev['date'] > since and ev['from'] != 'timeline row':
                add(path, 'restore', [f'interaction evidence {ev["date"]} ({ev["from"]}) after the move: restore?'])
    research = [p for p in brain.files if brain.kind(p) == 'research' and not p.startswith(rc['archive'])]
    by_question = collections.defaultdict(list)
    for p in research:
        stem = re.sub(r'^r-\d{8}-', '', os.path.basename(p))
        by_question[(os.path.dirname(p), stem)].append(p)
    for group in by_question.values():
        group = sorted(group, key=lambda p: brain.page_date(p) or '')
        for older in group[:-1]:
            add(older, 'research', [f'superseded by {group[-1]}'])
    # a bounded sample of unchanged pages for time-sensitive drift
    rest = [] if requested else [p for p in slice_pages if p not in pages and brain.kind(p) not in rc['drift_skip']]
    scored = sorted(((drift_score(brain, p), brain.last_commit.get(p) or '', p) for p in rest), key=lambda t: (-t[0], t[1]))
    for score, _, path in [t for t in scored if t[0] > 0][:rc['drift_sample']]:
        add(path, 'drift', [f'{score} time-sensitive statement(s) with a past date'])
    return {
        'run_id': meta['run_id'], 'slice': slice_name, 'built_at': lib.iso(), 'today': today().isoformat(),
        'slice_pages': len(slice_pages), 'pages': pages, 'waiting_on_owner': skipped,
        'eval_set': len(evals), 'brain_head': lib.run(['git', '-C', brain.repo, 'rev-parse', 'HEAD'], timeout=30),
    }


def brief(packet):
    groups = [('slice', f'Slice `{slice_label(packet["slice"])}`: review candidates'), ('inbox', 'Inbox items past the window'),
              ('research', 'Research records past retention or superseded'), ('restore', 'Archived pages with new interaction'),
              ('drift', 'Drift sample: unchanged pages with time-sensitive statements')]
    lines = [f'# Relevance packet {packet["run_id"]}', '',
             f'Slice `{slice_label(packet["slice"])}`: {packet["slice_pages"]} reviewable pages; {len(packet["pages"])} pages to judge in all. '
             f'Today is {packet["today"]}. Brain at {packet["brain_head"][:12]}.']
    if packet['waiting_on_owner']:
        lines.append('Skipped, waiting on an open needs-attention issue: ' + ', '.join(packet['waiting_on_owner']))
    for key, title in groups:
        items = [e for e in packet['pages'].values() if e['group'] == key]
        lines += ['', f'## {title} ({len(items)})']
        for e in items:
            lines += ['', f'### `{e["path"]}`', f'- kind {e["kind"]}; ' + '; '.join(f'{k}: {v}' for k, v in e['fields'].items())]
            lines.append('- triggers: ' + '; '.join(e['triggers']))
            ev = e['evidence']
            lines.append(f'- last interaction evidence: {ev["date"] or "none"}' + (f' ({ev["from"]})' if ev['from'] else '')
                         + f'; last commit {e["last_commit"]}' + (f'; record date {e["record_date"]}' if e['record_date'] else ''))
            ib = e['inbound']
            lines.append(f'- inbound links: {ib["total"]} ({", ".join(f"{a} {n}" for a, n in ib["by_area"].items()) or "none"}); '
                         f'from live pages: {ib["live"]}' + (f' ({", ".join(ib["live_from"])})' if ib['live_from'] else ''))
            if e['sources'] is not None:
                lines.append('- news sources: ' + (', '.join(e['sources']) or 'none'))
            if e['hard_keeps']:
                lines.append('- hard keeps: ' + '; '.join(e['hard_keeps']))
            if e['tickets']:
                lines.append('- open tickets naming it: ' + '; '.join(e['tickets']))
            lines.append('- allowed verdicts: ' + ', '.join(e['allowed']))
            if e.get('option_verbs', e['allowed']) != e['allowed']:
                lines.append('- a flag\'s options may carry: ' + ', '.join(e['option_verbs']))
    return '\n'.join(lines) + '\n'


# judgments to verdicts, under the guards

def archive_path(rc, path):
    return rc['archive'] + path


def convert(packet, rc, j, brain_repo, depth=0):
    """Turn one judgment into apply.py verdicts, or raise Invalid."""
    path = j.get('path')
    e = packet['pages'].get(path)
    if not e:
        raise Invalid(f'{path} is not in this run\'s packet')
    verdict = j.get('verdict')
    if verdict not in VERDICTS:
        raise Invalid(f'unknown verdict {verdict!r}')
    verbs = e.get('option_verbs', e['allowed']) if depth else e['allowed']
    if verdict not in verbs and not (depth and verdict == 'keep'):  # keep is always an option of a flag
        raise Invalid(f'{verdict} is not allowed for {path} ({e["group"]}): allowed {", ".join(verbs)}')
    if verdict != 'keep' and not j.get('reason'):
        raise Invalid('a verdict other than keep needs a reason')
    hard = ' '.join(e['hard_keeps'])
    if 'eval:' in hard and verdict in ('archive', 'delete', 'merge'):
        raise Invalid('hard keep: a retrieval-eval case names this page')
    if 'cited:' in hard and verdict in ('delete', 'merge'):
        raise Invalid('hard keep: live pages cite this page as a source')
    if 'named:' in hard and verdict in ('archive', 'delete', 'merge'):
        raise Invalid('hard keep: live pages name this page in a kept field')
    summary = j.get('summary') or f'{verdict} {path}'
    base = {'path': path, 'sha256': e['sha256'], 'summary': summary, 'reason': j.get('reason', '')}
    if verdict == 'keep':
        return []
    if verdict == 'update':
        v = {**base, 'op': 'UPDATE' if j.get('old') else 'ADD', 'new': j.get('new'), 'evidence': j.get('evidence') or []}
        v['old' if j.get('old') else 'after'] = j.get('old') or j.get('after')
        return [v]
    if verdict == 'delete':
        return [{**base, 'op': 'DELETE'}]
    if verdict == 'archive':
        if e['kind'] == 'tool' and (e['sources'] or e['fields'].get('stance') != 'retired'):
            raise Invalid('only a retired tool with no news sources moves to the archive')
        if e['kind'] in rc['follows_subjects']:
            subjects = j.get('_subjects') or []
            if not subjects or not all(s['archived'] for s in subjects):
                raise Invalid(f'a {e["kind"]} moves to the archive only when every linked subject is archived')
        return [{**base, 'op': 'MOVE', 'to': archive_path(rc, path), 'status': 'archived'}]
    if verdict == 'restore':
        live = path[len(rc['archive']):]
        if j.get('status') not in rc['live_statuses'].get(e['kind'], []):
            raise Invalid(f'restore needs a live status for a {e["kind"]}: {", ".join(rc["live_statuses"].get(e["kind"], []))}')
        return [{**base, 'op': 'MOVE', 'to': live, 'status': j['status']}]
    if verdict == 'file':
        to = j.get('to') or ''
        if not under(to, rc['file_targets']) or not to.endswith('.md') or (brain_repo / to).exists():
            raise Invalid(f'file target {to!r} must be a new page under {", ".join(rc["file_targets"])}')
        if not j.get('type') or not j.get('status'):
            raise Invalid('filing needs the page type and status of its new home')
        return [{**base, 'op': 'MOVE', 'to': to, 'type': j['type'], 'status': j['status']}]
    if verdict == 'merge':
        into = j.get('into') or ''
        if into == path or not (brain_repo / into).is_file():
            raise Invalid(f'merge target {into!r} is not another existing page')
        if into.split('/', 1)[0] != path.split('/', 1)[0]:
            raise Invalid('distinctness guard: a merge stays within one area')
        if not (j.get('same_subject') or '').strip():
            raise Invalid('distinctness guard: a merge must state why both pages are the same subject')
        target = packet['pages'].get(into)
        out = []
        if j.get('update'):
            u = j['update']
            sha = target['sha256'] if target else lib.sha256(brain_repo / into)
            v = {'path': into, 'sha256': sha, 'op': 'UPDATE' if u.get('old') else 'ADD', 'new': u.get('new'),
                 'evidence': u.get('evidence') or [], 'summary': f'take in what {path} held', 'reason': j['reason']}
            v['old' if u.get('old') else 'after'] = u.get('old') or u.get('after')
            out.append(v)
        out.append({**base, 'op': 'DELETE', 'into': into})
        return out
    if verdict == 'flag':
        if depth:
            raise Invalid('an option cannot be another flag')
        options = j.get('options') or []
        if not 1 <= len(options) <= rc['max_options']:
            raise Invalid(f'a flag needs 1 to {rc["max_options"]} options')
        built = []
        for o in options:
            inner = dict(o.get('judgment') or {}, path=path)
            inner.setdefault('reason', j['reason'])
            built.append((o, convert(packet, rc, inner, brain_repo, depth=1)))
        return [{'op': 'FLAG', '_options': built, 'path': path, 'finding': j.get('finding') or '', 'why': j.get('why') or '',
                 'recommended': j.get('recommended', 1), 'recommended_reason': j.get('recommended_reason', '')}]
    raise Invalid(f'unhandled verdict {verdict}')


def flag_verdict(cfg, meta, e, v):
    """A FLAG for apply.py: each option's verdicts are stored, and choosing it applies them."""
    options = []
    store = lib.state_dir(cfg) / 'relevance' / 'options'
    for n, (o, verdicts) in enumerate(v['_options'], 1):
        action = {'type': 'close'}
        if verdicts:
            path = store / f'{meta["run_id"]}-{re.sub(r"[^A-Za-z0-9]+", "-", e["path"])}-{n}.json'
            lib.atomic(path, verdicts)
            action = {'type': 'command', 'argv': ['scripts/relevance.py', 'option', str(path)]}
        options.append({'label': o.get('label') or f'option {n}', 'detail': o.get('detail', ''), 'action': action})
    return {'op': 'FLAG', 'fingerprint': f'relevance:{e["path"]}',
            'title': f'{cfg["brain"]} relevance: `{e["path"]}` needs a call',
            'finding': v['finding'] or f'`{e["path"]}`: ' + '; '.join(e['triggers']),
            'why': v['why'] or 'The evidence does not settle the verdict.',
            'evidence': [f'Triggers: {"; ".join(e["triggers"])}',
                         f'Last interaction evidence: {e["evidence"]["date"] or "none"}; inbound links from live pages: {e["inbound"]["live"]}']
            + ([f'Hard keeps: {"; ".join(e["hard_keeps"])}'] if e['hard_keeps'] else []),
            'options': options, 'recommended': v['recommended'], 'recommended_reason': v['recommended_reason']}


def read_judgments(path):
    text = Path(path).read_text().strip()
    if text.startswith('['):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def cmd_apply(cfg, rc, meta, source):
    rd = lib.run_dir(cfg, meta['run_id'])
    packet = lib.read_json(rd / 'packet.json')
    if not packet:
        raise Failed('no packet for this run: run prep first')
    outcomes = lib.read_json(rd / 'outcomes.json', {})
    repo = Path(cfg['published_repo'])
    judgments = read_judgments(source or rd / 'judgments.jsonl')
    archiving = {j.get('path') for j in judgments if j.get('verdict') == 'archive'}
    brain = None
    batch, seen = [], set()
    for j in judgments:
        path = j.get('path')
        if path in seen:
            outcomes[path] = {'verdict': j.get('verdict'), 'status': 'invalid', 'reason': 'one judgment per page per run'}
            continue
        seen.add(path)
        if outcomes.get(path, {}).get('status') in SETTLED:
            continue
        try:
            if j.get('verdict') == 'archive' and packet['pages'].get(path, {}).get('kind') in rc['follows_subjects']:
                brain = brain or Brain(cfg, rc)
                j = dict(j, _subjects=record_subjects(brain, path, archived=archiving))
            verdicts = convert(packet, rc, j, repo)
        except Invalid as error:
            outcomes[path] = {'verdict': j.get('verdict'), 'status': 'invalid', 'reason': str(error)}
            continue
        if not verdicts:
            outcomes[path] = {'verdict': 'keep', 'status': 'kept', 'reason': j.get('reason', '')}
            continue
        batch.append((j, verdicts))
    order = {'UPDATE': 0, 'ADD': 0, 'FLAG': 1, 'MOVE': 2, 'DELETE': 3}
    flat = []
    for j, verdicts in batch:
        for v in verdicts:
            if v['op'] == 'FLAG':
                v = flag_verdict(cfg, meta, packet['pages'][j['path']], v)
            flat.append((j['path'], v))
    flat.sort(key=lambda pv: order[pv[1]['op']])
    result = {'applied': [], 'rejected': [], 'flagged': []}
    if flat:
        vfile = rd / f'verdicts-{lib.stamp()}.json'
        lib.atomic(vfile, [v for _, v in flat])
        code, out, err = lib.run([cfg['python_bin'], APPLY, '--run', meta['run_id'], vfile], timeout=1800, check=False,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        if code:
            raise Failed(f'apply.py failed (exit {code}): {(err or out).strip()[-300:]}')
        result = json.loads(out)
    applied = {(a['op'], a['path']): a for a in result['applied']}
    rejected = {(r['verdict'].get('op'), r['verdict'].get('path')): r['reason'] for r in result['rejected']}
    for j, verdicts in batch:
        path = j['path']
        if verdicts[0]['op'] == 'FLAG':
            failed = rejected.get(('FLAG', path))
            outcomes[path] = {'verdict': 'flag', 'status': 'rejected' if failed else 'flagged', 'reason': failed or ''}
            continue
        reasons = [rejected[(v['op'], v['path'])] for v in verdicts if (v['op'], v['path']) in rejected]
        if reasons:
            held = all(r.startswith('tripwire') for r in reasons)
            outcomes[path] = {'verdict': j['verdict'], 'status': 'held' if held else 'rejected', 'reason': '; '.join(reasons)}
        else:
            done = [applied.get((v['op'], v['path'])) for v in verdicts]
            outcomes[path] = {'verdict': j['verdict'], 'status': 'applied', 'commits': [a['url'] for a in done if a]}
    lib.atomic(rd / 'outcomes.json', outcomes)
    remaining = [p for p in packet['pages'] if outcomes.get(p, {}).get('status') not in SETTLED]
    report = {
        'applied': [{'path': p, **o} for p, o in outcomes.items() if o['status'] == 'applied'],
        'flagged': [{'path': p, 'url': o.get('url')} for p, o in outcomes.items() if o['status'] == 'flagged'],
        'rejected': [{'path': p, 'reason': o['reason']} for p, o in outcomes.items() if o['status'] in ('rejected', 'held')],
        'invalid': [{'path': p, 'reason': o['reason']} for p, o in outcomes.items() if o['status'] == 'invalid'],
        'kept': sum(1 for o in outcomes.values() if o['status'] == 'kept'),
        'not_judged': [p for p in remaining if p not in outcomes],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_finish(cfg, rc, meta):
    import routine as rt
    rd = lib.run_dir(cfg, meta['run_id'])
    packet = lib.read_json(rd / 'packet.json')
    if not packet:
        rt.end(cfg, meta, 'failed', 'no work packet was built')
        return 1
    outcomes = lib.read_json(rd / 'outcomes.json', {})
    tally = collections.Counter()
    for path, e in packet['pages'].items():
        o = outcomes.get(path, {})
        if o.get('status') == 'applied':
            tally[o['verdict']] += 1
        elif o.get('status') in SETTLED:
            tally[o['status']] += 1
        else:
            tally['not judged'] += 1
            lib.journal(cfg, meta['run_id'], 'problem', text=f'`{path}` was not judged'
                        + (f': {o["reason"]}' if o.get('reason') else '') + '; the next run of its slice judges it again.')
    groups = collections.Counter(e['group'] for e in packet['pages'].values())
    slice_open = [p for p, e in packet['pages'].items() if e['group'] == 'slice' and outcomes.get(p, {}).get('status') not in SETTLED]
    verbs = [('kept', 'kept'), ('update', 'updated'), ('archive', 'archived'), ('delete', 'deleted'), ('merge', 'merged'),
             ('restore', 'restored'), ('file', 'filed'), ('flagged', 'flagged'), ('held', 'held by the tripwire'),
             ('rejected', 'rejected by the guards'),
             ('not judged', 'not judged')]
    done = ', '.join(f'{label} {tally[k]}' for k, label in verbs if tally[k])
    summary = (f'slice {slice_label(packet["slice"])}: {groups["slice"]} of {packet["slice_pages"]} pages up for review'
               + (f'; inbox {groups["inbox"]}' if groups['inbox'] else '') + (f'; research {groups["research"]}' if groups['research'] else '')
               + (f'; restore checks {groups["restore"]}' if groups['restore'] else '') + f'; drift sample {groups["drift"]}'
               + (f'. {done}.' if done else '.'))
    counts = {'pages in slice': packet['slice_pages'], 'pages judged': len(packet['pages']) - tally['not judged'], 'kept': tally['kept']}
    state = load(cfg)
    complete = not slice_open
    done = {'slice': packet['slice'], 'source': packet['source'], 'run_id': meta['run_id'], 'at': lib.iso(), 'complete': complete}
    if packet['source'] == 'rotation':
        state['last'] = done
    if packet['source'] == 'queue' and complete and state['queue'] and state['queue'][0] == packet['slice']:
        state['queue'].pop(0)
    state['history'] = (state.get('history', []) + [{**done, 'summary': summary}])[-30:]
    save(cfg, state)
    rt.end(cfg, meta, 'ok' if not tally['not judged'] else 'partial', summary, counts)
    print(json.dumps({'status': 'ok' if not tally['not judged'] else 'partial', 'summary': summary}, ensure_ascii=False))
    return 0


def cmd_prep(cfg, rc, meta, slice_name):
    state = load(cfg)
    slice_name, source = (slice_name, 'manual') if slice_name else next_slice(rc, state)
    packet = dict(build_packet(cfg, rc, meta, slice_name), source=source)
    rd = lib.run_dir(cfg, meta['run_id'])
    lib.atomic(rd / 'packet.json', packet)
    (rd / 'brief.md').write_text(brief(packet))
    groups = collections.Counter(e['group'] for e in packet['pages'].values())
    print(json.dumps({'slice': slice_name, 'pages_to_judge': len(packet['pages']), 'by_group': groups,
                      'brief': str(rd / 'brief.md'), 'judgments': str(rd / 'judgments.jsonl')}, indent=2))
    return 0


def cmd_option(cfg, path):
    """Apply the stored verdicts of the option the owner chose, without the tripwire; relays apply.py's result."""
    code, out, err = lib.run([cfg['python_bin'], APPLY, '--held', path], timeout=1800, check=False,
                             env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    if code:
        raise Failed(f'apply.py failed (exit {code}): {(err or out).strip()[-300:]}')
    print(out)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('prep')
    c.add_argument('--run')
    c.add_argument('--slice')
    c = sub.add_parser('apply')
    c.add_argument('--run')
    c.add_argument('judgments', nargs='?')
    c = sub.add_parser('finish')
    c.add_argument('--run')
    c = sub.add_parser('queue')
    c.add_argument('slices', nargs='+')
    sub.add_parser('status')
    c = sub.add_parser('option')
    c.add_argument('file')
    args = p.parse_args()
    cfg, rc = lib.config(), rconfig()
    if args.command == 'queue':
        unknown = [s for s in args.slices if s not in rc['slices'] and not page_slice(s)]
        if unknown:
            raise Failed(f'unknown slice(s) {", ".join(unknown)}; slices: {", ".join(rc["slices"])}')
        with lib.flock(str(state_path(cfg)) + '.lock', 30):
            state = load(cfg)
            state['queue'] += args.slices
            save(cfg, state)
        print(json.dumps(state, indent=2))
        return 0
    if args.command == 'status':
        state = load(cfg)
        print(json.dumps({**state, 'next': next_slice(rc, state)[0]}, indent=2))
        return 0
    if args.command == 'option':
        return cmd_option(cfg, args.file)
    meta = lib.current_run(cfg, args.run)
    if args.command == 'prep':
        return cmd_prep(cfg, rc, meta, args.slice)
    if args.command == 'apply':
        return cmd_apply(cfg, rc, meta, args.judgments)
    return cmd_finish(cfg, rc, meta)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
