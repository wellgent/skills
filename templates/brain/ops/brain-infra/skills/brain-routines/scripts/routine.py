#!/usr/bin/env python3
"""Brain routine runner: run a routine under the maintenance lease, post its run update,
page partial runs, and register the routine manifest as the main agent's crons."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True  # routines write nothing into the published copy
import routinelib as lib  # noqa: E402
from routinelib import Failed

SCRIPT = Path(__file__).resolve()


def duration(seconds):
    seconds = int(seconds)
    return f'{seconds // 60}m {seconds % 60:02d}s' if seconds >= 60 else f'{seconds}s'


# run lifecycle

def begin(cfg, rid, pid=None):
    """Take the lease, reset the maintenance clone, apply owner replies; return the run meta."""
    r = lib.routine(cfg, rid)
    run_id = f'{rid}-{lib.stamp()}-{os.urandom(2).hex()}'
    ttl = r.get('timeout_seconds', cfg['timing']['default_timeout_seconds']) + 300
    stale = lib.acquire_lease(cfg, run_id, rid, ttl, pid)
    meta = {'run_id': run_id, 'routine': rid, 'workflow': r['workflow'], 'skill': r['skill'], 'kind': r['kind'],
            'started_at': lib.now(), 'repo': cfg['maintenance_repo']}
    lib.run_dir(cfg, run_id).mkdir(parents=True, exist_ok=True, mode=0o700)
    lib.atomic(lib.run_dir(cfg, run_id) / 'run.json', meta)
    routine_state(cfg, rid, last_run_id=run_id, started_at=lib.iso(), running=True)
    if stale:
        lib.journal(cfg, run_id, 'note', text=f'Took over the lease of `{stale["run_id"]}`, which did not finish.')
    try:
        wiped = lib.reset_clone(cfg)
        if wiped:
            lib.journal(cfg, run_id, 'note', text='Wiped leftovers in the maintenance clone: ' + ', '.join(wiped) + '.')
        lib.process_replies(cfg, meta)
    except Failed as error:
        lib.journal(cfg, run_id, 'problem', text=f'Run start: {error}')
    return meta


def end(cfg, meta, status, summary='', counts=None, detail=''):
    """Post the run update, page a partial run, write the heartbeat and release the lease."""
    rid, run_id = meta['routine'], meta['run_id']
    entries = lib.read_journal(cfg, run_id)
    if status == 'ok' and any(e['kind'] == 'problem' for e in entries):
        status = 'partial'
    state = lib.load_state(cfg)
    failures = state.pop('send_failures', [])
    failures += failure_alert_misses(cfg, rid, state)
    lib.save_state(cfg, state)
    took = lib.now() - meta['started_at']
    text = run_update(meta, status, took, summary, counts or {}, entries, failures, detail)
    error = lib.post(cfg, cfg['channels'][meta['workflow']], text)
    if error:
        state = lib.load_state(cfg)
        state.setdefault('send_failures', []).extend(failures + [{'at': lib.iso(), 'target': meta['workflow'], 'error': error}])
        lib.save_state(cfg, state)
    if status == 'partial' or (status == 'failed' and meta['kind'] == 'agentTurn'):
        # A failed command job exits non-zero, and the cron failureAlert pages for it.
        lib.alert(cfg, f'routine:{rid}:{status}', f'{cfg["brain"]} routine `{rid}` {status}: {summary or "see its run update"}\n'
                  f'Run update in #brain-{meta["workflow"]}, run `{run_id}`.')
    routine_state(cfg, rid, finished_at=lib.iso(), status=status, seconds=round(took, 1), running=False,
                  heartbeat_at=lib.iso(), update_error=error)
    lib.atomic(lib.run_dir(cfg, run_id) / 'run.json', {**meta, 'status': status, 'summary': summary, 'finished_at': lib.now()})
    heartbeat = lib.state_dir(cfg) / 'heartbeats' / rid
    heartbeat.parent.mkdir(exist_ok=True)
    heartbeat.write_text(lib.iso() + '\n')
    lib.release_lease(cfg, run_id)
    prune_runs(cfg)


def run_update(meta, status, took, summary, counts, entries, failures, detail):
    head = f'**{meta["routine"]}** {status} in {duration(took)}' + (f': {summary}' if summary else '')
    changes = [e for e in entries if e['kind'] == 'change']
    attention = [e for e in entries if e['kind'] == 'attention']
    resolved = [e for e in entries if e['kind'] == 'resolved']
    notes = [e for e in entries if e['kind'] in ('note', 'problem')]
    silent = ', '.join(f'{k} {v}' for k, v in counts.items() if v)
    lines = [head]
    if silent:
        lines.append(f'Silent: {silent}')
    if changes:
        lines.append(f'Changes ({len(changes)}):')
        for c in changes:
            lines.append(f'- {c["text"]}' + (f' <{c["url"]}>' if c.get('url') else '') + (f' revert: `{c["revert"]}`' if c.get('revert') else ''))
    if resolved:
        lines.append('Needs attention resolved:')
        lines += [f'- option {e["option"]} ({e["label"]}) on {e["title"]} <{e["url"]}>' for e in resolved]
    if attention:
        lines.append('Needs attention:')
        lines += [f'- {e["title"]} <{e["url"]}>' + ('' if e.get('new') else ' (still open)') for e in attention]
    if notes:
        lines += [f'{"Problem" if e["kind"] == "problem" else "Note"}: {e["text"]}' for e in notes]
    if failures:
        lines.append('Alert sends that failed:')
        lines += [f'- {f["at"]} to {f["target"]}: {f["error"][:200]}' for f in failures]
    if detail:
        lines.append(detail.strip()[-600:])
    if len(lines) == 1 and status == 'ok':
        lines[0] += ', no changes.'
    return '\n'.join(lines)


def routine_state(cfg, rid, **fields):
    path = lib.state_dir(cfg) / 'routines' / f'{rid}.json'
    current = lib.read_json(path, {})
    current.update(fields)
    lib.atomic(path, current)


def failure_alert_misses(cfg, rid, state):
    """Cron failure alerts OpenClaw could not deliver, reported once each."""
    job = find_jobs(cfg).get(declaration_key(cfg, rid))
    if not job:
        return []
    st = job.get('state', {})
    status = st.get('lastFailureNotificationDeliveryStatus')
    seen = state.setdefault('failure_alert_seen', {})
    if status in ('not-delivered', 'unknown') and seen.get(rid) != st.get('lastRunAtMs'):
        seen[rid] = st.get('lastRunAtMs')
        return [{'at': lib.iso((st.get('lastRunAtMs') or 0) / 1000), 'target': 'ops-alerts (cron failureAlert)',
                 'error': st.get('lastFailureNotificationDeliveryError') or status}]
    return []


def prune_runs(cfg):
    cutoff = lib.now() - cfg['timing']['run_retention_days'] * lib.DAY
    for d in (lib.state_dir(cfg) / 'runs').glob('*'):
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)


def cmd_run(cfg, rid):
    """A command job: begin, run the routine's step, end. Exit 1 on a failed run."""
    r = lib.routine(cfg, rid)
    if r['kind'] != 'command':
        raise Failed(f'{rid} is an agentTurn routine; its agent calls begin and end')
    meta = begin(cfg, rid, pid=os.getpid())
    status, summary, counts, detail = 'failed', '', {}, ''
    try:
        argv = list(r['run'])
        script = lib.SKILLS_DIR / r['skill'] / argv[0]
        argv = ([cfg['python_bin']] if script.suffix == '.py' else []) + [script] + argv[1:]
        timeout = r.get('timeout_seconds', cfg['timing']['default_timeout_seconds']) - 60
        env = lib.step_env(cfg, meta)
        if r.get('sync_lock'):
            with lib.sync_lock(cfg):
                code, out, err = lib.run(argv, cwd=script.parent, env=env, timeout=timeout, check=False)
        else:
            code, out, err = lib.run(argv, cwd=script.parent, env=env, timeout=timeout, check=False)
        result = lib.read_json(lib.run_dir(cfg, meta['run_id']) / 'result.json', {})
        summary, counts = result.get('summary', ''), result.get('counts', {})
        status = result.get('status', 'ok') if code == 0 else 'failed'
        if code:
            detail = f'Exit {code}:\n```\n{(err or out).strip()[-500:]}\n```'
    except Failed as error:
        detail = str(error)
    finally:
        end(cfg, meta, status, summary, counts, detail)
    return 1 if status == 'failed' else 0


# the manifest as crons

def declaration_key(cfg, rid):
    return f'{cfg["brain"]}-routine-{rid}'


def find_jobs(cfg):
    o = cfg['openclaw']
    try:
        raw = lib.run([o['bin'], 'cron', 'list', '--all', '--json'], timeout=90)
    except Failed:
        return {}
    return {j['declarationKey']: j for j in json.loads(raw).get('jobs', []) if j.get('declarationKey')}


def desired(cfg, m, r):
    o = cfg['openclaw']
    timeout = r.get('timeout_seconds', cfg['timing']['default_timeout_seconds'])
    spec = {
        'name': f'{cfg["brain"]} {r["workflow"]}: {r["id"]}', 'agentId': o['agent'], 'enabled': r.get('enabled', True),
        'schedule': {'expr': r['schedule'], 'tz': m['timezone']},
        'delivery': 'none',
        'failureAlert': {'after': 1, 'to': 'channel:' + cfg['channels']['ops-alerts'], 'accountId': o['account'], 'cooldownMs': lib.DAY * 1000},
    }
    if r['kind'] == 'command':
        spec['payload'] = {'kind': 'command', 'argv': [cfg['python_bin'], str(SCRIPT), 'run', r['id']],
                           'cwd': str(lib.state_dir(cfg)), 'timeoutSeconds': timeout}
    else:
        skill_md = lib.SKILLS_DIR / r['skill'] / 'SKILL.md'
        spec['payload'] = {'kind': 'agentTurn', 'model': r['model'], 'thinking': r.get('thinking', 'high'), 'timeoutSeconds': timeout,
                           'message': f'Run the {cfg["brain"]} routine `{r["id"]}`: read {skill_md} and follow its `{r["id"]}` routine. '
                                      f'Start with `{cfg["python_bin"]} {SCRIPT} begin {r["id"]}` and finish with its `end` command; '
                                      'the run update is the only output, so end the turn with NO_REPLY.'}
    return spec


def actual(job):
    p = job.get('payload', {})
    payload = {'kind': p.get('kind')}
    keys = ('argv', 'cwd', 'timeoutSeconds') if p.get('kind') == 'command' else ('model', 'thinking', 'timeoutSeconds', 'message')
    payload.update({k: p.get(k) for k in keys})
    fa = job.get('failureAlert') or {}
    return {
        'name': job.get('name'), 'agentId': job.get('agentId'), 'enabled': job.get('enabled'),
        'schedule': {'expr': job.get('schedule', {}).get('expr'), 'tz': job.get('schedule', {}).get('tz')},
        'delivery': job.get('delivery', {}).get('mode'),
        'failureAlert': {k: fa.get(k) for k in ('after', 'to', 'accountId', 'cooldownMs')},
        'payload': payload,
    }


def register(cfg, rid, spec):
    o = cfg['openclaw']
    p = spec['payload']
    argv = [o['bin'], 'cron', 'add', '--name', spec['name'], '--declaration-key', declaration_key(cfg, rid),
            '--agent', spec['agentId'], '--cron', spec['schedule']['expr'], '--tz', spec['schedule']['tz'], '--exact',
            '--session', 'isolated', '--no-deliver', '--timeout-seconds', str(p['timeoutSeconds'])]
    if not spec['enabled']:
        argv.append('--disabled')
    if p['kind'] == 'command':
        argv += ['--command-argv', json.dumps(p['argv']), '--command-cwd', p['cwd'], '--no-output-timeout-seconds', str(p['timeoutSeconds'])]
    else:
        argv += ['--message', p['message'], '--model', p['model'], '--thinking', p['thinking']]
    job = json.loads(lib.run(argv, timeout=90))['job']
    fa = spec['failureAlert']
    lib.run([o['bin'], 'cron', 'edit', job['id'], '--failure-alert', '--failure-alert-after', str(fa['after']),
             '--failure-alert-channel', 'discord', '--failure-alert-to', fa['to'], '--failure-alert-mode', 'announce',
             '--failure-alert-account-id', fa['accountId'], '--failure-alert-cooldown', f'{fa["cooldownMs"] // 3600000}h'], timeout=90)


def cmd_sync(cfg, check):
    """Make the main agent's crons match the manifest; with --check, only report drift."""
    if not SCRIPT.is_relative_to(Path(cfg['published_repo']).resolve()):
        raise Failed(f'run sync from the published copy {cfg["published_repo"]}: the crons point at its scripts')
    m = lib.manifest(cfg)
    jobs = {k: j for k, j in find_jobs(cfg).items() if k.startswith(declaration_key(cfg, ''))}
    report = []
    o = cfg['openclaw']
    for r in m['routines']:
        key = declaration_key(cfg, r['id'])
        want = desired(cfg, m, r)
        job = jobs.pop(key, None)
        link = Path(o['workspace_skills']) / r['skill']
        if not (link.is_symlink() and link.resolve() == (lib.SKILLS_DIR / r['skill']).resolve()):
            report.append({'routine': r['id'], 'drift': f'workspace skill link {link} missing or wrong'})
            if not check:
                if link.is_symlink():
                    link.unlink()
                link.symlink_to(lib.SKILLS_DIR / r['skill'])
        if job and actual(job) == want:
            continue
        diff = 'missing' if not job else ', '.join(k for k in want if actual(job).get(k) != want[k])
        report.append({'routine': r['id'], 'drift': f'cron {diff}'})
        if not check:
            if job:
                lib.run([o['bin'], 'cron', 'rm', job['id']], timeout=90)
            register(cfg, r['id'], want)
    for key, job in jobs.items():
        report.append({'routine': key, 'drift': 'cron not in the manifest'})
        if not check:
            lib.run([o['bin'], 'cron', 'rm', job['id']], timeout=90)
    print(json.dumps({'checked': len(m['routines']), 'drift' if check else 'changed': report}, ensure_ascii=False, indent=2))
    return 1 if check and report else 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('run', help='run a command routine (the cron entry point)')
    c.add_argument('routine')
    c = sub.add_parser('begin', help='start an agentTurn routine run; prints the run meta')
    c.add_argument('routine')
    c = sub.add_parser('end', help='finish an agentTurn routine run')
    c.add_argument('run_id')
    c.add_argument('--status', choices=('ok', 'partial', 'failed'), required=True)
    c.add_argument('--summary', default='')
    c.add_argument('--counts', default='{}', help='silent-tier counts as a JSON object')
    c = sub.add_parser('sync', help='register the routine manifest as crons')
    c.add_argument('--check', action='store_true', help='report drift without changing anything')
    c = sub.add_parser('status', help='print the lease and each routine state')
    args = p.parse_args()
    cfg = lib.config()
    if args.command == 'run':
        return cmd_run(cfg, args.routine)
    if args.command == 'begin':
        meta = begin(cfg, args.routine)
        print(json.dumps({**meta, 'run_dir': str(lib.run_dir(cfg, meta['run_id']))}, indent=2))
        return 0
    if args.command == 'end':
        meta = lib.read_json(lib.run_dir(cfg, args.run_id) / 'run.json')
        if not meta:
            raise Failed(f'unknown run {args.run_id}')
        end(cfg, meta, args.status, args.summary, json.loads(args.counts))
        return 0
    if args.command == 'sync':
        return cmd_sync(cfg, args.check)
    sd = lib.state_dir(cfg)
    print(json.dumps({'lease': lib.read_json(sd / 'lease.json'),
                      'routines': {f.stem: lib.read_json(f) for f in sorted((sd / 'routines').glob('*.json'))}}, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
