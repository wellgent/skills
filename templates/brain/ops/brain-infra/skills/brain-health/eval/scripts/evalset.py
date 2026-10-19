#!/usr/bin/env python3
"""The retrieval eval set and its candidates: validate, queue, build the packet, promote.

  evalset.py validate [--set <qrels.json>] [--repo <brain checkout>]
  evalset.py add --query <q> --expected <slug> [<slug> ...] --origin <url or run> [--family F] [--note N] [--run <run_id>]
  evalset.py packet [--run <run_id>]
  evalset.py promote <verdicts.json> [--run <run_id>]

add, packet and promote act inside a routine run (--run or ROUTINE_RUN_ID) on the maintenance
clone, and add and promote commit and push from it.

A promote verdict, one per candidate (a queued id like "c3", or an eval-candidate issue URL):

  {"candidate": "c3", "verdict": "accept", "query": "...", "relevant_slugs": ["people/x"],
   "first_relevant_slug": "people/x", "family": "title", "reason": "..."}
  {"candidate": "https://github.com/.../issues/9", "verdict": "reject", "reason": "..."}

Guards on an accepted candidate: the candidate is open, the query is non-empty and new to the
set, the family is known, every slug is a page in the brain, the first relevant slug is one of
the relevant slugs. Promoted cases are never critical. A candidate that fails a guard stays
open for the next run. Accepting any candidate makes a new set version.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True  # routines write nothing into the published copy
EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL.parents[1] / 'brain-routines' / 'scripts'))
import routinelib as lib  # noqa: E402
from routinelib import Failed  # noqa: E402

EVAL_REL = 'ops/brain-infra/skills/brain-health/eval'
FAMILIES = ('title', 'alias', 'generic', 'relational', 'negative')
LABEL = 'eval-candidate'


def norm(text):
    return ' '.join((text or '').lower().split())


def validate(data, repo):
    """Every problem with a set, as text; an empty list means valid."""
    problems = []
    if data.get('schema_version') != 1:
        problems.append('schema_version must be 1')
    if not isinstance(data.get('set_version'), int) or data['set_version'] < 1:
        problems.append('set_version must be a positive integer')
    cases = data.get('queries') or []
    if not cases:
        problems.append('the set has no cases')
    ids, texts = set(), set()
    for c in cases:
        qid = c.get('query_id', '?')
        if not re.fullmatch(r'q\d+', qid) or qid in ids:
            problems.append(f'{qid}: query_id must be a unique q<n>')
        ids.add(qid)
        if not (c.get('query') or '').strip() or norm(c.get('query')) in texts:
            problems.append(f'{qid}: query must be non-empty and unique')
        texts.add(norm(c.get('query')))
        if c.get('family') not in FAMILIES:
            problems.append(f'{qid}: family must be one of {", ".join(FAMILIES)}')
        slugs = c.get('relevant_slugs') or []
        if not slugs:
            problems.append(f'{qid}: relevant_slugs is empty')
        problems += [f'{qid}: {s} is not a page' for s in slugs if not (Path(repo) / f'{s}.md').is_file()]
        if c.get('first_relevant_slug') and c['first_relevant_slug'] not in slugs:
            problems.append(f'{qid}: first_relevant_slug is not among relevant_slugs')
        if not isinstance(c.get('critical', False), bool) or not isinstance(c.get('added_in'), int):
            problems.append(f'{qid}: critical must be a boolean and added_in an integer')
    return problems


# the maintenance clone

def clone_files(cfg):
    base = Path(cfg['maintenance_repo']) / EVAL_REL
    return base / 'qrels.json', base / 'candidates.json'


def load(path):
    return json.loads(Path(path).read_text())


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def commit_push(cfg, meta, subject, body):
    lib.clone_git(cfg, 'add', '--', EVAL_REL)
    lib.clone_git(cfg, 'commit', '--quiet', '-m', subject, '-m', '\n'.join([f'Routine: {meta["routine"]} ({meta["run_id"]})'] + body))
    sha = lib.push_clone(cfg)
    return lib.commit_url(cfg, sha), sha


def candidate_issues(cfg):
    raw = lib.gh(cfg, 'issue', 'list', '--repo', cfg['github_repo'], '--state', 'all', '--label', LABEL,
                 '--json', 'number,title,url,body,state,comments', '--limit', '100')
    return [{'url': i['url'], 'number': i['number'], 'title': i['title'], 'state': i['state'], 'body': i['body'],
             'comments': [c['body'] for c in i.get('comments', []) if lib.MARKER not in (c.get('body') or '')]}
            for i in json.loads(raw or '[]')]


# commands

def cmd_validate(args, cfg):
    path = Path(args.set or EVAL / 'qrels.json')
    repo = Path(args.repo or EVAL.parents[4])
    problems = validate(load(path), repo)
    print(json.dumps({'set': str(path), 'problems': problems}, ensure_ascii=False, indent=2))
    return 1 if problems else 0


def cmd_add(args, cfg):
    meta = lib.current_run(cfg, args.run)
    set_path, cand_path = clone_files(cfg)
    if lib.clone_git(cfg, 'status', '--porcelain').strip():
        raise Failed('the maintenance clone has uncommitted changes; queue the candidate between apply batches')
    missing = [s for s in args.expected if not (Path(cfg['maintenance_repo']) / f'{s}.md').is_file()]
    if missing:
        raise Failed('not brain pages: ' + ', '.join(missing))
    if args.family and args.family not in FAMILIES:
        raise Failed(f'family must be one of {", ".join(FAMILIES)}')
    queue = load(cand_path)
    known = {norm(c['query']) for c in load(set_path)['queries']} | {norm(c['query']) for c in queue['candidates']}
    if norm(args.query) in known:
        print(json.dumps({'note': f'"{args.query}" is already in the eval set or its candidates'}))
        return 0
    cid = f'c{queue["next_id"]}'
    queue['next_id'] += 1
    queue['candidates'].append({'id': cid, 'query': args.query, 'expected': args.expected, 'family': args.family,
                                'origin': args.origin, 'note': args.note, 'added_at': lib.iso(), 'added_by': meta['run_id']})
    save(cand_path, queue)
    url, _ = commit_push(cfg, meta, f'setup: retrieval eval candidate {cid} from {meta["routine"]}',
                         [f'Query: {args.query}', f'Expected: {", ".join(args.expected)}', f'Origin: {args.origin}'])
    lib.journal(cfg, meta['run_id'], 'change', text=f'Queued retrieval eval candidate {cid}: "{args.query}"', url=url)
    print(json.dumps({'note': f'queued eval candidate {cid}', 'commits': [url]}))
    return 0


def cmd_packet(args, cfg):
    lib.current_run(cfg, args.run)
    set_path, cand_path = clone_files(cfg)
    data = load(set_path)
    packet = {
        'set_version': data['set_version'], 'families': FAMILIES,
        'cases': [{k: c.get(k) for k in ('query_id', 'query', 'family', 'relevant_slugs')} for c in data['queries']],
        'candidates': load(cand_path)['candidates'],
        'issues': candidate_issues(cfg),
    }
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


def cmd_promote(args, cfg):
    meta = lib.current_run(cfg, args.run)
    raw = json.loads(Path(args.verdicts).read_text())
    verdicts = raw['verdicts'] if isinstance(raw, dict) else raw
    lib.reset_clone(cfg)
    set_path, cand_path = clone_files(cfg)
    data, queue = load(set_path), load(cand_path)
    repo = Path(cfg['maintenance_repo'])
    queued = {c['id']: c for c in queue['candidates']}
    issues = {i['url']: i for i in candidate_issues(cfg)}
    texts = {norm(c['query']) for c in data['queries']}
    version = data['set_version'] + 1
    next_q = max(int(c['query_id'][1:]) for c in data['queries']) + 1
    promoted, rejected, held = [], [], []
    for v in verdicts:
        key = v.get('candidate')
        origin = queued[key]['origin'] if key in queued else key
        try:
            if key not in queued and key not in issues:
                raise ValueError('not an open candidate')
            if key in {k for k, _ in promoted + rejected}:
                raise ValueError('a second verdict for the same candidate')
            if v.get('verdict') == 'reject':
                if not v.get('reason'):
                    raise ValueError('a rejection needs a reason')
                rejected.append((key, v['reason']))
            elif v.get('verdict') == 'accept':
                query = ' '.join((v.get('query') or '').split())
                slugs = v.get('relevant_slugs') or []
                if not query or norm(query) in texts:
                    raise ValueError('the query is empty or already in the set')
                if v.get('family') not in FAMILIES:
                    raise ValueError(f'family must be one of {", ".join(FAMILIES)}')
                missing = [s for s in slugs if not (repo / f'{s}.md').is_file()]
                if not slugs or missing:
                    raise ValueError('not brain pages: ' + (', '.join(missing) or 'none given'))
                if v.get('first_relevant_slug') and v['first_relevant_slug'] not in slugs:
                    raise ValueError('first_relevant_slug is not among relevant_slugs')
                case = {'query_id': f'q{next_q}', 'query': query, 'family': v['family'], 'relevant_slugs': slugs}
                if v.get('first_relevant_slug'):
                    case['first_relevant_slug'] = v['first_relevant_slug']
                case.update(origin=origin, added_in=version)
                data['queries'].append(case)
                texts.add(norm(query))
                next_q += 1
                promoted.append((key, case))
            else:
                raise ValueError('verdict must be accept or reject')
        except ValueError as error:
            held.append((key, str(error)))
    result = {'promoted': [c['query_id'] for _, c in promoted], 'rejected': [k for k, _ in rejected], 'held': held}
    for key, reason in held:
        lib.journal(cfg, meta['run_id'], 'note', text=f'Eval candidate {key} stays open: {reason}.')
    if not promoted and not rejected:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if promoted:
        data['set_version'] = version
        problems = validate(data, repo)
        if problems:
            raise Failed('the promoted set does not validate: ' + '; '.join(problems[:5]))
        save(set_path, data)
    settled = {k for k, _ in promoted + rejected}
    queue['candidates'] = [c for c in queue['candidates'] if c['id'] not in settled]
    save(cand_path, queue)
    subject = (f'setup: retrieval eval set v{version} takes {len(promoted)} case(s) from its candidates' if promoted
               else f'setup: retrieval eval candidates, {len(rejected)} rejected')
    body = [f'Promoted {c["query_id"]}: "{c["query"]}" from {c["origin"]}' for _, c in promoted]
    body += [f'Rejected {k}: {r}' for k, r in rejected]
    url, _ = commit_push(cfg, meta, subject, body)
    result['commit'] = url
    for _, c in promoted:
        lib.journal(cfg, meta['run_id'], 'change', text=f'Eval set v{version}: {c["query_id"]} "{c["query"]}" ({c["family"]}) from {c["origin"]}', url=url)
    for key, reason in rejected:
        lib.journal(cfg, meta['run_id'], 'note', text=f'Eval candidate {key} rejected: {reason}.')
    answers = [(k, f'Taken into the retrieval eval set v{version} as `{c["query_id"]}`: "{c["query"]}" -> '
                + ', '.join(f'`{s}`' for s in c['relevant_slugs']) + f' ({url}).') for k, c in promoted]
    answers += [(k, f'Not taken into the retrieval eval set: {r}') for k, r in rejected]
    for key, text in answers:
        if key not in issues:
            continue
        issue = issues[key]
        lib.gh(cfg, 'issue', 'comment', str(issue['number']), '--repo', cfg['github_repo'], '--body-file', '-',
               input=f'{text}\n\n{lib.MARKER}')
        lib.gh(cfg, 'issue', 'edit', str(issue['number']), '--repo', cfg['github_repo'], '--remove-label', LABEL)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('validate', help='check a set: ids, families, slugs, versions')
    c.add_argument('--set')
    c.add_argument('--repo', help='brain checkout the slugs resolve in (default: the one holding this script)')
    c = sub.add_parser('add', help='queue a candidate case (inside a routine run)')
    c.add_argument('--query', required=True)
    c.add_argument('--expected', nargs='+', required=True, help='the brain page slugs the query should return')
    c.add_argument('--origin', required=True, help='where the miss came from: an issue URL, a run id, a commit')
    c.add_argument('--family', choices=FAMILIES)
    c.add_argument('--note', default='')
    c.add_argument('--run')
    c = sub.add_parser('packet', help='print the set, queued candidates and eval-candidate issues for the weekly turn')
    c.add_argument('--run')
    c = sub.add_parser('promote', help='apply the weekly turn verdicts on the candidates')
    c.add_argument('verdicts')
    c.add_argument('--run')
    args = p.parse_args()
    cfg = lib.config()
    return {'validate': cmd_validate, 'add': cmd_add, 'packet': cmd_packet, 'promote': cmd_promote}[args.command](args, cfg)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Failed as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
