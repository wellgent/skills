"""Shared library of the brain routine framework: config, manifest, locks, run journal,
Discord posts, alerts, the subscription window, the maintenance clone and needs-attention issues.

One program for every brain. Everything brain-specific lives in config.json next to this
skill and in the brain's routine manifest; the code is cross-checked against the shared core.
"""
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import uuid

SCRIPTS = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS.parent
SKILLS_DIR = SKILL_DIR.parent
CONFIG = SKILL_DIR / 'config.json'
MARKER = '<!-- brain-routines -->'
ANSWER = '<!-- brain-routines-answer -->'  # an owner's answer the agent recorded from the digest channel or a chat
DAY = 86400
DISCORD_LIMIT = 1900
TIMING = {
    'default_timeout_seconds': 1800,  # a routine's cron timeout unless the manifest sets one
    'lease_wait_seconds': 1800,       # wait for another routine's maintenance lease
    'sync_lock_wait_seconds': 600,    # wait for the reconciler's sync lock
    'action_timeout_seconds': 600,    # bound on one needs-attention option action
    'run_retention_days': 14,
}


class Failed(RuntimeError):
    """A step failed; the message says which and why."""


def now():
    return time.time()


def iso(ts=None):
    return dt.datetime.fromtimestamp(ts if ts is not None else now(), dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def stamp():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')


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


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def run(argv, cwd=None, env=None, timeout=120, input=None, check=True):
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
            raise Failed(f'{Path(str(argv[0])).name} timed out after {timeout}s')
        raise
    if check and p.returncode:
        tail = (err or out or '').strip().splitlines()[-1:] or ['']
        raise Failed(f'{" ".join(Path(str(a)).name for a in argv[:3])} failed (exit {p.returncode}): {tail[0][:300]}')
    return out.strip() if check else (p.returncode, out, err)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# config and manifest

def config():
    cfg = read_json(CONFIG)
    cfg['timing'] = {**TIMING, **cfg.get('timing', {})}
    os.environ['PATH'] = cfg.get('path', os.environ.get('PATH', ''))
    return cfg


def manifest(cfg):
    m = read_json(Path(cfg['published_repo']) / cfg['manifest'])
    if not m:
        raise Failed(f'routine manifest {cfg["manifest"]} is missing or invalid')
    return m


def routine(cfg, rid):
    for r in manifest(cfg)['routines']:
        if r['id'] == rid:
            return r
    raise Failed(f'routine {rid} is not in the manifest')


def state_dir(cfg):
    path = Path(cfg['state_dir'])
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def load_state(cfg):
    return read_json(state_dir(cfg) / 'state.json', {})


def save_state(cfg, state):
    atomic(state_dir(cfg) / 'state.json', state)


@contextlib.contextmanager
def flock(path, wait):
    """Hold an exclusive flock on path, waiting up to `wait` seconds."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a') as handle:
        until = now() + wait
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if now() >= until:
                    raise Failed(f'{path} is held by another process after {wait}s')
                time.sleep(2)
        yield


def sync_lock(cfg):
    """The reconciler's lock, for any step that runs gbrain sync, embed or a full doctor."""
    return flock(cfg['sync_lock'], cfg['timing']['sync_lock_wait_seconds'])


# the maintenance lease: one routine at a time, held across processes for agent turns

def _alive(pid):
    if not pid:
        return True  # an agent turn's lease lives until it expires
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


LEASE_POLL = 10  # seconds between a waiter's lease checks


def _in_force(lease):
    """The lease in force: a run admitted into a hold that died hands the lease back to the hold."""
    while lease and not (lease['expires_at'] > now() and _alive(lease.get('pid'))):
        lease = lease.get('within')
    return lease


def acquire_lease(cfg, run_id, rid, ttl, pid=None, hold=None):
    """Take the brain maintenance lease in arrival order; return the stale lease it replaced, if any.

    Waiters queue in lease-queue.json and the oldest one takes the lease when it is free. A waiter refreshes
    its entry on every check, so the entry of a waiter that died drops out after six missed checks.
    An operator hold (`hold`: its reason and the routines it admits) keeps the lease across a manual
    operation such as an engine upgrade; only the routines it admits run inside it, one at a time."""
    until = now() + cfg['timing']['lease_wait_seconds']
    path, queue_path = state_dir(cfg) / 'lease.json', state_dir(cfg) / 'lease-queue.json'
    while True:
        with flock(cfg['maintenance_lock'], 60):
            raw = read_json(path)
            lease = _in_force(raw)
            queue = {k: w for k, w in read_json(queue_path, {}).items() if w['seen_at'] > now() - 6 * LEASE_POLL}
            queue.setdefault(run_id, {'routine': rid, 'since': now()})['seen_at'] = now()
            admits = (lease or {}).get('hold', {}).get('admit', [])
            eligible = [k for k, w in queue.items() if not lease or w['routine'] in admits]
            first = min(eligible or queue, key=lambda k: (queue[k]['since'], k))
            if (eligible and first == run_id) or now() >= until:
                del queue[run_id]
                atomic(queue_path, queue)
                if run_id not in eligible:
                    raise Failed(f'maintenance lease held by {lease["run_id"]}')
                if first != run_id:
                    raise Failed(f'maintenance lease queued behind {first}')
                new = {'run_id': run_id, 'routine': rid, 'pid': pid, 'acquired_at': now(), 'expires_at': now() + ttl}
                if hold:
                    new['hold'] = hold
                if lease:
                    new['within'] = lease
                atomic(path, new)
                return raw if raw and raw is not lease else None
            atomic(queue_path, queue)
        time.sleep(LEASE_POLL)


def holds_lease(cfg, run_id):
    lease = read_json(state_dir(cfg) / 'lease.json')
    return bool(lease and lease['run_id'] == run_id and lease['expires_at'] > now())


def release_lease(cfg, run_id):
    """Release a run's lease, handing it back to the hold the run ran within, or end a hold."""
    with flock(cfg['maintenance_lock'], 60):
        path = state_dir(cfg) / 'lease.json'
        lease = read_json(path)
        if not lease:
            return
        if lease['run_id'] == run_id:
            within = _in_force(lease.get('within'))
            if within:
                atomic(path, within)
            else:
                path.unlink()
        elif (lease.get('within') or {}).get('run_id') == run_id:
            atomic(path, {k: v for k, v in lease.items() if k != 'within'})


# the run journal

def run_dir(cfg, run_id):
    return state_dir(cfg) / 'runs' / run_id


def current_run(cfg, run_id=None):
    """The run a script acts for: --run, else ROUTINE_RUN_ID; it must hold the lease."""
    run_id = run_id or os.environ.get('ROUTINE_RUN_ID')
    if not run_id:
        raise Failed('no run: pass --run <run_id> or run inside a routine')
    meta = read_json(run_dir(cfg, run_id) / 'run.json')
    if not meta:
        raise Failed(f'run {run_id} has no run.json')
    if not holds_lease(cfg, run_id):
        raise Failed(f'run {run_id} does not hold the maintenance lease')
    return meta


def journal(cfg, run_id, kind, **fields):
    """Record what a run did; the run record and the daily digest are built from this journal."""
    if not run_id:
        return
    path = run_dir(cfg, run_id) / 'journal.jsonl'
    with path.open('a') as f:
        f.write(json.dumps({'at': iso(), 'kind': kind, **fields}, ensure_ascii=False) + '\n')


def read_journal(cfg, run_id):
    path = run_dir(cfg, run_id) / 'journal.jsonl'
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def step_env(cfg, meta):
    return dict(os.environ, ROUTINE_ID=meta['routine'], ROUTINE_RUN_ID=meta['run_id'],
                ROUTINE_RUN_DIR=str(run_dir(cfg, meta['run_id'])), ROUTINE_WORKFLOW=meta['workflow'],
                BRAIN_MAINTENANCE_REPO=cfg['maintenance_repo'],
                PYTHONPATH=os.pathsep.join(filter(None, [str(SCRIPTS), os.environ.get('PYTHONPATH')])),
                PYTHONDONTWRITEBYTECODE='1')


# Discord

def post(cfg, channel, text, silent=True):
    """Post to a Discord channel in chunks under the message limit; return None or the error."""
    chunks, current = [], ''
    for line in text.splitlines():
        line = line[:DISCORD_LIMIT]
        if current and len(current) + len(line) + 1 > DISCORD_LIMIT:
            chunks.append(current)
            current = ''
        current = f'{current}\n{line}' if current else line
    chunks.append(current)
    o = cfg['openclaw']
    try:
        for chunk in chunks:
            run([o['bin'], 'message', 'send', '--account', o['account'], '--channel', 'discord',
                 '--target', 'channel:' + str(channel), '--message', chunk] + (['--silent'] if silent else []), timeout=60)
    except Failed as error:
        return str(error)
    return None


def alert(cfg, fingerprint, text):
    """Page #ops-alerts once per fingerprint per day; a failed send is kept for the daily digest."""
    state = load_state(cfg)
    sent = state.setdefault('alerts', {})
    if now() - sent.get(fingerprint, 0) < DAY:
        return 'deduped'
    error = post(cfg, cfg['channels']['ops-alerts'], text, silent=False)
    if error:
        state.setdefault('send_failures', []).append({'at': iso(), 'target': 'ops-alerts', 'fingerprint': fingerprint, 'error': error})
    else:
        sent[fingerprint] = now()
    for key in [k for k, t in sent.items() if now() - t > 7 * DAY]:
        sent.pop(key)
    save_state(cfg, state)
    return error or 'sent'


# the subscription window

WINDOW_LABELS = {'168h': 'Week', '24h': 'Day'}


def usage(cfg):
    """The provider quota windows (percent used) and credit balance OpenClaw reports, or None when unreadable."""
    try:
        out = run([cfg['openclaw']['bin'], 'gateway', 'call', 'usage.status', '--json', '--timeout', '20000'], timeout=25)
        data = json.loads(out[out.find('{'):])
    except (Failed, OSError, ValueError):
        return None
    return {p.get('provider', '?'): {'windows': {WINDOW_LABELS.get(w['label'], w['label']): w.get('usedPercent') for w in p.get('windows', [])},
                                     'credits': next((b.get('amount') for b in p.get('billing', []) if b.get('unit') == 'credits'), None)}
            for p in data.get('providers', [])} or None


def window_deltas(cfg, start, end):
    """Points each agentTurn run that started in [start, end) moved each quota window: {"<provider> <window>": {routine: points}}."""
    path = state_dir(cfg) / 'load.jsonl'
    out = {}
    for line in (path.read_text().splitlines() if path.exists() else []):
        rec = json.loads(line)
        if not start <= rec['started_at'] < end or not rec.get('start') or not rec.get('end'):
            continue
        for provider, s in rec['start'].items():
            for label, before in s['windows'].items():
                after = rec['end'].get(provider, {}).get('windows', {}).get(label)
                if before is not None and after is not None and after >= before:  # a lower reading means the window reset
                    per = out.setdefault(f'{provider} {label.lower()}', {})
                    per[rec['routine']] = per.get(rec['routine'], 0) + after - before
    return out


# the maintenance clone

def clone_git(cfg, *args, timeout=120, env=None, check=True):
    return run(['git', '-C', cfg['maintenance_repo'], *args], timeout=timeout, env=env, check=check)


def reset_clone(cfg):
    """Fetch, then reset and clean the maintenance clone to origin; return what was wiped."""
    repo = Path(cfg['maintenance_repo'])
    if not (repo / '.git').exists():
        raise Failed(f'maintenance clone {repo} is missing')
    branch = cfg.get('branch', 'main')
    clone_git(cfg, 'fetch', '--quiet', 'origin', branch)
    gd = Path(clone_git(cfg, 'rev-parse', '--absolute-git-dir'))
    for verb, marker in (('rebase', 'rebase-merge'), ('rebase', 'rebase-apply'), ('merge', 'MERGE_HEAD'), ('cherry-pick', 'CHERRY_PICK_HEAD')):
        if (gd / marker).exists():
            clone_git(cfg, verb, '--abort', check=False)
    dirty = clone_git(cfg, 'status', '--porcelain=v1', '--untracked-files=all').splitlines()
    code, ahead, _ = clone_git(cfg, 'rev-list', '--count', f'origin/{branch}..HEAD', check=False)
    clone_git(cfg, 'checkout', '--quiet', '--force', '-B', branch, f'origin/{branch}')
    clone_git(cfg, 'reset', '--quiet', '--hard', f'origin/{branch}')
    clone_git(cfg, 'clean', '-ffdxq')
    wiped = []
    if dirty:
        wiped.append(f'{len(dirty)} uncommitted path(s)')
    if code == 0 and ahead.strip() not in ('', '0'):
        wiped.append(f'{ahead.strip()} unpushed commit(s)')
    return wiped


def push_clone(cfg, attempts=3):
    """Rebase the clone's commits onto origin and push them; return the pushed head."""
    branch = cfg.get('branch', 'main')
    for attempt in range(attempts):
        clone_git(cfg, 'fetch', '--quiet', 'origin', branch)
        code, _, err = clone_git(cfg, 'rebase', '--quiet', f'origin/{branch}', check=False)
        if code:
            clone_git(cfg, 'rebase', '--abort', check=False)
            raise Failed(f'rebase onto origin/{branch} conflicted: {err.strip()[-200:]}')
        code, _, err = clone_git(cfg, 'push', '--quiet', 'origin', f'HEAD:{branch}', check=False)
        if code == 0:
            return clone_git(cfg, 'rev-parse', 'HEAD')
        time.sleep(2 + attempt * 3)
    raise Failed(f'push to origin/{branch} failed: {err.strip()[-200:]}')


def commit_url(cfg, sha):
    return f'https://github.com/{cfg["github_repo"]}/commit/{sha}'


# needs attention

def gh(cfg, *args, input=None, timeout=60):
    return run(['gh', *args], input=input, timeout=timeout)


def _json_comment(name, obj):
    # JSON inside an HTML comment: escape '>' so the comment cannot close early.
    return f'<!-- {name}: ' + json.dumps(obj, ensure_ascii=False).replace('>', '\\u003e') + ' -->'


def _parse_comment(name, body):
    m = re.search(rf'<!-- {name}: (.*?) -->', body or '', re.S)
    if not m:
        return None
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(m.group(1))
    return m.group(1).strip()


def open_attention(cfg, workflow=None):
    labels = ['--label', 'needs-attention'] + (['--label', f'workflow:{workflow}'] if workflow else [])
    raw = gh(cfg, 'issue', 'list', '--repo', cfg['github_repo'], '--state', 'open', *labels,
             '--json', 'number,title,url,body,author', '--limit', '200')
    return json.loads(raw or '[]')


def file_attention(cfg, meta, fingerprint, title, finding, why, evidence, options, recommended, reason=''):
    """Open one needs-attention issue per fingerprint; return (url, created).

    options: [{"label": str, "detail": str, "action": {"type": "close"} | {"type": "command", "argv": [...]}}]
    A command action runs from the filing routine's skill directory on the run after the owner's reply.
    """
    if not 1 <= recommended <= len(options):
        raise Failed('recommended option is out of range')
    for issue in open_attention(cfg):
        if _parse_comment('fingerprint', issue['body']) == fingerprint:
            journal(cfg, meta and meta['run_id'], 'attention', url=issue['url'], title=issue['title'], new=False)
            return issue['url'], False
    workflow = meta['workflow'] if meta else 'health'
    evidence = evidence if isinstance(evidence, list) else [evidence]
    lines = [
        f'**Finding.** {finding}', '',
        f'**Why the routine could not settle it.** {why}', '',
        '**Evidence.**', '', *[f'- {e}' for e in evidence], '',
        '**Options.**', '',
        *[f'{i}. **{o["label"]}**' + (f' - {o["detail"]}' if o.get('detail') else '') for i, o in enumerate(options, 1)], '',
        f'**Recommended:** {recommended}' + (f', {reason}' if reason else '') + '.', '',
        f'Reply with the option number, here or to the digest in `#brain-review`. '
        f'The next `{meta["routine"] if meta else workflow}` run applies it and closes this issue.', '',
        f'<!-- fingerprint: {fingerprint} -->',
        _json_comment('options', {'skill': meta['skill'] if meta else 'brain-routines',
                                  'options': [{'label': o['label'], 'action': o.get('action', {'type': 'close'})} for o in options]}),
    ]
    argv = ['issue', 'create', '--repo', cfg['github_repo'], '--title', title, '--body-file', '-',
            '--assignee', cfg['owner_github'], '--label', 'needs-attention', '--label', f'workflow:{workflow}']
    url = gh(cfg, *argv, input='\n'.join(lines)).splitlines()[-1]
    journal(cfg, meta and meta['run_id'], 'attention', url=url, title=title, new=True)
    return url, True


def parse_choice(text, count):
    """Read the option number from a reply: a leading number, or 'option N' anywhere."""
    body = re.sub(r'^>.*$', '', text or '', flags=re.M)  # drop quoted lines
    first = next((line for line in body.splitlines() if line.strip()), '')
    m = re.match(r'^\W*(?:option\s*)?#?(\d+)\b', first, re.I) or re.search(r'\boption\s*#?(\d+)\b', body, re.I)
    if m and 1 <= int(m.group(1)) <= count:
        return int(m.group(1))
    return None


def _rescue_options(fingerprint):
    branch = fingerprint.split(':', 1)[1]
    return {'skill': 'brain-routines', 'options': [
        {'label': 'Land', 'action': {'type': 'rescue-land', 'branch': branch}},
        {'label': 'Discard', 'action': {'type': 'rescue-discard', 'branch': branch}},
    ]}


def _rescue(cfg, meta, branch, land):
    exists = clone_git(cfg, 'ls-remote', '--heads', 'origin', branch, timeout=60)
    if not exists:
        return {'note': f'`{branch}` is already gone'}
    result = {}
    if land:
        reset_clone(cfg)
        clone_git(cfg, 'fetch', '--quiet', 'origin', f'refs/heads/{branch}:refs/remotes/origin/{branch}')
        snapshot = f'origin/{branch}'
        base = clone_git(cfg, 'merge-base', f'origin/{cfg.get("branch", "main")}', snapshot)
        code, patch, err = clone_git(cfg, 'diff', '--binary', base, snapshot, check=False)
        if code:
            raise Failed(f'diff of `{branch}` failed: {err.strip()[-200:]}')
        if not patch.strip():
            result['note'] = f'`{branch}` holds no change against main'
        else:
            code, _, err = run(['git', '-C', cfg['maintenance_repo'], 'apply', '--3way', '--index'], input=patch, check=False)
            if code:
                reset_clone(cfg)
                raise Failed(f'`{branch}` does not apply cleanly on main: {err.strip()[-200:]}')
            clone_git(cfg, 'commit', '--quiet', '-m', f'brain: land the rescued published-copy changes from {branch}')
            sha = push_clone(cfg)
            result['commits'] = [commit_url(cfg, sha)]
            journal(cfg, meta['run_id'], 'change', text=f'Landed rescued changes from `{branch}`', url=commit_url(cfg, sha), revert=f'git revert {sha[:12]}')
    clone_git(cfg, 'push', '--quiet', 'origin', '--delete', branch, timeout=60)
    result.setdefault('note', f'`{branch}` deleted')
    return result


def _run_action(cfg, meta, action, skill, issue, option, reply):
    kind = action.get('type', 'close')
    if kind == 'close':
        return {}
    if kind in ('rescue-land', 'rescue-discard'):
        return _rescue(cfg, meta, action['branch'], kind == 'rescue-land')
    if kind == 'command':
        argv = list(action['argv'])
        base = (SKILLS_DIR / action.get('skill', skill)).resolve()
        script = (base / argv[0]).resolve()
        if not script.is_relative_to(base):
            raise Failed(f'action script {argv[0]} is outside the {skill} skill')
        argv = ([cfg['python_bin']] if script.suffix == '.py' else []) + [script] + argv[1:]
        env = dict(step_env(cfg, meta), ATTENTION_ISSUE=issue['url'], ATTENTION_OPTION=str(option), ATTENTION_REPLY=reply)
        out = run(argv, cwd=base, env=env, timeout=cfg['timing']['action_timeout_seconds'])
        for line in reversed(out.splitlines()):
            with contextlib.suppress(json.JSONDecodeError):
                result = json.loads(line)
                if isinstance(result, dict):
                    return result
        return {}
    raise Failed(f'unknown action type {kind}')


def process_replies(cfg, meta):
    """Apply the owner's chosen option on each open needs-attention issue of this workflow."""
    for issue in open_attention(cfg, meta['workflow']):
        fingerprint = _parse_comment('fingerprint', issue['body'])
        if not isinstance(fingerprint, str):
            continue
        spec = _parse_comment('options', issue['body'])
        if not isinstance(spec, dict) and fingerprint.startswith('reconciler-rescue:'):
            spec = _rescue_options(fingerprint)
        if not isinstance(spec, dict):
            continue
        number = issue['number']
        comments = json.loads(gh(cfg, 'api', f'repos/{cfg["github_repo"]}/issues/{number}/comments', '--paginate') or '[]')
        last_ours = max((i for i, c in enumerate(comments) if MARKER in (c.get('body') or '')), default=-1)
        filer = (issue.get('author') or {}).get('login')
        replies = [c for c in comments[last_ours + 1:] if MARKER not in (c.get('body') or '')
                   and (c['user']['login'] == cfg['owner_github'] or (ANSWER in (c.get('body') or '') and c['user']['login'] == filer))]
        if not replies:
            continue
        reply = replies[-1]['body']
        option = parse_choice(reply, len(spec['options']))
        if option is None:
            gh(cfg, 'issue', 'comment', str(number), '--repo', cfg['github_repo'], '--body-file', '-',
               input=f'I could not read an option from that reply. Reply with the option number, for example `1`.\n\n{MARKER}')
            journal(cfg, meta['run_id'], 'note', text=f'No option read from the reply on <{issue["url"]}>')
            continue
        chosen = spec['options'][option - 1]
        try:
            result = _run_action(cfg, meta, chosen['action'], spec.get('skill', 'brain-routines'), issue, option, reply)
        except Failed as error:
            journal(cfg, meta['run_id'], 'problem', text=f'Option {option} on <{issue["url"]}> failed, retried next run: {error}')
            continue
        lines = [f'Applied option {option}: **{chosen["label"]}** (run `{meta["run_id"]}`).']
        if result.get('note'):
            lines.append(result['note'])
        lines += [f'- {url}' for url in result.get('commits', [])]
        gh(cfg, 'issue', 'comment', str(number), '--repo', cfg['github_repo'], '--body-file', '-', input='\n'.join(lines) + f'\n\n{MARKER}')
        gh(cfg, 'issue', 'close', str(number), '--repo', cfg['github_repo'], '--reason', 'completed')
        journal(cfg, meta['run_id'], 'resolved', url=issue['url'], title=issue['title'], option=option, label=chosen['label'],
                commits=result.get('commits', []))
