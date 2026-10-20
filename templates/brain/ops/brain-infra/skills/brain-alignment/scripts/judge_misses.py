#!/usr/bin/env python3
"""Judge misses: maintenance edits whose span another writer reverted or rewrote within the window.

Read from Git alone. Every commit `apply.py` makes carries `Routine: <id> (<run>)` and `Op: <OP> <path>`
in its body; owner-chosen options carry `Reason: Owner chose ...` and do not count as judge edits.

- UPDATE or ADD: a later commit by another writer removes a line the edit added.
- span DELETE: a later commit by another writer adds back a line the edit removed.
- page DELETE or MOVE: a later commit by another writer re-creates the old path.

The rate per workflow is misses over the maintenance edits made in the lookback window.
`python3 judge_misses.py` prints the report and writes `<state_dir>/judge-misses.json`, which the digest's
weekly edition reads.
"""
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True  # routines write nothing into the published copy
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'brain-routines' / 'scripts'))
import routinelib as lib  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
REPORT = 'judge-misses.json'


def lines_of(diff, sign):
    """The meaningful lines a -U0 diff adds ('+') or removes ('-')."""
    out = set()
    for line in diff.splitlines():
        if line.startswith(sign * 3) or not line.startswith(sign):
            continue
        text = line[1:].strip()
        if len(text) > 3 and not re.match(r'^(updated|created):', text):
            out.add(text)
    return out


def maintenance_edits(cfg, author, since_days):
    raw = lib.clone_git(cfg, 'log', f'--since={since_days} days ago', f'--author=^{re.escape(author)} <',
                        '--format=%x01%H%x02%ct%x02%B', timeout=120)
    edits = []
    for chunk in raw.split('\x01'):
        if not chunk.strip():
            continue
        sha, ct, body = chunk.split('\x02', 2)
        routine = re.search(r'^Routine: (\S+)', body, re.M)
        op = re.search(r'^Op: (\w+) (\S+)', body, re.M)
        if not routine or not op or re.search(r'^Reason: Owner chose', body, re.M):
            continue
        edits.append({'commit': sha, 'at': int(ct), 'routine': routine.group(1), 'op': op.group(1), 'path': op.group(2)})
    return edits[::-1]


def later_commits(cfg, sha, path, until):
    """Commits after sha that touch path, up to the window end: [(sha, author, ct, status)]."""
    raw = lib.clone_git(cfg, 'log', '--reverse', '--no-merges', '--format=%x01%H%x02%an%x02%ct', '--name-status',
                        f'{sha}..HEAD', '--', path, timeout=120)
    out = []
    for chunk in raw.split('\x01'):
        if not chunk.strip():
            continue
        head, _, files = chunk.partition('\n')
        c, author, ct = head.split('\x02')
        if int(ct) > until:
            break
        status = next((f.split('\t', 1)[0] for f in files.splitlines() if f.strip()), '')
        out.append((c, author, int(ct), status))
    return out


def judge(cfg, edit, author, window):
    """Return the miss for one edit, 'open' while its window runs, or None when it held."""
    until = edit['at'] + window
    diff = lib.clone_git(cfg, 'show', '--format=', '-U0', edit['commit'], '--', edit['path'], timeout=60)
    page_gone = 'deleted file mode' in diff  # a page DELETE, or the old path of a MOVE
    added, removed = lines_of(diff, '+'), lines_of(diff, '-')
    for c, who, _, status in later_commits(cfg, edit['commit'], edit['path'], until):
        if who == author:
            continue
        if page_gone:
            if status.startswith('A'):
                return {'by_commit': c, 'by_author': who, 'how': 're-created the page'}
            continue
        if status.startswith('D'):
            return None  # the page itself left (moved or deleted); its span is no longer judged
        later = lib.clone_git(cfg, 'show', '--format=', '-U0', c, '--', edit['path'], timeout=60)
        if added & lines_of(later, '-'):
            return {'by_commit': c, 'by_author': who, 'how': 'rewrote or removed the added span'}
        if edit['op'] == 'DELETE' and removed & lines_of(later, '+'):
            return {'by_commit': c, 'by_author': who, 'how': 'restored the deleted span'}
    return 'open' if lib.now() < until else None


def workflow_of(cfg, routine):
    """The workflow of a commit's routine id, matching a manifest routine's `aliases` too."""
    for r in lib.manifest(cfg)['routines']:
        if routine == r['id'] or routine in r.get('aliases', []):
            return r['workflow']
    return routine.split('-', 1)[0]


def compute(cfg, conf):
    jm = conf['judge_miss']
    author = lib.clone_git(cfg, 'config', 'user.name')
    window = jm['window_days'] * lib.DAY
    report = {'computed_at': lib.iso(), 'window_days': jm['window_days'], 'lookback_days': jm['lookback_days'],
              'threshold': jm['threshold'], 'workflows': {}, 'misses': []}
    for edit in maintenance_edits(cfg, author, jm['lookback_days']):
        wf = report['workflows'].setdefault(workflow_of(cfg, edit['routine']), {'edits': 0, 'misses': 0, 'open': 0, 'held': 0})
        wf['edits'] += 1
        verdict = judge(cfg, edit, author, window)
        if verdict == 'open':
            wf['open'] += 1
        elif verdict is None:
            wf['held'] += 1
        else:
            wf['misses'] += 1
            report['misses'].append({**edit, 'workflow': workflow_of(cfg, edit['routine']), 'url': lib.commit_url(cfg, edit['commit']),
                                     'at': lib.iso(edit['at']), **verdict, 'by_url': lib.commit_url(cfg, verdict['by_commit'])})
    for wf in report['workflows'].values():
        wf['rate'] = round(wf['misses'] / wf['edits'], 3) if wf['edits'] else 0.0
    lib.atomic(lib.state_dir(cfg) / REPORT, report)
    return report


def main():
    cfg = lib.config()
    conf = json.loads((SKILL_DIR / 'config.json').read_text())
    print(json.dumps(compute(cfg, conf), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except lib.Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
