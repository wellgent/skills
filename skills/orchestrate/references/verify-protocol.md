# Verify protocol

The shared runtime-verification mechanics behind every project's `verify` skill.
Read this first; the project's `verify` skill declares the repo-specific facts (ports, launch, sign-in, gotchas, proven checks) and wins on conflict.
Agents observe what they actually built through this loop: browser review during development, and the dev-loop gate calls `/verify` for any ticket with runtime surface.

## Dev-server discipline

Never drive a dev server you did not start.
Long-lived servers silently degrade, and a shared server dies with whichever session exits first.
Each verification session launches its own ephemeral server on the port its role owns (the project's `verify` skill declares the map) and tears it down when done, via the project's `scripts/dev-server.sh`:

    scripts/dev-server.sh start <port>
    scripts/dev-server.sh status <port>
    scripts/dev-server.sh stop <port>

- `start` refuses a taken port - it never adopts a running server.
- `stop` reaps by pidfile plus a port-scoped sweep, never a broad pkill that could kill someone else's server.
- Teardown is part of the loop, not optional.
- One server per checkout at a time - concurrent dev processes share build state and corrupt it - unless the project's script isolates build dirs per port and its `verify` skill says so.

## Browser health preflight

Default tool: **`agent-browser`**.
Before a verification session, prove the daemon spawns:

    agent-browser open about:blank && agent-browser session info --json && agent-browser close

Healthy output has `"browserLaunched":true` and `"success":true`.
If the daemon fails with `Resource temporarily unavailable` (EAGAIN), the likely cause is per-user process-limit exhaustion: diagnose with `ps aux | wc -l` vs `ulimit -u`, recover by reaping strays (`agent-browser close --all`, leftover dev servers, headless Chrome) rather than reinstalling.

## The review loop

The known-good sequence, against your session's own port:

    agent-browser open http://localhost:<port> && agent-browser wait --load networkidle
    agent-browser set viewport 375 812 && agent-browser screenshot --full /abs/path/mobile.png
    agent-browser set viewport 1280 800 && agent-browser screenshot --full /abs/path/desktop.png
    agent-browser close

Pass **absolute paths** to `agent-browser screenshot` - relative paths resolve against the daemon's working directory, not the caller's.

## Universal gotchas

- A production build clobbers a running dev server's build dir - stop the server before building, and restart clean if it 500s.
- Saved browser auth state goes stale; re-run sign-in at the start of each session rather than trusting yesterday's.

## The living-skill rule

Each verification session appends the gotchas it earns to the project's `verify` skill - the local manual sharpens with use.
Nothing project-specific lands in this protocol; a line belongs here only when it reads identically for every project.
