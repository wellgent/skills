#!/usr/bin/env python3
"""The core workflow: keep the brain aligned with the shared core, and the main agent's crons with the routine manifest.

  core.py align --run <run_id>                    cross-check, bring core changes in, list what needs judgment
  core.py flag --run <run_id> <verdicts.json>     file a needs-attention issue for each judged finding

Needs-attention option actions (run by the reply loop from this skill directory):

  core.py revert <path>                take the core text for one file, with the brain's values
  core.py promote <path>               make the brain's text of one file the core text
  core.py add <path> <values json>     write a new core file with the given placeholder values
  core.py crons                        make the crons match the manifest

The brain is aligned when every core file matches the core at its head commit. A file that
matches an older core version is behind: the core change since that version is merged in with
the brain's values and committed. A file that matches no core version since the recorded base
commit has departed from the core and becomes a finding. The base commit is recorded in the
brain whenever the whole brain matches a new core head.
"""
import argparse
import bisect
import difflib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import types

sys.dont_write_bytecode = True  # routines write nothing into the published copy
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR.parent / 'brain-routines' / 'scripts'))
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402

ROUTINE = 'core-check'
DIFF_LINES = 120


def braced(name):
    """A placeholder marker, built so this file holds no literal one: core files are read as templates."""
    return '{' * 2 + name + '}' * 2


class Unfilled(Exception):
    """A core text needs a placeholder value the brain does not carry."""


def load_config():
    cfg = lib.config()
    cfg['core'] = lib.read_json(SKILL_DIR / 'config.json')
    return cfg


# the shared core: a clone of the core repository in the routine state directory

class Core:
    def __init__(self, cfg, fetch=True):
        c = cfg['core']
        self.root, self.branch = c['root'], c['branch']
        self.dir = Path(c.get('clone') or lib.state_dir(cfg) / 'core' / Path(c['repo']).stem)
        self.web = c['web']
        if not (self.dir / '.git').exists():
            self.dir.parent.mkdir(parents=True, exist_ok=True)
            lib.run(['git', 'clone', '--quiet', c['repo'], self.dir], timeout=300)
        elif fetch:
            self.git('fetch', '--quiet', 'origin', self.branch, timeout=180)
        self.head = self.git('rev-parse', f'origin/{self.branch}')
        self.cc = self.checker()

    def git(self, *args, timeout=120, check=True, input=None):
        return lib.run(['git', '-C', self.dir, *args], timeout=timeout, check=check, input=input)

    def checker(self):
        """The core's own cross-check rules (setup/setup-brain/core-check at the head commit)."""
        source = self.git('show', f'{self.head}:setup/setup-brain/core-check')
        module = types.ModuleType('core_check')
        module.__file__ = str(self.dir / 'setup' / 'setup-brain' / 'core-check')
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
        return module

    def path(self, rel):
        return f'{self.root}/{rel}'

    def show(self, sha, rel):
        code, out, _ = self.git('show', f'{sha}:{self.path(rel)}', check=False)
        return out if code == 0 else None

    def files(self, sha):
        if not sha:
            return []
        out = self.git('ls-tree', '-r', '--name-only', sha, '--', self.root + '/')
        rels = [p[len(self.root) + 1:] for p in out.splitlines() if p]
        return [r for r in rels if r not in self.cc.SKIP]

    def mode(self, sha, rel):
        out = self.git('ls-tree', sha, '--', self.path(rel))
        return out.split()[0] if out else '100644'

    def tree(self, sha):
        return self.git('rev-parse', f'{sha}:{self.root}') if sha else None

    def versions(self, rel, base=None, limit=40):
        """The file's core texts, newest first: the head, then each version back to the base commit (all history without one)."""
        span = [self.head] + ([f'^{base}'] if base else [])
        shas = self.git('rev-list', f'--max-count={limit}', *span, '--', self.path(rel)).split()
        if base:
            shas.append(base)
        seen, out = set(), []
        for sha in [self.head] + shas:
            text = self.show(sha, rel)
            if text is not None and text not in seen:
                seen.add(text)
                out.append((sha, text))
        return out

    def changed_at(self, rel):
        out = self.git('log', '-1', '--format=%ct', self.head, '--', self.path(rel))
        return int(out) if out else 0

    def link(self, sha, rel=None):
        return f'{self.web}/blob/{sha}/{self.path(rel)}' if rel else f'{self.web}/commit/{sha}'


# the brain: its maintenance clone

class Brain:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = Path(cfg['maintenance_repo'])

    def git(self, *args, **kw):
        return lib.clone_git(self.cfg, *args, **kw)

    def text(self, rel):
        path = self.dir / rel
        return path.read_text() if path.is_file() else None

    def write(self, rel, text, mode=None):
        path = self.dir / rel
        if text is None:
            if path.exists():
                self.git('rm', '--quiet', '--', rel)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if mode == '100755':
            path.chmod(0o755)
        self.git('add', '--', rel)

    def history(self, rel, limit=30):
        """The file's committed texts, newest first."""
        out = []
        for sha in self.git('log', f'--max-count={limit}', '--format=%H', '--', rel).split():
            code, text, _ = self.git('show', f'{sha}:{rel}', check=False)
            if code == 0:
                out.append((sha, text))
        return out

    def changed_at(self, rel):
        out = self.git('log', '-1', '--format=%ct', '--', rel)
        return int(out) if out else 0


# matching and rendering, by the core's own rules

def sectioned(cc, rel):
    return Path(rel).name in cc.SECTIONED


def matches(cc, rel, template, target):
    """Whether target matches the core text template, exactly as core-check decides."""
    if template is None or target is None:
        return False
    if not sectioned(cc, rel):
        return cc.match(cc.content_lines(template), cc.content_lines(target))[1] is None
    found = cc.sections(target)
    return all(h in found and cc.match(lines, found[h])[1] is None for h, lines in cc.sections(template).items())


def raw_sections(text):
    """[(heading or None, raw text)] in order, split where core-check splits AGENTS.md."""
    out, fenced = [[None, []]], False
    for line in text.splitlines(keepends=True):
        if line.startswith('```'):
            fenced = not fenced
        if not fenced and line.startswith('## '):
            out.append([line.rstrip(), []])
        out[-1][1].append(line)
    return [(h, ''.join(lines)) for h, lines in out if h or lines]


def compile_parts(cc, lines):
    """core-check's pattern, with each local block captured in order as local__<n>."""
    seen, parts, local = set(), [], 0
    for line in lines:
        block = cc.BLOCK.fullmatch(line.strip())
        if block:
            name = block.group(1)
            if name == 'local':
                local += 1
                parts.append(rf'(?P<local__{local}>(?:[^\n]*\n)*?)')
            elif name in seen:
                parts.append(f'(?P={name})')
            else:
                seen.add(name)
                parts.append(rf'(?P<{name}>(?:[^\n]*\n)*?)')
            continue
        out, pos = [], 0
        for m in cc.PLACEHOLDER.finditer(line):
            out.append(re.escape(line[pos:m.start()]))
            name = m.group(1)
            out.append(f'(?P={name})' if name in seen else rf'(?P<{name}>[^\n]*?)')
            seen.add(name)
            pos = m.end()
        out.append(re.escape(line[pos:]))
        parts.append(''.join(out) + r'\n')
    return parts


def values_of(cc, template, target):
    """Placeholder values when target matches template, else None. Block values keep the target's blank lines."""
    tl = cc.content_lines(template)
    lines = target.splitlines()
    idx = [i for i, line in enumerate(lines) if line.strip()]
    text = ''.join(lines[i].rstrip() + '\n' for i in idx)
    m = re.fullmatch(''.join(compile_parts(cc, tl)), text)
    if not m:
        return None
    starts, pos = [], 0
    for i in idx:
        starts.append(pos)
        pos += len(lines[i].rstrip()) + 1
    blocks = {b.group(1) for line in tl if (b := cc.BLOCK.fullmatch(line.strip()))}
    values = {}
    for name in m.re.groupindex:
        s, e = m.span(name)
        if name in blocks or name.startswith('local__'):
            if s == e:
                values[name] = ''
            else:
                first, last = bisect.bisect_right(starts, s) - 1, bisect.bisect_right(starts, e - 1) - 1
                values[name] = '\n'.join(lines[idx[first]:idx[last] + 1]) + '\n'
        else:
            values[name] = m.group(name)
    return values


def doc_values(cc, rel, template, target):
    """Values of a whole file; for AGENTS.md one dict per core section heading."""
    if not sectioned(cc, rel):
        return values_of(cc, template, target)
    found, out = dict(raw_sections(target)), {}
    for heading, raw in raw_sections(template):
        if heading is None:
            continue
        if heading not in found:
            return None
        got = values_of(cc, raw, found[heading])
        if got is None:
            return None
        out[heading] = got
    return out


def local_slots(template):
    return sum(1 for line in template.splitlines() if line.strip() == braced('local'))


def render(cc, template, values, locals_=False):
    """The template with values filled in; local blocks stay empty unless locals_ fills them in order."""
    out, local = [], 0
    for line in template.splitlines():
        block = cc.BLOCK.fullmatch(line.strip())
        if block:
            name = block.group(1)
            if name == 'local':
                local += 1
                value = values.get(f'local__{local}', '') if locals_ else ''
            elif name in values:
                value = values[name]
            else:
                raise Unfilled(name)
            if value:
                out.append(value.rstrip('\n'))
            continue

        def fill(m):
            if m.group(1) not in values:
                raise Unfilled(m.group(1))
            return values[m.group(1)]
        out.append(cc.PLACEHOLDER.sub(fill, line))
    return '\n'.join(out) + '\n'


def project(cc, rel, template, target, values, drop=(), locals_=False):
    """The brain file as the template would make it: for AGENTS.md, the target with its core sections rendered."""
    if not sectioned(cc, rel):
        return render(cc, template, values, locals_)
    sections = [(h, raw) for h, raw in raw_sections(template) if h]
    wanted = dict(sections)
    flag = (lambda h: locals_.get(h, False)) if isinstance(locals_, dict) else (lambda h: locals_)
    rendered = {h: render(cc, raw, {**values.get('*', {}), **values.get(h, {})}, flag(h)) for h, raw in sections}
    out, placed = [], set()
    for heading, raw in raw_sections(target or ''):
        if heading in wanted:
            out.append(rendered[heading])
            placed.add(heading)
        elif heading not in drop:
            out.append(raw)
    for i, (heading, _) in enumerate(sections):
        if heading in placed:
            continue
        before = [h for h, _ in sections[:i] if h in placed]
        at = len(out)
        if before:
            anchor = rendered[before[-1]]
            at = next(k for k, part in enumerate(out) if part is anchor) + 1
        out.insert(at, rendered[heading])
        placed.add(heading)
    return ''.join(part if part.endswith('\n') else part + '\n' for part in out)


def merge3(ours, base, theirs, favor=None):
    """git merge-file: (clean, text)."""
    with tempfile.TemporaryDirectory(prefix='brain-core-') as d:
        paths = []
        for name, text in (('ours', ours), ('base', base), ('theirs', theirs)):
            p = Path(d) / name
            p.write_text(text)
            paths.append(str(p))
        code, out, err = lib.run(['git', 'merge-file', '-p', '--quiet', *([f'--{favor}'] if favor else []), *paths], check=False)
    if code >= 128:
        raise Failed(f'git merge-file failed: {err.strip()[-200:]}')
    return code == 0, out


def diff(a, b, label_a, label_b):
    lines = list(difflib.unified_diff((a or '').splitlines(), (b or '').splitlines(), label_a, label_b, lineterm='', n=2))
    if len(lines) > DIFF_LINES:
        lines = lines[:DIFF_LINES] + [f'... {len(lines) - DIFF_LINES} more diff lines']
    return '\n'.join(lines)


# the alignment

class Aligner:
    def __init__(self, cfg, core, brain):
        self.cfg, self.core, self.brain, self.cc = cfg, core, brain, core.cc
        base = lib.read_json(brain.dir / cfg['core']['base_file'], {}) or {}
        self.base = base.get('commit')
        if self.base and self.core.git('cat-file', '-e', self.base + '^{commit}', check=False)[0]:
            self.base = None  # not in the core history: search it all
        self.shared = None
        self.run_id = None

    def settled(self, rel):
        window = self.cfg['core'].get('settle_minutes', 30) * 60
        latest = max(self.core.changed_at(rel), self.brain.changed_at(rel))
        return time.time() - latest >= window

    def shared_values(self):
        """Placeholder values every aligned file agrees on, for core files the brain lacks."""
        if self.shared is None:
            seen = {}
            for rel in self.core.files(self.core.head):
                text = self.brain.text(rel)
                if sectioned(self.cc, rel) or not matches(self.cc, rel, self.core.show(self.core.head, rel), text):
                    continue
                for name, value in (values_of(self.cc, self.core.show(self.core.head, rel), text) or {}).items():
                    if not name.startswith('local__'):
                        seen.setdefault(name, set()).add(value)
            self.shared = {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}
        return self.shared

    def behind(self, rel, text, versions):
        """The newest core version this brain text matches, with its values, or None."""
        for sha, core_text in versions:
            if matches(self.cc, rel, core_text, text):
                return sha, core_text, doc_values(self.cc, rel, core_text, text)
        return None

    def merge(self, rel, text, old, values, favor=None):
        """Bring the core change from old to head into the brain text; (clean, merged)."""
        head = self.core.show(self.core.head, rel)
        # The brain's local block lines go into both sides when the local slots line up, so a core
        # change next to them merges cleanly.
        if not sectioned(self.cc, rel):
            values = {**self.shared_values(), **values}
            same = local_slots(old) == local_slots(head)
            base, theirs = render(self.cc, old, values, same), render(self.cc, head, values, same)
        else:
            values = {**values, '*': self.shared_values()}
            old_s, head_s = dict(raw_sections(old)), dict(raw_sections(head))
            same = {h: local_slots(raw) == local_slots(old_s.get(h, '')) for h, raw in head_s.items() if h}
            dropped = set(old_s) - set(head_s)
            base = project(self.cc, rel, old, text, values, locals_=same)
            theirs = project(self.cc, rel, head, text, values, drop=dropped, locals_=same)
        clean, merged = merge3(text, base, theirs, favor)
        return clean and matches(self.cc, rel, head, merged), merged

    def restored(self, rel):
        """The brain file with the core text restored: its newest aligned version, brought to the core head."""
        versions = self.core.versions(rel)
        for _, text in self.brain.history(rel):
            hit = self.behind(rel, text, versions)
            if hit:
                ok, merged = self.merge(rel, text, hit[1], hit[2], favor='theirs')
                if ok:
                    return merged
        return None

    def align(self):
        """Classify every core file; return (changes, findings, settling, ok_count)."""
        head_files = self.core.files(self.core.head)
        base_files = set(self.core.files(self.base))
        changes, findings, settling, ok = [], [], [], 0
        for rel in sorted(set(head_files) | base_files):
            head = self.core.show(self.core.head, rel)
            text = self.brain.text(rel)
            if head is not None and matches(self.cc, rel, head, text):
                ok += 1
                continue
            if not self.settled(rel):
                settling.append(rel)
                continue
            if head is None:  # the core dropped the file
                if text is not None and self.behind(rel, text, self.core.versions(rel, self.base)):
                    changes.append({'path': rel, 'text': None, 'what': 'removed, as in the core'})
                elif text is not None:
                    lib.journal(self.cfg, self.run_id, 'note', text=f'`{rel}` left the core; the brain keeps its own copy.')
                continue
            if text is None:
                if rel in base_files:
                    findings.append(self.departure(rel, None))
                    continue
                try:
                    new = project(self.cc, rel, head, None, {'*': self.shared_values()} if sectioned(self.cc, rel) else self.shared_values())
                    changes.append({'path': rel, 'text': new, 'mode': self.core.mode(self.core.head, rel), 'what': 'added from the core'})
                except Unfilled as missing:
                    findings.append(self.unfilled(rel, str(missing)))
                continue
            hit = self.behind(rel, text, self.core.versions(rel, self.base)[1:])
            if not hit:
                findings.append(self.departure(rel, text))
                continue
            try:
                clean, merged = self.merge(rel, text, hit[1], hit[2])
            except Unfilled as missing:
                findings.append(self.unfilled(rel, str(missing)))
                continue
            if clean:
                changes.append({'path': rel, 'text': merged, 'what': f'core change since {hit[0][:7]} brought in'})
            else:
                findings.append(self.conflict(rel, text, hit[0]))
        return changes, findings, settling, ok

    # findings

    def finding(self, kind, rel, title, finding, why, evidence, options, recommended, question):
        return {'id': f'{kind}:{rel}', 'type': kind, 'path': rel, 'fingerprint': f'{ROUTINE}:file:{rel}',
                'title': f'{self.cfg["brain"]} core: {title}', 'finding': finding, 'why': why, 'evidence': evidence,
                'options': options, 'recommended': recommended, 'question': question}

    def departure(self, rel, text):
        restored = self.restored(rel)
        head = self.core.show(self.core.head, rel)
        link = self.core.link(self.core.head, rel)
        if text is None:
            title = f'`{rel}` is missing, the core still carries it'
            finding = f'The brain no longer has `{rel}`, which the shared core still carries ([core text]({link})).'
        else:
            title = f'`{rel}` departs from the shared core'
            finding = f'`{rel}` matches no version of its [core text]({link}) since the core commit the brain last synced to.'
        shown = diff(text, restored, f'brain/{rel}', f'core/{rel}') if restored else diff(head, text, f'core template/{rel}', f'brain/{rel}')
        options = []
        if restored:
            options.append({'label': 'Revert the brain to the core text', 'detail': 'restores the core lines with the brain\'s values (the diff above)',
                            'action': {'type': 'command', 'argv': ['scripts/core.py', 'revert', rel]}})
        if text is not None and restored:
            options.append({'label': 'Promote the brain\'s text to the core', 'detail': 'commits it to the core repository, from where every brain takes it',
                            'action': {'type': 'command', 'argv': ['scripts/core.py', 'promote', rel]}})
        options.append({'label': 'Settle it by hand', 'detail': 'for example a new placeholder in the core; closes this issue, and the next run files it again if the file still departs',
                        'action': {'type': 'close'}})
        return self.finding('departure', rel, title, finding,
                            'A brain change to a core file is either a core improvement or a local mistake, and only the owner decides which.',
                            [f'Core head: [{self.core.head[:7]}]({self.core.link(self.core.head)})', f'Diff:\n\n```diff\n{shown}\n```'],
                            options, 1, 'Is the brain\'s change an improvement every brain should carry (promote) or a slip to undo (revert)?')

    def conflict(self, rel, text, since):
        restored = self.restored(rel)
        link = self.core.link(self.core.head, rel)
        changed = diff(self.core.show(since, rel), self.core.show(self.core.head, rel), f'core@{since[:7]}/{rel}', f'core@{self.core.head[:7]}/{rel}')
        evidence = [f'Core change: [{since[:7]}..{self.core.head[:7]}]({self.core.web}/compare/{since[:12]}...{self.core.head[:12]})',
                    f'Core change to the template:\n\n```diff\n{changed}\n```']
        if restored:
            evidence.append(f'Taking the core text changes the brain file like this:\n\n```diff\n{diff(text, restored, "brain/" + rel, "core/" + rel)}\n```')
        options = []
        if restored:
            options.append({'label': 'Take the core text', 'detail': 'the brain lines that collide with the core change give way (the last diff)',
                            'action': {'type': 'command', 'argv': ['scripts/core.py', 'revert', rel]}})
        options.append({'label': 'Merge it by hand', 'detail': 'closes this issue; the next run files it again if the file still lags the core',
                        'action': {'type': 'close'}})
        return self.finding('conflict', rel, f'the core change to `{rel}` does not merge cleanly',
                            f'The [core text]({link}) of `{rel}` changed, and the change collides with brain-local lines.',
                            'The core change and the brain\'s own lines touch the same place, so a merge would drop one of them.',
                            evidence, options, 1, 'Do the colliding brain lines matter enough to merge by hand?')

    def unfilled(self, rel, name):
        link = self.core.link(self.core.head, rel)
        options = [{'label': 'Write it with the proposed values', 'detail': 'the values in the recommendation',
                    'action': {'type': 'command', 'argv': ['scripts/core.py', 'add', rel, '{}']}},
                   {'label': 'Write it by hand', 'detail': 'closes this issue; the next run files it again while the file is missing or unfilled',
                    'action': {'type': 'close'}}]
        return self.finding('unfilled', rel, f'`{rel}` needs a value for `{braced(name)}`',
                            f'The [core text]({link}) of `{rel}` uses `{braced(name)}`, which no file of the brain carries a value for.',
                            'A placeholder value is a brain fact the routine cannot derive from the core.',
                            [f'Core head: [{self.core.head[:7]}]({self.core.link(self.core.head)})',
                             f'Placeholder index: {self.core.web}/blob/{self.core.head}/{self.core.root}/README.md'],
                            options, 1, f'Propose the value of every placeholder `{rel}` needs, read from the brain, in "values".')


# the crons

def cron_drift(cfg):
    """The manifest-to-cron drift list of routine.py sync --check."""
    script = SKILL_DIR.parent / 'brain-routines' / 'scripts' / 'routine.py'
    code, out, err = lib.run([cfg['python_bin'], script, 'sync', '--check'], timeout=300, check=False)
    try:
        report = json.loads(out)
    except json.JSONDecodeError:
        raise Failed(f'routine.py sync --check failed (exit {code}): {(err or out).strip()[-300:]}')
    return report.get('drift', [])


def drift_finding(cfg, drift):
    lines = [f'`{d["routine"]}`: {d["drift"]}' for d in drift]
    return {'id': 'crons', 'type': 'drift', 'path': cfg['manifest'], 'fingerprint': f'{ROUTINE}:crons',
            'title': f'{cfg["brain"]} core: the crons drift from the routine manifest',
            'finding': f'{len(drift)} routine(s) differ between `{cfg["manifest"]}` and the {cfg["openclaw"]["agent"]} agent\'s crons.',
            'why': 'A cron edited outside the manifest may be a deliberate runtime change, so the routine does not overwrite it unasked.',
            'evidence': lines,
            'options': [{'label': 'Sync the crons to the manifest', 'detail': 'runs `routine.py sync`',
                         'action': {'type': 'command', 'argv': ['scripts/core.py', 'crons']}},
                        {'label': 'Fix the manifest by hand', 'detail': 'closes this issue; the next run files it again while the drift lasts',
                         'action': {'type': 'close'}}],
            'recommended': 1, 'question': 'Is any drift a deliberate runtime change the manifest should take instead?'}


# commands

def commit_push(cfg, brain, subject, body):
    brain.git('commit', '--quiet', '-m', subject, '-m', body)
    lib.push_clone(cfg)
    return brain.git('rev-parse', 'HEAD')


def cmd_align(cfg, run_id):
    meta = lib.current_run(cfg, run_id)
    lib.reset_clone(cfg)
    core, brain = Core(cfg), Brain(cfg)
    aligner = Aligner(cfg, core, brain)
    aligner.run_id = meta['run_id']
    changes, findings, settling, ok = aligner.align()
    applied = None
    for c in changes:
        brain.write(c['path'], c['text'], c.get('mode'))
    if changes:
        listing = '\n'.join(f'- {c["path"]}: {c["what"]}' for c in changes)
        if not findings and not settling:
            write_base(cfg, brain, core)
        sha = commit_push(cfg, brain, f'setup: the shared core at {core.head[:7]} flows into {len(changes)} file(s)',
                          f'Routine: {ROUTINE} ({meta["run_id"]})\nCore: {core.link(core.head)}\n\n{listing}')
        applied = sha
        lib.journal(cfg, meta['run_id'], 'change', text=f'Core {core.head[:7]} brought into ' + ', '.join(f'`{c["path"]}`' for c in changes),
                    url=lib.commit_url(cfg, sha), revert=f'git revert {sha[:12]}')
    elif not findings and not settling and core.tree(aligner.base) != core.tree(core.head):
        write_base(cfg, brain, core)
        commit_push(cfg, brain, f'setup: the brain matches the shared core at {core.head[:7]}',
                    f'Routine: {ROUTINE} ({meta["run_id"]})\nCore: {core.link(core.head)}')
    manifest_age = time.time() - int(lib.run(['git', '-C', cfg['published_repo'], 'log', '-1', '--format=%ct', '--', cfg['manifest']]) or 0)
    drift = cron_drift(cfg)
    if drift and manifest_age < cfg['core'].get('settle_minutes', 30) * 60:
        settling.append(cfg['manifest'])
    elif drift:
        findings.append(drift_finding(cfg, drift))
    if settling:
        lib.journal(cfg, meta['run_id'], 'note', text='Changed in the last '
                    f'{cfg["core"].get("settle_minutes", 30)} minutes, checked next run: ' + ', '.join(f'`{s}`' for s in settling) + '.')
    close_resolved(cfg, meta, {f['fingerprint'] for f in findings}, settling)
    lib.atomic(lib.run_dir(cfg, meta['run_id']) / 'core-packet.json', {'core': core.head, 'findings': findings})
    parts = [f'{ok} of {len(core.files(core.head))} core files match the core at {core.head[:7]}']
    if changes:
        parts.append(f'{len(changes)} brought in from the core')
    if findings:
        parts.append(f'{len(findings)} need attention')
    parts.append('crons match the manifest' if not drift else f'{len(drift)} cron drift(s)')
    summary = '; '.join(parts)
    routine = SKILL_DIR.parent / 'brain-routines' / 'scripts' / 'routine.py'
    counts = {'core files ok': ok}
    end = f'{cfg["python_bin"]} {routine} end {meta["run_id"]} --status ok --summary {json.dumps(summary)} --counts {json.dumps(json.dumps(counts))}'
    print(json.dumps({
        'differs': bool(findings),
        'summary': summary,
        'applied': lib.commit_url(cfg, applied) if applied else None,
        'findings': [{k: f[k] for k in ('id', 'type', 'path', 'title', 'question', 'options', 'recommended', 'evidence')} for f in findings],
        'next': (f'Judge each finding, write [{{"id", "recommended", "reason"}}] to {lib.run_dir(cfg, meta["run_id"])}/verdicts.json, '
                 f'run `{cfg["python_bin"]} {Path(__file__).resolve()} flag --run {meta["run_id"]} {lib.run_dir(cfg, meta["run_id"])}/verdicts.json`, then end.'
                 if findings else 'Nothing needs judgment: end the run.'),
        'end': end,
    }, ensure_ascii=False, indent=2))
    return 0


def write_base(cfg, brain, core):
    rel = cfg['core']['base_file']
    record = {'repo': cfg['core']['repo'], 'root': core.root, 'commit': core.head}
    brain.write(rel, json.dumps(record, indent=2) + '\n')


def close_resolved(cfg, meta, live, settling):
    """Close this routine's open file and cron issues whose finding is gone."""
    for issue in lib.open_attention(cfg, 'core'):
        fingerprint = lib._parse_comment('fingerprint', issue['body'])
        if not isinstance(fingerprint, str) or not fingerprint.startswith(f'{ROUTINE}:') or fingerprint in live:
            continue
        rel = fingerprint.split(':file:', 1)[1] if ':file:' in fingerprint else cfg['manifest']
        if rel in settling:
            continue
        lib.gh(cfg, 'issue', 'comment', str(issue['number']), '--repo', cfg['github_repo'], '--body-file', '-',
               input=f'The finding is gone: run `{meta["run_id"]}` found `{rel}` aligned. Closing.\n\n{lib.MARKER}')
        lib.gh(cfg, 'issue', 'close', str(issue['number']), '--repo', cfg['github_repo'], '--reason', 'completed')
        lib.journal(cfg, meta['run_id'], 'note', text=f'Closed <{issue["url"]}>: its finding is gone.')


def cmd_flag(cfg, run_id, verdicts_path):
    meta = lib.current_run(cfg, run_id)
    packet = lib.read_json(lib.run_dir(cfg, meta['run_id']) / 'core-packet.json')
    if not packet:
        raise Failed('no core packet in this run: run align first')
    raw = json.loads(Path(verdicts_path).read_text())
    verdicts = {v['id']: v for v in (raw.get('verdicts', []) if isinstance(raw, dict) else raw)}
    filed = []
    for f in packet['findings']:
        v = verdicts.get(f['id'], {})
        options = json.loads(json.dumps(f['options']))
        recommended = v.get('recommended', f['recommended'])
        if not isinstance(recommended, int) or not 1 <= recommended <= len(options):
            recommended = f['recommended']
        if f['type'] == 'unfilled':
            values = v.get('values') or {}
            if values:
                options[0]['action']['argv'][-1] = json.dumps(values, ensure_ascii=False)
                options[0]['detail'] = 'with ' + ', '.join(f'`{braced(k)}` = `{val}`' for k, val in values.items())
            else:
                options = options[1:]
                recommended = 1
        url, _ = lib.file_attention(cfg, meta, f['fingerprint'], f['title'], f['finding'], f['why'], f['evidence'],
                                    options, recommended, v.get('reason', ''))
        filed.append(url)
    print(json.dumps({'filed': filed}, indent=2))
    return 0


def action_result(cfg, meta, brain, rel, subject, what):
    sha = commit_push(cfg, brain, subject, f'Routine: {ROUTINE} ({meta["run_id"]})\nIssue: {os.environ.get("ATTENTION_ISSUE", "")}')
    url = lib.commit_url(cfg, sha)
    lib.journal(cfg, meta['run_id'], 'change', text=f'{what} `{rel}`', url=url, revert=f'git revert {sha[:12]}')
    print(json.dumps({'note': f'{what} `{rel}`.', 'commits': [url]}))


def cmd_revert(cfg, rel):
    meta = lib.current_run(cfg)
    core, brain = Core(cfg), Brain(cfg)
    aligner = Aligner(cfg, core, brain)
    restored = aligner.restored(rel)
    if restored is None:
        raise Failed(f'no aligned version of {rel} to restore the core text from')
    brain.write(rel, restored, core.mode(core.head, rel) if brain.text(rel) is None else None)
    action_result(cfg, meta, brain, rel, f'setup: {rel} takes the shared core text at {core.head[:7]}', 'Restored the core text of')
    return 0


def cmd_add(cfg, rel, values):
    meta = lib.current_run(cfg)
    core, brain = Core(cfg), Brain(cfg)
    aligner = Aligner(cfg, core, brain)
    head = core.show(core.head, rel)
    if head is None:
        raise Failed(f'{rel} is not a core file')
    values = {**aligner.shared_values(), **json.loads(values)}
    try:
        text = project(core.cc, rel, head, brain.text(rel), {'*': values} if sectioned(core.cc, rel) else values)
    except Unfilled as missing:
        raise Failed(f'{rel} still needs a value for {braced(str(missing))}')
    brain.write(rel, text, core.mode(core.head, rel))
    action_result(cfg, meta, brain, rel, f'setup: {rel} comes from the shared core at {core.head[:7]}', 'Added from the core')
    return 0


def lift(cc, template, values, text):
    """The template with the brain's departing lines in place of the core lines they replace.

    The template is rendered with the aligned values, tracking which template line made each
    output line; the brain text is diffed against that rendering, and each changed run of lines
    goes back into the template with inline values turned back into placeholders. Changes at a
    local block stay brain-local; a change inside any other block cannot be lifted.
    """
    tlines = template.splitlines()
    out, owner, kinds, local_spans, local = [], [], [], [], 0
    for ti, line in enumerate(tlines):
        block = cc.BLOCK.fullmatch(line.strip())
        if block:
            name = block.group(1)
            if name == 'local':
                local += 1
                value, kind = values.get(f'local__{local}', ''), 'local'
            else:
                value, kind = values[name], 'block'
            start = len(out)
            for vl in value.splitlines():
                out.append(vl)
                owner.append(ti)
            if kind == 'local':
                local_spans.append((start, len(out)))
            kinds.append(kind)
            continue
        kinds.append('text')
        out.append(cc.PLACEHOLDER.sub(lambda m: values[m.group(1)], line))
        owner.append(ti)
    inline = sorted(((k, v) for k, v in values.items() if not k.startswith('local__') and v and '\n' not in v and len(v) >= 4),
                    key=lambda kv: -len(kv[1]))

    def placeholders(line):
        for name, value in inline:
            line = line.replace(value, braced(name))
        return line

    covered, before = set(), {}
    sm = difflib.SequenceMatcher(None, out, text.splitlines(), autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        owned = {owner[i] for i in range(i1, i2)}
        if owned and all(kinds[t] == 'local' for t in owned):
            continue
        if not owned and any(s <= i1 <= e for s, e in local_spans):
            continue
        if any(kinds[t] != 'text' for t in owned):
            raise Failed('the brain change reaches into a placeholder block')
        covered |= owned
        anchor = min(owned) if owned else (owner[i1] if i1 < len(out) else len(tlines))
        before.setdefault(anchor, []).extend(placeholders(line) for line in text.splitlines()[j1:j2])
    result = []
    for ti, line in enumerate(tlines):
        result += before.get(ti, [])
        if ti not in covered:
            result.append(line)
    result += before.get(len(tlines), [])
    return '\n'.join(result) + '\n'


def promoted(aligner, rel):
    """The core template carrying the brain's text of rel."""
    core, cc = aligner.core, aligner.cc
    template, text = core.show(core.head, rel), aligner.brain.text(rel)
    restored = aligner.restored(rel)
    if template is None or text is None or restored is None:
        raise Failed(f'{rel} has no aligned version to promote from')
    values = doc_values(cc, rel, template, restored)
    if values is None:
        raise Failed(f'the restored text of {rel} does not match the core')
    if not sectioned(cc, rel):
        new = lift(cc, template, values, text)
    else:
        found = dict(raw_sections(text))
        parts = []
        for heading, raw in raw_sections(template):
            if heading is None:
                parts.append(raw)
            elif heading in found:
                parts.append(lift(cc, raw, values[heading], found[heading]))
        new = ''.join(parts)
    if not matches(cc, rel, new, text):
        raise Failed(f'the promoted core text of {rel} would not match the brain; settle it by hand')
    return new


def cmd_promote(cfg, rel):
    meta = lib.current_run(cfg)
    core, brain = Core(cfg), Brain(cfg)
    aligner = Aligner(cfg, core, brain)
    new = promoted(aligner, rel)
    name = brain.git('config', 'user.name')
    email = brain.git('config', 'user.email')
    issue = os.environ.get('ATTENTION_ISSUE', '')
    ref = f'{cfg["github_repo"]}#{issue.rsplit("/", 1)[-1]}' if issue else cfg['github_repo']
    for attempt in range(3):
        core.git('checkout', '--quiet', '--force', '-B', core.branch, f'origin/{core.branch}')
        core.git('clean', '-ffdxq')
        path = core.dir / core.path(rel)
        path.write_text(new)
        core.git('add', '--', core.path(rel))
        core.git('-c', f'user.name={name}', '-c', f'user.email={email}', 'commit', '--quiet', '-m',
                 f'setup: the {cfg["brain"]} text of {rel} becomes the brain core ({ref})',
                 '-m', f'Routine: {ROUTINE} ({meta["run_id"]})\nIssue: {issue}')
        code, _, err = core.git('push', '--quiet', 'origin', f'HEAD:{core.branch}', check=False, timeout=120)
        if code == 0:
            break
        core.git('fetch', '--quiet', 'origin', core.branch)
        time.sleep(2 + attempt * 3)
    else:
        raise Failed(f'push to the core failed: {err.strip()[-200:]}')
    sha = core.git('rev-parse', 'HEAD')
    url = core.link(sha)
    lib.journal(cfg, meta['run_id'], 'change', text=f'Promoted the brain text of `{rel}` to the shared core', url=url,
                revert=f'git -C <core clone> revert {sha[:12]}')
    print(json.dumps({'note': f'Promoted the brain text of `{rel}` to the shared core.', 'commits': [url]}))
    return 0


def cmd_crons(cfg):
    meta = lib.current_run(cfg)
    script = SKILL_DIR.parent / 'brain-routines' / 'scripts' / 'routine.py'
    out = lib.run([cfg['python_bin'], script, 'sync'], timeout=600)
    changed = json.loads(out).get('changed', [])
    note = 'Synced the crons to the manifest: ' + ('; '.join(f'{c["routine"]} ({c["drift"]})' for c in changed) or 'nothing left to change') + '.'
    lib.journal(cfg, meta['run_id'], 'note', text=note)
    print(json.dumps({'note': note}))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('align', help='cross-check the brain and the crons, bring core changes in')
    c.add_argument('--run', required=True)
    c = sub.add_parser('flag', help='file needs-attention issues for the judged findings')
    c.add_argument('--run', required=True)
    c.add_argument('verdicts')
    c = sub.add_parser('revert', help='option action: take the core text for one file')
    c.add_argument('path')
    c = sub.add_parser('promote', help='option action: make the brain text of one file the core text')
    c.add_argument('path')
    c = sub.add_parser('add', help='option action: write a new core file with placeholder values')
    c.add_argument('path')
    c.add_argument('values')
    sub.add_parser('crons', help='option action: sync the crons to the manifest')
    args = p.parse_args()
    cfg = load_config()
    if args.command == 'align':
        return cmd_align(cfg, args.run)
    if args.command == 'flag':
        return cmd_flag(cfg, args.run, args.verdicts)
    if args.command == 'revert':
        return cmd_revert(cfg, args.path)
    if args.command == 'promote':
        return cmd_promote(cfg, args.path)
    if args.command == 'add':
        return cmd_add(cfg, args.path, args.values)
    return cmd_crons(cfg)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
