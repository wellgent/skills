# Retrieval eval

A fixed set of real lookups, each with the brain pages a good search returns, scored weekly through `gbrain eval gate --qrels` to prove search still finds what agents ask for.
The set grows from real misses: a case enters only after the weekly turn verifies it.

## Files

- `qrels.json` - the set, in the gate's qrels shape (`schema_version` 1, `queries`), plus `set_version` and optional `local_families`.
  Each case: `query_id` (`q<n>`), `query`, `family`, `relevant_slugs` (brain paths without `.md`), optional `first_relevant_slug` (the page that must rank first), optional `critical`, `origin` (where the lookup came from), `added_in` (the set version that took it).
- `candidates.json` - the queue of cases waiting for verification, with `next_id`.
- `scripts/score.py` - scores the set; `scripts/evalset.py` - validates, queues, builds the packet and promotes.

Every slug in `relevant_slugs` is a **hard keep** for the relevance routine.

## Families

- `title` - the query names the page's subject by its title or obvious name.
- `alias` - the query uses another name: alias, slug, handle, short form, spelling variant.
- `generic` - the query describes the subject without naming it.
- `relational` - the answer lives on a page connected to the thing the query names.
- `negative` - a near-namesake or broader page competes, and the expected page must still rank first.

A brain adds families of its own in the set's `local_families`, each name mapped to its meaning; they are scored, alerted and promoted like the five above.

## Scoring

`score.py` runs each case as its own single-entry gate at k=10, so every case gets recall@10, a top-1 hit and, with `first_relevant_slug`, an expected-top-1 hit.
A case **passes** when its top result is the expected page, or any relevant page when none is expected.
The run record carries the set-level score with the gate's own verdict, the score per family and the cases that miss at top-1.

Alerts to `#ops-alerts`, once per fingerprint a day:

- a **critical** case fails;
- the run is **incomplete**: a case did not score, or a case points at a page that no longer exists (the run is partial);
- a **family drop**: a family's recall@10 or top-1 falls by more than its noise band since the previous complete run, on the cases both runs share.
  The band is the spread of each family score over the first four complete runs, at least 0.10; family drops alert once those four runs exist.

History lives on the host in `<state_dir>/eval/history.jsonl`, the band in `<state_dir>/eval/noise-band.json`.
`score.py` with no run is a probe: it prints every case's result and touches nothing.

## Candidates

A candidate is a real lookup that missed, with the pages it should have found.
They come in two ways:

- **A routine run** queues one: `evalset.py add --query "<q>" --expected <slug> [...] --origin <run id or URL> [--family F] [--note N]`, between apply batches, from any workflow's run, for example a miss the daily alignment finds.
- **An issue labelled `eval-candidate`**: any needs-attention item or issue about a failed lookup, from a routine, an agent or the owner. The weekly turn reads the lookup and the expected page from the issue.

## The `health-eval` routine

A weekly agentTurn, at its slot in the routine manifest. This session is the fresh session that verifies candidates: it judges each one on the pages themselves, never on the word of whoever queued it.

1. `routine.py begin health-eval`; keep the run id.
2. `python3 eval/scripts/evalset.py packet --run <run_id>` prints the set, the queued candidates and the `eval-candidate` issues.
   With no candidates and no issues, go to step 5.
3. Verify each candidate, one verdict each:
   - run the lookup with `gbrain search` and `gbrain query`, and read every expected page with `gbrain get`;
   - **accept** when the pages answer the lookup and are the pages a good search should return, adding any equally essential page; prefer durable pages over `research/`, `meetings/`, `tasks/`, `finance/` and `sources/`;
   - phrase the query as the real lookup, with personal or sensitive detail replaced by a neutral paraphrase that tests the same retrieval;
   - choose the family, and set `first_relevant_slug` when one page clearly must rank first;
   - **reject** with a reason when the pages do not answer it, the lookup duplicates a case, or the expected answer is not in the brain.
4. Write the verdicts to `<run_dir>/eval-verdicts.json` in the shape in `evalset.py`'s docstring and run `python3 eval/scripts/evalset.py promote <run_dir>/eval-verdicts.json --run <run_id>`.
   Accepted cases become a new set version, committed from the maintenance clone; issue candidates get a comment and lose their label.
5. `python3 eval/scripts/score.py --run <run_id>` scores the set from the maintenance clone, journals the score and pages the alerts.
   Its last line is `{"status", "summary", "counts"}`.
6. `routine.py end <run_id>` with that status, summary and counts, then end the turn with `NO_REPLY`.

Paths in the steps are relative to the `brain-health` skill directory.
