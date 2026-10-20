---
name: gbrain-host-reconciler
description: "The brain host's reconciler service: how pushed commits reach the published copy and the engine, indexing receipts for on-box writers, rescue branches, the shared sync lock, and operating or recovering the service."
---

# GBrain Host Reconciler

The reconciler is the only process that moves the brain's **published copy** and the only writer of the brain database.
It runs as a systemd user service on the brain host, from the published copy itself.

## Contract

- **Published copy.** Nobody writes in it. Writers commit in their own clone and push to GitHub `main`; the reconciler never commits, rebases or pushes to `main`.
- **Cycle.** Every 15 s it fetches `main` with a bounded fetch, fast-forwards the published copy, imports the text (`gbrain sync --no-pull --no-embed`), proves the engine bookmark matches, then runs a bounded `gbrain embed --stale --max-usd`.
  An embed attempt that times out or leaves stale chunks retries after 2 minutes; embedding never holds up publication or import.
  Without a new commit it re-checks the engine every 30 minutes.
- **Rescue.** A published copy with uncommitted files, local commits, another branch or an unfinished Git operation gets 10 minutes, because a writer may be mid-commit.
  After that the reconciler pushes everything to a `rescue/<UTC timestamp>` branch, resets the copy to `origin/main`, keeps syncing, and files a needs-attention issue with the branch, the changed paths and the options (land through a writer clone, or discard).
- **Paging.** A step that keeps failing for 10 minutes pages `#ops-alerts` once per day per stage, in a plain sentence naming what the reconciler cannot do, and a recovery posts once.
  The same applies to embedding failures and to a sync lock held by someone else for an hour.
  A failed send is logged as an `alert_failed` event and shows in the rollup.
- **Shared sync lock.** Every host job that runs `gbrain sync`, `gbrain embed` or a full doctor takes the same lock file as the reconciler, blocking with `flock -w`. While a job holds it, the reconciler waits.
- **Self-update.** A published commit that touches this skill restarts the service on the new code.

Every brain-specific value (paths, unit name, source, alert account and channel, issue labels, lock file, timings) lives in `config.json`.
The code is identical in every brain and is cross-checked against the shared-core reference copy in wellgent/skills `templates/brain/ops/brain-infra/skills/gbrain-host-reconciler/`.

## Indexing receipts

After a push, an on-box writer asks for its receipt:

```bash
python3 <published>/ops/brain-infra/skills/gbrain-host-reconciler/scripts/reconciler.py receipt <sha> --wait 120
```

- `--level` is `published`, `text` (imported, searchable by keyword) or `complete` (also embedded, the default).
- Exit 0 means the level is reached. Exit 75 means it is still pending when the wait ran out; the push is durable either way, and `phase` and `blocked_reason` in the output say why it waits.

## Operating

- `reconciler.py status` prints the state file, including `heartbeat_at`, the published, indexed and embedded heads, and any block.
- `reconciler.py rollup --hours 24` summarizes publishes, imports, embeds, blocks, alerts, failed sends and rescues for the health workflow's daily run record.
- The journal is `journalctl --user -u <unit>`; events also go to `<state_dir>/events/YYYY-MM-DD.jsonl`, kept for 14 days.
- The health workflow pages on a stale `heartbeat_at`. The reconciler watches the heartbeats listed under `deadman` in `config.json`.
- Install or change the unit: `reconciler.py unit > ~/.config/systemd/user/<unit>`, then `systemctl --user daemon-reload && systemctl --user enable --now <unit>`.
- A sync always targets the published copy. A `gbrain sync --repo <other clone>` moves the source's `local_path` to that clone.

## Recovery

A broken reconciler commit crash-loops the service, so the published copy stops moving.
Push the fix to `main`, then on the host run `git -C <published> fetch origin main && git -C <published> merge --ff-only origin/main`.
The service restarts on the fixed code within 10 seconds.

A rescue issue is settled by its chosen option: land the wanted changes from the branch through a writer clone and delete the branch, or delete the branch.
