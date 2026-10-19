#!/usr/bin/env python3
"""Apply a routine's structured verdicts to the brain from the maintenance clone, under code guards.

Input is a JSON list of verdicts (or {"verdicts": [...]}) on stdin or in a file. Each verdict:

  {"op": "NOOP"}
  {"op": "UPDATE", "path", "sha256", "old", "new", "evidence", "summary", "reason"}
  {"op": "ADD", "path", "sha256", "after", "new", "evidence", "summary", "reason"}
  {"op": "DELETE", "path", "sha256", "old", "evidence", "summary", "reason"}   a span
  {"op": "DELETE", "path", "sha256", "summary", "reason"}                       the whole page
  {"op": "MOVE", "path", "sha256", "to", "status", "summary", "reason"}         archive or restore
  {"op": "FLAG", "fingerprint", "title", "finding", "why", "evidence", "options", "recommended", "recommended_reason"}

evidence is [{"path": "<brain path>", "quote": "<exact text in that file>"}].
Prints {"applied", "rejected", "flagged", "noop"}; every applied verdict is one pushed commit.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True  # routines write nothing into the published copy
import routinelib as lib  # noqa: E402
from routinelib import Failed

NUMBER = re.compile(r'\d+(?:[.,:/-]\d+)*')
LINK = re.compile(r'(?<!!)\[([^\]\n]*)\]\(([^)\s]+)((?:\s+"[^"]*")?)\)')


class Rejected(Exception):
    """A guard refused the verdict; nothing was written."""


def norm(text):
    return ' '.join((text or '').split())


def link_target(src, target):
    """The brain path a relative markdown link in src points at, or None for external links."""
    if '://' in target or target.startswith(('#', 'mailto:')):
        return None, ''
    path, _, anchor = target.partition('#')
    resolved = os.path.normpath(path[1:] if path.startswith('/') else os.path.join(os.path.dirname(src), path))
    return resolved, ('#' + anchor if anchor else '')


def relpath(target, src):
    """The relative link from page src to brain path target."""
    return os.path.relpath(target, os.path.dirname(src) or '.')


def safe_path(rel):
    path = os.path.normpath(rel or '')
    if not path.endswith('.md') or path.startswith(('..', '/', '.git/')):
        raise Rejected(f'{rel!r} is not a brain page path')
    return path


def rewrite_links(text, src, fn):
    """Rewrite each link in a file: fn(resolved) returns a new target, '' to unlink, or None to keep."""
    def sub(m):
        resolved, anchor = link_target(src, m.group(2))
        if resolved is None:
            return m.group(0)
        new = fn(resolved)
        if new is None:
            return m.group(0)
        if new == '':
            return m.group(1)
        return f'[{m.group(1)}]({new}{anchor}{m.group(3)})'
    return LINK.sub(sub, text)


def set_status(text, status):
    if not text.startswith('---\n'):
        raise Rejected('page has no frontmatter to carry its status')
    close = text.find('\n---', 4)
    if close < 0:
        raise Rejected('page frontmatter is not closed')
    head, rest = text[:close], text[close:]
    if re.search(r'^status:.*$', head, re.M):
        head = re.sub(r'^status:.*$', f'status: {status}', head, count=1, flags=re.M)
    else:
        head += f'\nstatus: {status}'
    return head + rest


class Applier:
    def __init__(self, cfg, meta, tripwire=True):
        self.cfg, self.meta, self.tripwire = cfg, meta, tripwire
        self.repo = Path(cfg['maintenance_repo'])
        self.run_dir = lib.run_dir(cfg, meta['run_id'])
        self.result = {'applied': [], 'rejected': [], 'flagged': [], 'noop': 0}

    def git(self, *args, **kw):
        return lib.clone_git(self.cfg, *args, **kw)

    def read(self, rel):
        path = self.repo / rel
        if not path.is_file():
            raise Rejected(f'{rel} does not exist')
        return path.read_text()

    def pages(self):
        return [p for p in self.git('ls-files', '--', '*.md').splitlines() if p]

    # guards

    def check_hash(self, v):
        if v.get('sha256') != lib.sha256(self.repo / v['path']):
            raise Rejected('page changed since the work packet was built (content hash differs)')

    def check_evidence(self, v, required=True):
        evidence = v.get('evidence') or []
        if required and not evidence:
            raise Rejected('no cited evidence')
        quotes = []
        for e in evidence:
            if not isinstance(e, dict) or not e.get('path') or not e.get('quote'):
                raise Rejected('evidence must be {"path", "quote"}')
            if norm(e['quote']) not in norm(self.read(e['path'])):
                raise Rejected(f'cited quote not found in {e["path"]}')
            quotes.append(norm(e['quote']))
        known = set(NUMBER.findall(v.get('old') or '')) | set(NUMBER.findall(' '.join(quotes)))
        missing = [n for n in NUMBER.findall(v.get('new') or '') if n not in known]
        if missing:
            raise Rejected('numbers or dates not in the cited source: ' + ', '.join(sorted(set(missing))))

    def span(self, text, s, what):
        if not s:
            raise Rejected(f'no {what} span')
        count = text.count(s)
        if count != 1:
            raise Rejected(f'{what} span found {count} times, needs exactly one')

    # operations

    def write(self, rel, text):
        (self.repo / rel).write_text(text)

    def op_update(self, v):
        text = self.read(v['path'])
        self.span(text, v.get('old'), 'old')
        self.check_evidence(v)
        self.write(v['path'], text.replace(v['old'], v['new'], 1))
        return {}

    def op_add(self, v):
        text = self.read(v['path'])
        self.span(text, v.get('after'), 'after')
        if not v.get('new'):
            raise Rejected('nothing to add')
        self.check_evidence(v)
        self.write(v['path'], text.replace(v['after'], v['after'] + v['new'], 1))
        return {}

    def op_delete(self, v):
        if v.get('old'):
            text = self.read(v['path'])
            self.span(text, v['old'], 'old')
            self.check_evidence(v)
            self.write(v['path'], text.replace(v['old'], '', 1))
            return {}
        if not v.get('reason'):
            raise Rejected('a page deletion needs a reason')
        links = self.repair(v['path'], None)
        self.git('rm', '--quiet', '--', v['path'])
        return {'revert': True, 'links': links}

    def op_move(self, v):
        to = safe_path(v.get('to'))
        if (self.repo / to).exists():
            raise Rejected(f'{to} already exists')
        if not v.get('reason'):
            raise Rejected('a move needs a reason')
        old = v['path']
        text = self.read(old)
        if v.get('status'):
            text = set_status(text, v['status'])
        if os.path.dirname(old) != os.path.dirname(to):
            # the moved page's own relative links now start from its new directory
            text = rewrite_links(text, old, lambda r: relpath(to if r == old else r, to))
        links = self.repair(old, to)
        (self.repo / to).parent.mkdir(parents=True, exist_ok=True)
        self.git('mv', old, to)
        self.write(to, text)
        return {'revert': True, 'links': links}

    def repair(self, old, new):
        """Point every inbound link at the new path, or unlink it when the page goes away; return the pages fixed."""
        touched = 0
        for rel in self.pages():
            if rel == old:
                continue
            text = (self.repo / rel).read_text()
            fixed = rewrite_links(text, rel, lambda r: None if r != old else ('' if new is None else relpath(new, rel)))
            if fixed != text:
                self.write(rel, fixed)
                touched += 1
        return touched

    def commit(self, v):
        self.git('add', '-A')  # the clone holds only this verdict's changes
        scope = v['path'].split('/', 1)[0] if '/' in v['path'] else 'brain'
        body = [f'Routine: {self.meta["routine"]} ({self.meta["run_id"]})', f'Op: {v["op"]} {v["path"]}']
        if v.get('reason'):
            body.append(f'Reason: {v["reason"]}')
        body += [f'Evidence: {e["path"]}: "{norm(e["quote"])[:200]}"' for e in v.get('evidence') or []]
        self.git('commit', '--quiet', '-m', f'{scope}: {v["summary"]}', '-m', '\n'.join(body))
        return self.git('rev-parse', 'HEAD')

    # tripwire

    def destructive(self, v):
        return (v.get('op') == 'DELETE' and not v.get('old')) or \
               (v.get('op') == 'MOVE' and (v.get('to') or '').startswith('archive/'))

    def trip(self, verdicts):
        """Hold every destructive verdict of an area whose run total passes the tripwire share."""
        if not self.tripwire:
            return verdicts
        tally_path = self.run_dir / 'tripwire.json'
        tally = lib.read_json(tally_path, {'counts': {}, 'tripped': []})
        by_area = {}
        for v in verdicts:
            if self.destructive(v):
                by_area.setdefault(v['path'].split('/', 1)[0], []).append(v)
        share = self.cfg['tripwire_share']
        held = []
        for area, items in by_area.items():
            size = sum(1 for p in self.pages() if p.startswith(area + '/'))
            total = tally['counts'].get(area, 0) + len(items)
            if area in tally['tripped'] or total > share * size:
                held += items
                if area not in tally['tripped']:
                    tally['tripped'].append(area)
                    self.hold(area, items, total, size)
            else:
                tally['counts'][area] = total
        lib.atomic(tally_path, tally)
        for v in held:
            self.result['rejected'].append({'verdict': v, 'reason': 'tripwire: held for the owner'})
        return [v for v in verdicts if not any(v is h for h in held)]

    def hold(self, area, items, total, size):
        path = lib.state_dir(self.cfg) / 'held' / f'{self.meta["run_id"]}-{area}.json'
        lib.atomic(path, items)
        url, _ = lib.file_attention(
            self.cfg, self.meta, f'tripwire:{self.meta["routine"]}:{area}',
            f'{self.cfg["brain"]} {self.meta["routine"]} would remove {total} of {size} pages in {area}/',
            f'The run would delete or archive {total} of the {size} pages in `{area}/`, over the {int(self.cfg["tripwire_share"] * 100)}% tripwire.',
            'A share that large points at a malfunction more often than at real staleness, so nothing in this area was applied.',
            [f'`{v["op"]} {v["path"]}`' + (f' to `{v["to"]}`' if v.get('to') else '') + f': {v.get("reason", "")}' for v in items[:30]]
            + ([f'... {len(items) - 30} more'] if len(items) > 30 else []),
            [{'label': 'Apply the held verdicts', 'detail': 'the next run applies them, each still checked against its content hash',
              'action': {'type': 'command', 'argv': ['scripts/apply.py', '--held', str(path)]}},
             {'label': 'Discard them', 'detail': 'nothing changes; later runs judge these pages again',
              'action': {'type': 'close'}}],
            2, 'a share this large usually means the judge or its packet went wrong')
        self.result['flagged'].append(url)

    # the batch

    def apply(self, verdicts):
        wiped = lib.reset_clone(self.cfg)
        if wiped:
            lib.journal(self.cfg, self.meta['run_id'], 'note', text='Wiped unpushed leftovers before applying: ' + ', '.join(wiped) + '.')
        commits = []
        for v in self.trip(verdicts):
            op = v.get('op')
            try:
                if op == 'NOOP':
                    self.result['noop'] += 1
                    continue
                if op == 'FLAG':
                    url, _ = lib.file_attention(self.cfg, self.meta, v['fingerprint'], v['title'], v['finding'], v['why'],
                                                v.get('evidence', []), v['options'], v.get('recommended', 1), v.get('recommended_reason', ''))
                    self.result['flagged'].append(url)
                    continue
                handler = {'UPDATE': self.op_update, 'ADD': self.op_add, 'DELETE': self.op_delete, 'MOVE': self.op_move}.get(op)
                if not handler:
                    raise Rejected(f'unknown op {op}')
                if not v.get('summary'):
                    raise Rejected('a write needs a summary for its commit subject')
                v['path'] = safe_path(v.get('path'))
                self.read(v['path'])
                self.check_hash(v)
                info = handler(v)
                self.commit(v)
                commits.append((v, info))
            except (Rejected, KeyError, Failed) as error:
                self.git('reset', '--quiet', '--hard', 'HEAD')
                self.git('clean', '-ffdq')
                self.result['rejected'].append({'verdict': v, 'reason': f'missing field {error}' if isinstance(error, KeyError) else str(error)})
        if commits:
            try:
                lib.push_clone(self.cfg)
            except Failed as error:
                lib.reset_clone(self.cfg)
                for v, _ in commits:
                    self.result['rejected'].append({'verdict': v, 'reason': f'not pushed: {error}'})
                lib.journal(self.cfg, self.meta['run_id'], 'problem', text=f'{len(commits)} change(s) not pushed: {error}')
                return self.result
            # the rebase before the push rewrote the commits; find each by its subject, oldest first
            log = self.git('log', '--format=%H %s', f'-{len(commits)}').splitlines()[::-1]
            for (v, info), line in zip(commits, log):
                sha = line.split(' ', 1)[0]
                url = lib.commit_url(self.cfg, sha)
                entry = {'op': v['op'], 'path': v['path'], 'commit': sha, 'url': url}
                if info.get('revert'):
                    entry['revert'] = f'git revert {sha[:12]}'
                text = f'{v["op"]} `{v["path"]}`' + (f' to `{v["to"]}`' if v.get('to') else '') + f': {v["summary"]}'
                if info.get('links'):
                    text += f' ({info["links"]} linking page(s) repaired)'
                self.result['applied'].append(entry)
                lib.journal(self.cfg, self.meta['run_id'], 'change', text=text, url=url, revert=entry.get('revert'))
        if self.result['rejected']:
            reasons = {}
            for r in self.result['rejected']:
                key = r['reason'].split(':', 1)[0]
                reasons[key] = reasons.get(key, 0) + 1
            lib.journal(self.cfg, self.meta['run_id'], 'note', text=f'{len(self.result["rejected"])} verdict(s) rejected: '
                        + '; '.join(f'{k} ({n})' for k, n in reasons.items()) + '.')
        return self.result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('verdicts', nargs='?', help='verdict JSON file (default: stdin)')
    p.add_argument('--run', help='run id (default: ROUTINE_RUN_ID)')
    p.add_argument('--held', help='apply verdicts the tripwire held, after the owner chose to apply them')
    args = p.parse_args()
    cfg = lib.config()
    meta = lib.current_run(cfg, args.run)
    source = args.held or args.verdicts
    data = json.loads(Path(source).read_text() if source else sys.stdin.read())
    verdicts = data['verdicts'] if isinstance(data, dict) else data
    result = Applier(cfg, meta, tripwire=not args.held).apply(verdicts)
    out = lib.run_dir(cfg, meta['run_id']) / f'apply-{lib.stamp()}.json'
    lib.atomic(out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.held:
        print(json.dumps({'note': f'{len(result["applied"])} held verdict(s) applied, {len(result["rejected"])} rejected',
                          'commits': [a['url'] for a in result['applied']]}))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
