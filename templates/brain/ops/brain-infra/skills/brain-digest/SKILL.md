---
name: brain-digest
description: "The daily digest in #brain-review: what needs {{owner}}, what the maintenance system changed in plain sentences, the answers it applied and a health line only when something is off, with Monday's run as the weekly edition. Also how {{owner}}'s answers to it are recorded. Use when running the digest-daily routine, answering a #brain-review reply or follow-up, or changing what the digest reports."
---

# Brain Digest

The **digest** workflow is the one place maintenance talks to {{owner}}: a morning post in `#brain-review`, after the last morning routine, only on days with something to report.
Its routine `digest-daily` is an agentTurn of the main agent on the `brain-routines` framework.
The other routines post nothing; their results stay in the run records on the host, and their problems page `#ops-alerts`.
Code states every fact: `scripts/digest.py` gathers the window with zero LLM calls and renders the post.
The agent writes only the plain sentences, which the code checks against the commits and issues.
The digest writes nothing to the brain.

## The `digest-daily` routine

Run every command with the paths below; `S` is `{{host_home}}/{{name}}/ops/brain-infra/skills`.

1. **Begin.** `python3 $S/brain-routines/scripts/routine.py begin digest-daily` prints the run id.
2. **Gather.** `python3 $S/brain-digest/scripts/digest.py gather --run <run_id>` writes the packet and prints its path, the `narrative_file`, the `edition` and `news`.
   When `news` is false, run the printed `next` command (`post --quiet`), which ends the run without a post, and end the turn with `NO_REPLY`.
3. **Write the narrative** from the packet into `narrative_file`, by the contract below.
4. **Check.** `digest.py post --run <run_id> --dry-run` prints the rendered digest, or `{"errors": [...]}`. Fix every error and rerun until it renders.
   When the narrative still fails after three attempts, use `post --fallback`, which renders the sentences from the facts.
5. **Post.** `digest.py post --run <run_id>` posts the digest to `#brain-review` and ends the run.
6. End the turn with `NO_REPLY`; the digest is the only output.

## The narrative

`narrative_file` is one JSON object:

```json
{"needs_you": {"<issue number>": "<sentence>"}, "changed": [{"text": "<sentence>", "commits": ["<sha>", "..."], "link": "<sha>"}], "done": {"<issue number>": "<sentence>"}, "health": "<sentence or empty>"}
```

- **needs_you**: one sentence per item in the packet's `needs_you`, from its `finding`, saying what {{owner}} is asked to decide. The render adds the recommended option and the issue link.
- **changed**: the window's changes grouped into items by what they did and why, from each commit's `title`, `kind`, `subject` and `reason`: "Moved four people whose engagements ended to the archive", followed by their names, never one item per commit. Name pages by their title and say why. Each item lists every commit it covers in `commits`, and every commit in the packet belongs to an item; `link` is the commit whose page the item links to. Changes from {{owner}}'s answers (`owner_choice`) read as {{owner}}'s choices.
- **done**: one sentence per applied answer in the packet's `done`, saying what now happened because of it. The weekly edition renders Done itself, as one line, and takes no `done` sentences.
- **health**: one sentence when the packet's `health` lists anything, on what went wrong and what it means for the brain; empty otherwise.
- Write plain sentences: no counts, timings or internal check names unless they are the news, and no raw URLs, commit ids, file paths, markup or revert instructions. The check refuses them.
- Keep within the packet's `limits`: `gist_chars` per needs_you and done sentence, `item_chars` per changed item, at most `items` changed items, and `health_chars`. On the weekly edition the code sets them so that a narrative within them fits on one screen.
{{local}}

## What the digest reports

1. **Needs you**: the open `needs-attention` issues, oldest first, numbered, each with its sentence, the recommended option parsed from the issue and the issue link, then how to reply. A daily digest lists only the items new in its window and puts the older open ones on one line of issue links; the weekly edition lists every open item.
2. **Changed**: the maintenance writer's commits in the window, and changes routines recorded in other repositories (the agent workspace, the shared core), one link per item to the page on the main branch, or to its last version for a deleted page.
3. **Done**: the answers the workflows applied in the window; on the weekly edition one line with their count and issue numbers.
4. **Health**: one line, only when a routine run failed, ran partly or was deferred in the window, or an alert could not be sent. The weekly edition names a routine only while its last run in the week has not ended ok.

The window runs from the start of the last digest run that ended ok, at most `max_window_days` back, and `first_window_hours` for the first run.
A daily digest posts when the window has a change, an applied answer, a new needs-attention item or a health fact; otherwise the run ends quietly. An item that only stays open is no news.

**The weekly edition** is Monday's run (`weekly_day`), over the 7 days before it starts, and it always posts.
It carries the same sections over the week, at most `items_weekly` change items, and fits on one screen: `screen_chars` of visible text, where a link counts by its text. It adds **Watch** lines that the code writes only when they move:

- the GBrain version: this brain's engine against upstream's latest stable release, from `gbrain check-update --json` on the host, shown when it is `engine_far_releases` releases behind or the range holds a security fix, with the security fixes and new default-on features in the range named; the packet's `watch_facts` keeps the numbers and why a quiet line stayed quiet. Upgrades stay manual, through the GBrain lane;
- search quality: the weekly search check did not run, failed, or moved by `eval_move` or more;
- subscription use within `window_near_points` of the `brain-routines` deferral threshold;
- pages per area, ledger areas included, for an area that moved by `area_change_pages` pages and `area_change_share` of its size.

A data source that cannot be read becomes a line under the header and a journal problem, so the run ends partial and pages `#ops-alerts`.

## Replies

The digest is a regular post, and {{owner}} replies in the channel, or settles items in a chat session with the agent.
Either way the agent records the answer on the issue, and the owning workflow's next run applies it and lists it under Done in the next digest.

- **Record an answer.** `digest.py answer --item <n> --reply "<the reply>" --who {{owner}} --where "#brain-review"` records it for item `n` of the last posted digest; `--issue <number>` names the issue directly, for example in a chat or for an issue on the still-open line. "yes", "ok" and their kin take the recommended option, and a number or "option N" takes that option.
  Record only {{owner}}'s own answers. When the command prints `"error"`, ask {{owner}} which option is meant.
- **Follow-up questions.** `digest.py items` prints the last digest's items with their issues, findings and options, and the path of the posted text; answer from those, the issue and the run records.
- The answer is a comment on the issue in the framework's answer format, which the reply loop reads like a reply on the issue itself.

## Operating

- Force a run with `routine.py force digest-daily`. A forced run posts like a scheduled one.
- `digest.py edition weekly` makes the next run the weekly edition, and `edition daily` a daily one.
- `digest.py preview --edition weekly` prints the weekly edition a run starting now would post, in the sentences built from the facts, and its `watch_facts` and data problems on stderr. It posts nothing and keeps no digest state.
- `<state_dir>/digest/state.json` holds the window start and the last digest's numbered items; each run directory keeps `packet.json`, `narrative.json` and the posted `digest.md`.
- Areas, ledger areas, windows, watch thresholds and narrative limits (`min_sentence_chars` is the floor the weekly share never goes under) are in `config.json`; schedule, model and effort are in `ops/brain-infra/routines.json`. The routine is not deferrable: only a used-up window holds it back.
