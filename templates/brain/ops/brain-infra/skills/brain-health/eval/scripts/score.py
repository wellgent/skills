#!/usr/bin/env python3
"""Score the retrieval eval set with `gbrain eval gate --qrels`, one gate call per case.

  score.py [--run <run_id>] [--set <qrels.json>] [--only q1,q2]

Each case runs as its own single-entry gate, so every case gets its own recall@10, top-1
hit and expected-top-1 hit; families, critical cases and drops are computed from those.
Inside a run (--run or ROUTINE_RUN_ID) it reads the set from the maintenance clone, records
the run in the eval history, pages #ops-alerts for a failed critical case or a family drop
beyond the noise band, journals the score and writes $ROUTINE_RUN_DIR/result.json.
Without a run it only prints the per-case results (a probe).
Prints a last-line JSON {"status", "summary", "counts"} for `routine.py end`.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True  # routines write nothing into the published copy
EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL.parents[1] / 'brain-routines' / 'scripts'))
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402

SET_REL = 'ops/brain-infra/skills/brain-health/eval/qrels.json'
K = 10
WORKERS = 4
RUNS_FOR_BAND = 4    # the noise band is measured over the first complete runs
BAND_FLOOR = 0.10    # a family must move by more than this before a drop alerts
METRICS = ('recall', 'hit1')
NAMES = {'recall': f'recall@{K}', 'hit1': 'top-1'}


def gate(case, workdir):
    """One case through the gate; returns its metrics or an error."""
    entry = {k: case[k] for k in ('query_id', 'query', 'relevant_slugs', 'first_relevant_slug') if k in case}
    path = Path(workdir) / f'{case["query_id"]}.json'
    path.write_text(json.dumps({'schema_version': 1, 'queries': [entry]}, ensure_ascii=False))
    try:
        code, out, err = lib.run(['gbrain', 'eval', 'gate', '--qrels', path, '--json', '-k', str(K)], timeout=180, check=False)
    except Failed as error:
        return {'error': str(error)}
    for line in out.splitlines():
        if line.startswith('{') and '"correctness_gate"' in line:
            gate_result = json.loads(line)['correctness_gate']
            summary = gate_result.get('summary')
            if not summary or summary.get('queries_errored'):
                breaches = gate_result.get('breaches') or [{}]
                return {'error': breaches[0].get('error_tail') or breaches[0].get('reason') or 'gate did not run'}
            result = {'recall': summary['mean_recall_at_k'], 'hit1': summary['first_relevant_hit_rate']}
            if summary.get('expected_top1_denominator'):
                result['top1'] = summary['expected_top1_hit_rate']
            return result
    return {'error': f'no gate result (exit {code}): {(err or out).strip()[-200:]}'}


def score_cases(cases):
    with tempfile.TemporaryDirectory(prefix='brain-eval-') as workdir:
        with ThreadPoolExecutor(WORKERS) as pool:
            results = list(pool.map(lambda c: gate(c, workdir), cases))
    return {c['query_id']: {**r, 'family': c['family'], 'critical': bool(c.get('critical'))} for c, r in zip(cases, results)}


def passed(r):
    """A case passes when its top result is a relevant page (the expected one, when set)."""
    return r.get('top1', r.get('hit1')) == 1


def aggregate(results, ids=None):
    """Mean of each metric per family and overall, over the given case ids."""
    rows = [r for q, r in results.items() if 'error' not in r and (ids is None or q in ids)]
    out = {}
    for key, group in [('all', rows)] + [(f, [r for r in rows if r['family'] == f]) for f in sorted({r['family'] for r in rows})]:
        if group:
            out[key] = {m: sum(r[m] for r in group) / len(group) for m in METRICS} | {'n': len(group)}
    return out


def gate_verdict(results):
    """The gate's own set-level verdict at its default floors."""
    rows = [r for r in results.values() if 'error' not in r]
    if not rows:
        return 'fail'
    top1 = [r['top1'] for r in rows if 'top1' in r]
    ok = (sum(r['recall'] for r in rows) / len(rows) >= 0.70 and sum(r['hit1'] for r in rows) / len(rows) >= 0.60
          and (not top1 or sum(top1) / len(top1) >= 0.50))
    return 'pass' if ok else 'fail'


# history and the noise band

def history_path(cfg):
    return lib.state_dir(cfg) / 'eval' / 'history.jsonl'


def read_history(cfg):
    path = history_path(cfg)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def noise_band(complete):
    """Per family and metric: the spread over the first complete runs, on the cases all of them share."""
    first = complete[:RUNS_FOR_BAND]
    if len(first) < RUNS_FOR_BAND:
        return None
    shared = set.intersection(*(set(h['results']) for h in first))
    band = {}
    for h in first:
        for family, metrics in aggregate(h['results'], shared).items():
            for m in METRICS:
                band.setdefault(family, {}).setdefault(m, []).append(metrics[m])
    return {f: {m: max(BAND_FLOOR, max(v) - min(v)) for m, v in ms.items()} for f, ms in band.items()}


def drops(previous, results, band):
    """Families whose score fell by more than their band since the previous complete run, on shared cases."""
    shared = set(previous['results']) & set(results)
    before, now = aggregate(previous['results'], shared), aggregate(results, shared)
    found = []
    for family, metrics in now.items():
        if family == 'all' or family not in before:
            continue
        for m in METRICS:
            limit = band.get(family, {}).get(m, BAND_FLOOR)
            if before[family][m] - metrics[m] > limit:
                found.append(f'{family} {NAMES[m]} {before[family][m]:.2f} to {metrics[m]:.2f} (band {limit:.2f})')
    return found


def load_set(path):
    data = json.loads(Path(path).read_text())
    return data, data['queries']


def fmt(metrics):
    return f'{NAMES["recall"]} {metrics["recall"]:.2f}, {NAMES["hit1"]} {metrics["hit1"]:.2f}'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--run', help='run id (default: ROUTINE_RUN_ID); without one the script only probes')
    p.add_argument('--set', help='qrels file (default: the maintenance clone in a run, else the one next to this script)')
    p.add_argument('--only', help='comma-separated case ids to score (a probe)')
    args = p.parse_args()
    cfg = lib.config()
    run_id = args.run or os.environ.get('ROUTINE_RUN_ID')
    meta = lib.current_run(cfg, run_id) if run_id and not args.only else None
    path = args.set or (Path(cfg['maintenance_repo']) / SET_REL if meta else EVAL / 'qrels.json')
    data, cases = load_set(path)
    if args.only:
        wanted = set(args.only.split(','))
        cases = [c for c in cases if c['query_id'] in wanted]
    repo = Path(cfg['maintenance_repo'] if meta else cfg['published_repo'])
    missing = sorted({s for c in cases for s in c['relevant_slugs'] if not (repo / f'{s}.md').is_file()})
    results = score_cases(cases)
    errored = {q: r['error'] for q, r in results.items() if 'error' in r}
    complete = not errored and not missing
    agg = aggregate(results)
    critical = [c for c in cases if c.get('critical')]
    critical_failed = [c for c in critical if 'error' not in results[c['query_id']] and not passed(results[c['query_id']])]
    misses = [c for c in cases if 'error' not in results[c['query_id']] and not passed(results[c['query_id']])]
    verdict = gate_verdict(results)
    overall = agg.get('all', {'recall': 0, 'hit1': 0, 'n': 0})
    summary = (f'set v{data.get("set_version")}, {len(cases)} cases: {fmt(overall)}; gate {verdict}; '
               f'critical {len(critical) - len(critical_failed)}/{len(critical)}' + ('' if complete else '; incomplete'))
    counts = {'cases': len(cases), 'misses': len(misses), 'errored': len(errored)}
    report = {'set_version': data.get('set_version'), 'gate': verdict, 'aggregate': agg, 'results': results,
              'errored': errored, 'missing_pages': missing}

    if not meta:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({'status': 'ok' if complete else 'partial', 'summary': summary, 'counts': counts}, ensure_ascii=False))
        return 0

    history = read_history(cfg)
    complete_runs = [h for h in history if h.get('complete')]
    band = noise_band(complete_runs)
    families = '; '.join(f'{f} {fmt(m)} (n={m["n"]})' for f, m in agg.items() if f != 'all')
    lib.journal(cfg, meta['run_id'], 'note', text=f'Families: {families}.')
    if misses:
        shown = ', '.join(f'{c["query_id"]} "{c["query"][:60]}"' for c in misses[:12])
        lib.journal(cfg, meta['run_id'], 'note', text=f'Misses at top-1 ({len(misses)}): {shown}' + (' ...' if len(misses) > 12 else '') + '.')
    if missing:
        lib.journal(cfg, meta['run_id'], 'problem', text='Eval cases point at pages that no longer exist: ' + ', '.join(missing) + '.')
    if errored:
        lib.journal(cfg, meta['run_id'], 'problem', text=f'{len(errored)} case(s) did not score: '
                    + '; '.join(f'{q}: {e[:120]}' for q, e in list(errored.items())[:5]) + '.')
    alerts = []
    for c in critical_failed:
        alerts.append(('critical:' + c['query_id'], f'critical case {c["query_id"]} "{c["query"]}" no longer returns '
                       f'`{c.get("first_relevant_slug") or c["relevant_slugs"][0]}` first'))
    if band is None:
        lib.journal(cfg, meta['run_id'], 'note', text=f'Noise band: {len(complete_runs) + complete}/{RUNS_FOR_BAND} complete runs measured; family drops alert from then on.')
    elif complete and complete_runs:
        for text in drops(complete_runs[-1], results, band):
            alerts.append(('drop:' + text.split(' ', 1)[0], f'family drop: {text}'))
    for fingerprint, text in alerts:
        lib.alert(cfg, f'{meta["routine"]}:{fingerprint}', f'{cfg["brain"]} retrieval eval: {text}.\nRun update in #brain-{meta["workflow"]}, run `{meta["run_id"]}`.')
        lib.journal(cfg, meta['run_id'], 'note', text=f'Alerted: {text}.')
    counts['alerts'] = len(alerts)
    entry = {'run_id': meta['run_id'], 'at': lib.iso(), 'set_version': data.get('set_version'), 'complete': complete,
             'gate': verdict, 'results': {q: {k: v for k, v in r.items() if k != 'error'} for q, r in results.items() if 'error' not in r}}
    path = history_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    band_now = band or noise_band(complete_runs + ([entry] if complete else []))
    if band_now:
        lib.atomic(lib.state_dir(cfg) / 'eval' / 'noise-band.json', band_now)
    lib.atomic(lib.run_dir(cfg, meta['run_id']) / 'eval-score.json', report)
    status = 'ok' if complete else 'partial'
    lib.atomic(lib.run_dir(cfg, meta['run_id']) / 'result.json', {'status': status, 'summary': summary, 'counts': counts})
    print(json.dumps({'status': status, 'summary': summary, 'counts': counts}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
