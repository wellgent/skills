#!/usr/bin/env python3
"""GBrain host reconciler: publish GitHub main into the brain's published copy and index it.

One program for every brain. Everything brain-specific lives in config.json next to this
skill; the code is identical across brains and is cross-checked against the shared core.
"""
import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_DIR / 'config.json'
TIMING = {
    'poll_seconds': 15,          # GitHub poll interval
    'fetch_timeout': 60,         # bound on one git network call
    'import_timeout': 300,       # bound on one text import
    'embed_budget_seconds': 45,  # bound on one embed attempt; the rest resumes later
    'embed_retry_seconds': 120,  # wait after an embed attempt that left stale chunks
    'embed_max_usd': 1,          # approves and caps each embed run
    'health_check_seconds': 1800,  # engine check without a new commit
    'block_alert_seconds': 600,  # page only a block that lasts this long
    'lock_alert_seconds': 3600,  # page a sync lock held by someone else this long
    'dirty_grace_seconds': 600,  # dirt younger than this may be a writer mid-commit
    'alert_repeat_seconds': 86400,  # one page per fingerprint per day
    'event_retention_days': 14,
}
OP_MARKERS = ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD', 'REVERT_HEAD')


class Blocked(RuntimeError):
    """A step failed; the tick stops and the block clock runs."""


def now():
    return time.time()


def iso(ts=None):
    return dt.datetime.fromtimestamp(ts if ts is not None else now(), dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_config(path):
    cfg = json.loads(Path(path).read_text())
    cfg['timing'] = {**TIMING, **cfg.get('timing', {})}
    cfg['state_dir'] = Path(cfg['state_dir'])
    cfg['config_path'] = str(Path(path).resolve())
    return cfg


def atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def label(argv):
    words = [str(x) for x in argv]
    if Path(words[0]).name == 'git' and len(words) > 3 and words[1] == '-C':
        return 'git ' + words[3]
    return ' '.join([Path(words[0]).name, *words[1:2]])


def run(argv, cwd=None, env=None, timeout=90, input=None, check=True):
    """Run a command in its own process group, killed whole on timeout."""
    p = subprocess.Popen([str(x) for x in argv], cwd=cwd, env=env, text=True, start_new_session=True,
                         stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = p.communicate(input=input, timeout=timeout)
    except BaseException as error:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
            try:
                p.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.communicate()
        if isinstance(error, subprocess.TimeoutExpired):
            raise Blocked(f'{label(argv)} timed out after {timeout}s')
        raise
    if check and p.returncode:
        tail = (err or '').strip().splitlines()[-1:] or ['']
        raise Blocked(f'{label(argv)} failed (exit {p.returncode}): {tail[0][:300]}')
    return out.strip() if check else (p.returncode, out, err)


class Reconciler:
    def __init__(self, cfg):
        self.cfg = cfg
        self.t = cfg['timing']
        self.repo = cfg['published_repo']
        self.branch = cfg.get('branch', 'main')
        self.state_path = cfg['state_dir'] / 'state.json'
        self.state = self.load_state()
        own = os.path.relpath(SKILL_DIR, self.repo)
        self.own = None if own.startswith('..') else own + '/'  # this skill's path in the brain
        self.restart = False
        os.environ['PATH'] = cfg.get('path', os.environ.get('PATH', ''))

    # state and events

    def load_state(self):
        try:
            return json.loads(self.state_path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self, **fields):
        self.state.update(fields)
        self.state['heartbeat_at'] = iso()
        self.state['pid'] = os.getpid()
        atomic(self.state_path, self.state)

    def event(self, kind, **fields):
        record = {'at': iso(), 'kind': kind, **fields}
        print(json.dumps(record, ensure_ascii=False), flush=True)
        events = self.cfg['state_dir'] / 'events'
        events.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (events / (record['at'][:10] + '.jsonl')).open('a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def prune_events(self):
        cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=self.t['event_retention_days'])).strftime('%Y-%m-%d')
        for f in (self.cfg['state_dir'] / 'events').glob('*.jsonl'):
            if f.stem < cutoff:
                f.unlink()

    # git and engine

    def git(self, *args, timeout=None, env=None):
        return run(['git', '-C', self.repo, *args], timeout=timeout or self.t['fetch_timeout'], env=env)

    def fetch(self):
        self.git('fetch', '--quiet', 'origin', self.branch)
        return self.git('rev-parse', 'origin/' + self.branch)

    def is_ancestor(self, older, newer):
        code, _, _ = run(['git', '-C', self.repo, 'merge-base', '--is-ancestor', older, newer], check=False)
        return code == 0

    def engine_receipt(self):
        raw = run([self.cfg['bun_bin'], SKILL_DIR / 'scripts' / 'index-receipt.ts'], timeout=60,
                  env=dict(os.environ, GBRAIN_SRC=self.cfg['gbrain_src'], RECONCILER_SOURCE=self.cfg['source_id']))
        return json.loads(raw.splitlines()[-1])

    def import_text(self, head):
        raw = run([self.cfg['gbrain_bin'], 'sync', '--repo', self.repo, '--source', self.cfg['source_id'],
                   '--no-pull', '--no-embed', '--json'], timeout=self.t['import_timeout'], cwd=self.repo)
        result = None
        for line in reversed(raw.splitlines()):
            with contextlib.suppress(json.JSONDecodeError):
                result = json.loads(line)
                break
        if not isinstance(result, dict):
            raise Blocked('sync returned no JSON receipt')
        status = result.get('sync_status')
        if result.get('source_id') != self.cfg['source_id'] or status not in ('synced', 'first_sync', 'up_to_date'):
            raise Blocked(f'sync returned {status or "an unknown result"}')
        proof = self.engine_receipt()
        if proof.get('indexed_commit') != head or proof.get('source_path') != self.repo:
            raise Blocked('engine bookmark or source path does not match the published copy')
        return result, proof

    def embed(self):
        env = dict(os.environ, GBRAIN_EMBED_LOCK_HEARTBEAT_MS='86400000')
        try:
            run([self.cfg['gbrain_bin'], 'embed', '--stale', '--max-usd', str(self.t['embed_max_usd'])],
                timeout=self.t['embed_budget_seconds'], env=env, cwd=self.repo)
        except Blocked as error:
            # A timed-out or budget-stopped embed keeps what it embedded; the next attempt resumes.
            if 'timed out' not in str(error) and 'exit 11' not in str(error):
                raise
        return self.engine_receipt().get('stale_chunks')

    # published copy hygiene

    def inspect(self, origin):
        """Return what makes the published copy differ from a clean fast-forwardable main."""
        gd = Path(self.git('rev-parse', '--absolute-git-dir'))
        problems = [f'{m} present' for m in OP_MARKERS if (gd / m).exists()]
        branch = run(['git', '-C', self.repo, 'symbolic-ref', '--quiet', '--short', 'HEAD'], check=False)[1].strip()
        if branch != self.branch:
            problems.append(f'HEAD is {branch or "detached"}, not {self.branch}')
        dirty = self.git('status', '--porcelain=v1', '--untracked-files=all').splitlines()
        if dirty:
            problems.append(f'{len(dirty)} uncommitted path(s)')
        if not self.is_ancestor('HEAD', origin):
            problems.append('local commits not on origin/' + self.branch)
        return problems, dirty

    def rescue(self, origin, problems, dirty):
        """Push the published copy's divergence to a rescue branch, reset it to origin, file an issue."""
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        branch = 'rescue/' + stamp
        head = self.git('rev-parse', 'HEAD')
        index = self.cfg['state_dir'] / 'rescue.index'
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        self.git('read-tree', 'HEAD', env=env)
        self.git('add', '-A', '--', '.', env=env)
        tree = self.git('write-tree', env=env)
        index.unlink(missing_ok=True)
        parents = [head]
        with contextlib.suppress(Blocked):
            local = self.git('rev-parse', 'refs/heads/' + self.branch)
            if local != head and not self.is_ancestor(local, head):
                parents.append(local)
        author = self.cfg['rescue_author']
        ident = {'GIT_AUTHOR_NAME': author['name'], 'GIT_AUTHOR_EMAIL': author['email'],
                 'GIT_COMMITTER_NAME': author['name'], 'GIT_COMMITTER_EMAIL': author['email']}
        message = f'rescue: published copy divergence at {stamp}\n\n' + '\n'.join(problems)
        args = ['commit-tree', tree, '-m', message]
        for parent in parents:
            args += ['-p', parent]
        snapshot = self.git(*args, env=dict(os.environ, **ident))
        if tree == self.git('rev-parse', origin + '^{tree}') and all(self.is_ancestor(p, origin) for p in parents):
            snapshot = None  # nothing beyond origin to keep
        if snapshot:
            self.git('push', '--quiet', 'origin', f'{snapshot}:refs/heads/{branch}')
        gd = Path(self.git('rev-parse', '--absolute-git-dir'))
        for verb, marker in (('rebase', 'rebase-merge'), ('rebase', 'rebase-apply'), ('merge', 'MERGE_HEAD'),
                             ('cherry-pick', 'CHERRY_PICK_HEAD'), ('revert', 'REVERT_HEAD')):
            if (gd / marker).exists():
                run(['git', '-C', self.repo, verb, '--abort'], check=False)
        for marker in ('rebase-merge', 'rebase-apply'):
            if (gd / marker).exists():
                run(['git', '-C', self.repo, 'rebase', '--quit'], check=False)
        self.git('checkout', '--quiet', '--force', '-B', self.branch, origin)
        self.git('clean', '-fdq')
        if self.git('status', '--porcelain=v1'):
            raise Blocked('published copy is still dirty after the rescue reset')
        issue = None
        if snapshot:
            issue = self.file_rescue_issue(branch, snapshot, origin, problems, dirty)
        self.event('rescue', branch=branch if snapshot else None, commit=snapshot, problems=problems, issue=issue)
        return branch

    def file_rescue_issue(self, branch, snapshot, origin, problems, dirty):
        na = self.cfg['needs_attention']
        slug = self.cfg['github_repo']
        changed = self.git('diff', '--name-status', origin, snapshot).splitlines()
        commits = self.git('log', '--format=%h %an: %s', f'{origin}..{snapshot}').splitlines()[1:]
        shown = changed[:40] + ([f'... {len(changed) - 40} more'] if len(changed) > 40 else [])
        content = any(line.split('\t')[-1].endswith('.md') for line in changed)
        url = f'https://github.com/{slug}/tree/{branch}'
        fingerprint = 'reconciler-rescue:' + branch
        body = '\n'.join([
            f'**Finding.** The published copy `{self.repo}` on this host diverged from `origin/{self.branch}` for over {self.t["dirty_grace_seconds"] // 60} minutes: ' + '; '.join(problems) + '.',
            '',
            '**Why the reconciler did not settle it.** Nobody writes in the published copy, and whether these changes belong on main is a content call.',
            '',
            f'**What it did.** It pushed everything to [`{branch}`]({url}), reset the copy to `origin/{self.branch}` (`{origin[:12]}`) and kept syncing.',
            '',
            '**Evidence.** Changes against main:',
            '',
            '```',
            *(shown or ['(none)']),
            '```',
            *(['', 'Local commits on the branch:', '', '```', *commits[:20], '```'] if commits else []),
            '',
            '**Options.**',
            '',
            f'1. Land: a writer applies the wanted changes from `{branch}` through its own clone, then deletes the branch.',
            f'2. Discard: delete `{branch}` and close this issue.',
            '',
            f'**Recommended:** {"1, the branch holds markdown pages" if content else "2, the branch holds no markdown pages"}.',
            '',
            f'<!-- fingerprint: {fingerprint} -->',
        ])
        title = f'{self.cfg["brain"]} published copy rescued to {branch}'
        argv = ['gh', 'issue', 'create', '--repo', slug, '--title', title, '--body-file', '-']
        if na.get('assignee'):
            argv += ['--assignee', na['assignee']]
        for name in na.get('labels', []):
            argv += ['--label', name]
        try:
            return run(argv, input=body, timeout=60).splitlines()[-1]
        except Blocked as error:
            self.alert('rescue_issue', f'Rescued to {branch}, but the needs-attention issue failed: {error}', force=True)
            return None

    # alerts

    def alert(self, stage, reason, force=False):
        """Page #ops-alerts once per stage per day; a failed send is logged and kept for the rollup."""
        alerts = self.state.setdefault('alerts', {})
        attempts = self.state.setdefault('alert_attempts', {})
        if not force and (now() - alerts.get(stage, {}).get('sent_at', 0) < self.t['alert_repeat_seconds']
                          or now() - attempts.get(stage, 0) < self.t['block_alert_seconds']):
            return
        attempts[stage] = now()
        a = self.cfg['alert']
        text = f'{self.cfg["brain"]} reconciler needs attention\nStage: {stage}\nReason: {reason}\nInspect: journalctl --user -u {self.cfg["unit"]}'
        try:
            run([a['openclaw_bin'], 'message', 'send', '--account', a['account'], '--channel', 'discord',
                 '--target', 'channel:' + a['channel'], '--message', text, '--silent'], timeout=60)
            alerts[stage] = {'sent_at': now(), 'reason': str(reason)[:500]}
            self.event('alert', stage=stage, reason=str(reason)[:500])
        except Blocked as error:
            self.event('alert_failed', stage=stage, reason=str(reason)[:500], error=str(error))

    def recovered(self, stage):
        alerts = self.state.get('alerts', {})
        if stage in alerts:
            alerts.pop(stage)
            self.state.get('alert_attempts', {}).pop(stage, None)
            a = self.cfg['alert']
            with contextlib.suppress(Blocked):
                run([a['openclaw_bin'], 'message', 'send', '--account', a['account'], '--channel', 'discord',
                     '--target', 'channel:' + a['channel'], '--message',
                     f'{self.cfg["brain"]} reconciler recovered: {stage}', '--silent'], timeout=60)
            self.event('recovered', stage=stage)

    def check_deadman(self):
        for item in self.cfg.get('deadman', []):
            path = Path(item['path'])
            age = now() - path.stat().st_mtime if path.exists() else None
            stage = 'deadman:' + item['name']
            if age is None or age > item['max_age_seconds']:
                self.alert(stage, f'{item["name"]} heartbeat {path} is ' + ('missing' if age is None else f'{int(age // 60)} minutes old'))
            else:
                self.recovered(stage)

    # the cycle

    def tick(self):
        """One poll: fetch, guard the published copy, fast-forward, import, embed."""
        s = self.state
        origin = self.fetch()
        problems, dirty = self.inspect(origin)
        if problems:
            s.setdefault('dirty_since', now())
            age = now() - s['dirty_since']
            if age < self.t['dirty_grace_seconds']:
                self.save(phase='dirty_grace', dirty=problems)
                return
            self.rescue(origin, problems, dirty)
        s.pop('dirty_since', None)
        s.pop('dirty', None)
        head = self.git('rev-parse', 'HEAD')
        if head != origin:
            changed = self.git('diff', '--name-only', head, origin).splitlines()
            self.git('merge', '--ff-only', '--quiet', origin)
            self.event('publish', old=head, new=origin, files=len(changed))
            head = origin
            if self.own and any(p.startswith(self.own) for p in changed):
                self.restart = True
        self.save(phase='publishing', published_head=head, published_at=iso())
        due = now() - s.get('health_checked_at', 0) >= self.t['health_check_seconds']
        if s.get('indexed_head') != head or due:
            if due and s.get('indexed_head') == head:
                proof = self.engine_receipt()
                s['health_checked_at'] = now()
                if proof.get('indexed_commit') != head or proof.get('source_path') != self.repo:
                    s['indexed_head'] = None
                if proof.get('stale_chunks'):
                    s['embedded_head'] = None
            if s.get('indexed_head') != head:
                started = now()
                result, proof = self.import_text(head)
                self.event('import', commit=head, status=result.get('sync_status'), added=result.get('added'),
                           modified=result.get('modified'), deleted=result.get('deleted'), seconds=round(now() - started, 1))
                s['health_checked_at'] = now()
                self.save(indexed_head=head, indexed_at=iso())
        if s.get('embedded_head') != head and now() >= s.get('embed_retry_at', 0):
            # Embedding failures never block publication or import; they page on their own clock.
            started = now()
            s['embed_retry_at'] = now() + self.t['embed_retry_seconds']
            try:
                stale = self.embed()
            except Blocked as error:
                s.setdefault('embed_failing_since', now())
                self.event('embed_failed', commit=head, reason=str(error)[:500])
                if now() - s['embed_failing_since'] >= self.t['block_alert_seconds']:
                    self.alert('embed', error)
                return
            if stale == 0:
                s.pop('embed_retry_at', None)
                if s.pop('embed_failing_since', None):
                    self.recovered('embed')
                self.save(embedded_head=head, embedded_at=iso())
                self.event('embed', commit=head, seconds=round(now() - started, 1))
            else:
                self.event('embed_pending', commit=head, stale_chunks=stale)

    def serve(self, once=False):
        lock_path = Path(self.cfg['sync_lock'])
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with (self.cfg['state_dir'] / 'worker.lock').open('a') as worker:
            fcntl.flock(worker, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.event('start', pid=os.getpid(), config=self.cfg['config_path'])
            self.prune_events()
            while True:
                with lock_path.open('a') as handle:
                    try:
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        self.state.setdefault('lock_busy_since', now())
                        if now() - self.state['lock_busy_since'] >= self.t['lock_alert_seconds']:
                            self.alert('lock_busy', f'{lock_path} held by another process for over {self.t["lock_alert_seconds"] // 60} minutes')
                        self.save(phase='lock_busy')
                    else:
                        if self.state.pop('lock_busy_since', None):
                            self.recovered('lock_busy')
                        try:
                            self.tick()
                            if self.state.pop('blocked_since', None):
                                self.state.pop('blocked_reason', None)
                                self.recovered('blocked')
                            if self.state.get('phase') != 'dirty_grace':
                                self.save(phase='idle')
                        except Exception as error:
                            self.state.setdefault('blocked_since', now())
                            self.state['blocked_reason'] = str(error)[:500]
                            self.event('blocked', reason=str(error)[:500])
                            if now() - self.state['blocked_since'] >= self.t['block_alert_seconds']:
                                self.alert('blocked', error)
                            self.save(phase='blocked')
                self.check_deadman()
                self.save()
                if self.restart:
                    # New reconciler code was published; systemd starts the new version.
                    self.event('restart', reason='reconciler code changed')
                    return 0
                if once:
                    return 0
                if now() - self.state.get('pruned_at', 0) > 86400:
                    self.prune_events()
                    self.state['pruned_at'] = now()
                time.sleep(self.t['poll_seconds'])

    # writer-facing commands

    def receipt(self, commit, level, wait):
        """Report whether a pushed commit is published, imported and embedded; wait up to `wait` seconds."""
        until = now() + wait
        order = {'published': 1, 'text': 2, 'complete': 3}
        while True:
            state = self.load_state()
            reached = None
            code, full, _ = run(['git', '-C', self.repo, 'rev-parse', '--verify', '--quiet', commit + '^{commit}'], check=False)
            full = full.strip()
            if code == 0:
                for name, key in (('complete', 'embedded_head'), ('text', 'indexed_head'), ('published', 'published_head')):
                    if state.get(key) and self.is_ancestor(full, state[key]):
                        reached = name
                        break
            result = {'commit': full or commit, 'reached': reached, 'wanted': level,
                      'published_head': state.get('published_head'), 'indexed_head': state.get('indexed_head'),
                      'embedded_head': state.get('embedded_head'), 'phase': state.get('phase'),
                      'blocked_reason': state.get('blocked_reason')}
            if reached and order[reached] >= order[level]:
                return result, 0
            if now() >= until:
                return result, 75
            time.sleep(2)

    def rollup(self, hours):
        since = iso(now() - hours * 3600)
        events = []
        for f in sorted((self.cfg['state_dir'] / 'events').glob('*.jsonl')):
            if f.stem >= since[:10]:
                events += [e for e in map(json.loads, f.read_text().splitlines()) if e['at'] >= since]
        count = lambda kind: sum(1 for e in events if e['kind'] == kind)
        seconds = [e['seconds'] for e in events if e['kind'] == 'import' and 'seconds' in e]
        state = self.load_state()
        return {
            'since': since, 'publishes': count('publish'), 'imports': count('import'),
            'import_seconds_max': max(seconds, default=None), 'embeds': count('embed'),
            'embed_pending': count('embed_pending'), 'blocked_ticks': count('blocked'),
            'alerts': [e for e in events if e['kind'] == 'alert'],
            'alert_send_failures': [e for e in events if e['kind'] == 'alert_failed'],
            'rescues': [e for e in events if e['kind'] == 'rescue'], 'restarts': count('restart'),
            'heartbeat_at': state.get('heartbeat_at'), 'phase': state.get('phase'),
            'published_head': state.get('published_head'), 'embedded_head': state.get('embedded_head'),
        }

    def unit(self):
        python = self.cfg.get('python_bin', '/usr/bin/python3')
        return '\n'.join([
            '[Unit]',
            f'Description={self.cfg["brain"]} host reconciler',
            'After=network-online.target',
            'Wants=network-online.target',
            'StartLimitIntervalSec=0',
            '',
            '[Service]',
            'Type=simple',
            f'ExecStart={python} {Path(__file__).resolve()} --config {self.cfg["config_path"]} worker',
            'Restart=always',
            'RestartSec=10',
            'TimeoutStopSec=30',
            'KillMode=control-group',
            f'EnvironmentFile=-{self.cfg["env_file"]}',
            f'Environment=PATH={self.cfg["path"]}',
            'Environment=PYTHONDONTWRITEBYTECODE=1',
            f'WorkingDirectory={self.cfg["state_dir"]}',
            'UMask=0077',
            '',
            '[Install]',
            'WantedBy=default.target',
            '',
        ])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default=str(DEFAULT_CONFIG))
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('worker', help='run the service loop')
    c.add_argument('--once', action='store_true', help='one tick, then exit')
    sub.add_parser('status', help='print the worker state')
    c = sub.add_parser('receipt', help='indexing receipt for a pushed commit')
    c.add_argument('commit')
    c.add_argument('--level', choices=('published', 'text', 'complete'), default='complete')
    c.add_argument('--wait', type=int, default=0, help='seconds to wait for the level')
    c = sub.add_parser('rollup', help='summary of recent runs for the health workflow')
    c.add_argument('--hours', type=float, default=24)
    sub.add_parser('unit', help='print the systemd user unit for this brain')
    args = p.parse_args()
    cfg = load_config(args.config)
    cfg['state_dir'].mkdir(parents=True, exist_ok=True, mode=0o700)
    r = Reconciler(cfg)
    code = 0
    if args.command == 'worker':
        return r.serve(args.once)
    if args.command == 'status':
        result = r.load_state()
    elif args.command == 'receipt':
        result, code = r.receipt(args.commit, args.level, args.wait)
    elif args.command == 'rollup':
        result = r.rollup(args.hours)
    else:
        sys.stdout.write(r.unit())
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(128 + signum))
    try:
        sys.exit(main())
    except BlockingIOError:
        print(json.dumps({'error': 'another worker holds the worker lock'}), file=sys.stderr)
        sys.exit(1)
    except Blocked as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
