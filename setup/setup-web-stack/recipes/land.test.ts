// @vitest-environment node
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  realpathSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, test } from "vitest";

const land = join(import.meta.dirname, "land");

const HEAD = "f6b986ab".padEnd(40, "0");
const OTHER_HEAD = "0badc0de".padEnd(40, "0");

const git = (cwd: string, ...args: Array<string>) => {
  const run = spawnSync(
    "git",
    ["-c", "user.name=Test", "-c", "user.email=test@example.com", ...args],
    { cwd, encoding: "utf8" },
  );
  expect(run.status, run.stderr).toBe(0);
  return run.stdout.trim();
};

// A checkout whose origin `main` holds the squash commit GitHub made, and a
// `gh` on PATH that answers from one PR record: open on HEAD until
// `gh pr merge` runs, which always fails, and AFTER_MERGE once it has. Any
// other commit's statuses are TIP_STATUSES, newest first, and that read fails
// when STATUSES_FAIL is set.
let scratch: string;
let checkout: string;
let hostBin: string;
let mergeCommit: string;
let baseCommit: string;
beforeEach(() => {
  scratch = realpathSync(mkdtempSync(join(tmpdir(), "land-")));
  const origin = join(scratch, "origin.git");
  checkout = join(scratch, "checkout");
  hostBin = join(scratch, "host-bin");
  mkdirSync(hostBin);
  git(scratch, "init", "-q", "--bare", "-b", "main", origin);
  git(scratch, "clone", "-q", origin, checkout);
  git(checkout, "commit", "-q", "--allow-empty", "-m", "base");
  git(checkout, "push", "-q", "origin", "HEAD:main");
  git(checkout, "commit", "-q", "--allow-empty", "-m", "squash of the PR");
  mergeCommit = git(checkout, "rev-parse", "HEAD");
  git(checkout, "push", "-q", "origin", "HEAD:main");
  git(checkout, "reset", "-q", "--hard", "HEAD~1");
  baseCommit = git(checkout, "rev-parse", "HEAD");

  const merged = join(scratch, "merge-ran");
  const gh = join(hostBin, "gh");
  writeFileSync(
    gh,
    `#!/usr/bin/env bash
jq_expr=.
while [ $# -gt 0 ]; do
  case "$1" in --jq) jq_expr=$2; shift ;; esac
  args+=("$1"); shift
done
answer() { jq -r "$jq_expr" <<<"$1"; }
case "\${args[0]} \${args[1]}" in
  "repo view") answer '{"nameWithOwner": "owner/repo"}' ;;
  "api repos/owner/repo/commits/${HEAD}/status")
    answer '{"statuses": [{"context": "check", "state": "success"}]}' ;;
  "api repos/owner/repo/commits/"*"/statuses")
    [ -z "\${STATUSES_FAIL:-}" ] || { echo "HTTP 502" >&2; exit 1; }
    answer "\${TIP_STATUSES:-[]}" ;;
  "pr merge") touch ${JSON.stringify(merged)}; echo "GraphQL: something went wrong" >&2; exit 1 ;;
  "pr view")
    if [ -e ${JSON.stringify(merged)} ]; then answer "$AFTER_MERGE"
    else answer '{"state": "OPEN", "baseRefName": "main", "headRefOid": "${HEAD}", "mergeCommit": null}'
    fi ;;
  *) echo "fake gh: unexpected $*" >&2; exit 64 ;;
esac
`,
  );
  chmodSync(gh, 0o755);
});
afterEach(() => {
  rmSync(scratch, { force: true, recursive: true });
});

const landAfterFailedMerge = (
  afterMerge: object,
  env: Record<string, string> = {},
) => {
  const run = spawnSync("bash", [land, "1496"], {
    cwd: checkout,
    encoding: "utf8",
    env: {
      ...process.env,
      AFTER_MERGE: JSON.stringify(afterMerge),
      PATH: `${hostBin}:${process.env.PATH}`,
      ...env,
    },
  });
  return { status: run.status, stderr: run.stderr, stdout: run.stdout };
};

describe("scripts/land when gh pr merge fails", () => {
  test("a PR GitHub merged on the checked head lands and reports its merge commit", () => {
    const run = landAfterFailedMerge({
      baseRefName: "main",
      headRefOid: HEAD,
      mergeCommit: { oid: mergeCommit },
      state: "MERGED",
    });

    expect(run.status, run.stderr).toBe(0);
    expect(run.stdout).toContain(
      `land: PR 1496 merged as ${mergeCommit} on origin/main (head ${HEAD})`,
    );
  });

  test("a PR still open is refused", () => {
    const run = landAfterFailedMerge({
      baseRefName: "main",
      headRefOid: HEAD,
      mergeCommit: null,
      state: "OPEN",
    });

    expect(run.status).toBe(1);
    expect(run.stderr).toContain(
      "land: merging PR 1496 failed (a moved head refuses)",
    );
  });

  test("a PR merged on another head is refused", () => {
    const run = landAfterFailedMerge({
      baseRefName: "main",
      headRefOid: OTHER_HEAD,
      mergeCommit: { oid: mergeCommit },
      state: "MERGED",
    });

    expect(run.status).toBe(1);
    expect(run.stderr).toContain(
      "land: merging PR 1496 failed (a moved head refuses)",
    );
    expect(run.stdout).not.toContain("merged as");
  });
});

// scripts/production-live answers from a list of commits, one per call, and
// repeats the last one once the list runs out.
const productionServes = (...commits: Array<string>) => {
  const calls = join(scratch, "production-calls");
  writeFileSync(calls, "0");
  mkdirSync(join(checkout, "scripts"), { recursive: true });
  const script = join(checkout, "scripts", "production-live");
  writeFileSync(
    script,
    `#!/usr/bin/env bash
commits=(${commits.join(" ")})
n=$(cat ${JSON.stringify(calls)})
echo $((n + 1)) > ${JSON.stringify(calls)}
[ "$n" -lt \${#commits[@]} ] || n=$((\${#commits[@]} - 1))
echo "\${commits[$n]}"
`,
  );
  chmodSync(script, 0o755);
};

const merged = { baseRefName: "main", headRefOid: HEAD, state: "MERGED" };

describe("scripts/land on a project with scripts/production-live", () => {
  test("production on main's tip lets the merge go ahead", () => {
    productionServes(mergeCommit);
    const run = landAfterFailedMerge({
      ...merged,
      mergeCommit: { oid: mergeCommit },
    });

    expect(run.status, run.stderr).toBe(0);
    expect(run.stdout).not.toContain("waiting for production");
  });

  test("the merge waits until production reaches main's tip", () => {
    productionServes(OTHER_HEAD, mergeCommit);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      { LAND_DEPLOY_POLL_S: "1", LAND_DEPLOY_WAIT_S: "30" },
    );

    expect(run.status, run.stderr).toBe(0);
    expect(run.stdout).toContain(
      `land: waiting for production to run main's tip ${mergeCommit}`,
    );
  });

  test("production behind main past the wait is a stop, and nothing merges", () => {
    productionServes(OTHER_HEAD);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      { LAND_DEPLOY_WAIT_S: "0" },
    );

    expect(run.status).toBe(4);
    expect(run.stderr).toContain(
      `land: production runs ${OTHER_HEAD}, not main's tip ${mergeCommit}`,
    );
    expect(existsSync(join(scratch, "merge-ran"))).toBe(false);
  });

  test("a failed production build of main's tip lets the merge go ahead", () => {
    productionServes(baseCommit);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      {
        LAND_DEPLOY_WAIT_S: "0",
        TIP_STATUSES: JSON.stringify([
          { context: "check", state: "success" },
          { context: "Vercel", state: "failure" },
          { context: "Vercel", state: "pending" },
        ]),
      },
    );

    expect(run.status, run.stderr).toBe(0);
    expect(run.stderr).toContain(
      `land: the production build of main's tip ${mergeCommit} failed (failure); production serves ${baseCommit}`,
    );
    expect(existsSync(join(scratch, "merge-ran"))).toBe(true);
  });

  test("an errored production build of main's tip lets the merge go ahead", () => {
    productionServes(baseCommit);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      {
        LAND_DEPLOY_WAIT_S: "0",
        TIP_STATUSES: JSON.stringify([{ context: "Vercel", state: "error" }]),
      },
    );

    expect(run.status, run.stderr).toBe(0);
    expect(run.stderr).toContain(
      `land: the production build of main's tip ${mergeCommit} failed (error); production serves ${baseCommit}`,
    );
  });

  test("a production build of main's tip still pending keeps the wait, and past it nothing merges", () => {
    productionServes(baseCommit);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      {
        LAND_DEPLOY_WAIT_S: "0",
        TIP_STATUSES: JSON.stringify([
          { context: "Vercel", state: "pending" },
          { context: "Vercel", state: "failure" },
        ]),
      },
    );

    expect(run.status).toBe(4);
    expect(run.stderr).not.toContain("production build of main's tip");
    expect(existsSync(join(scratch, "merge-ran"))).toBe(false);
  });

  test("a failed production build of main's tip keeps the wait when production serves no ancestor of it", () => {
    productionServes(OTHER_HEAD);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      {
        LAND_DEPLOY_WAIT_S: "0",
        TIP_STATUSES: JSON.stringify([{ context: "Vercel", state: "failure" }]),
      },
    );

    expect(run.status).toBe(4);
    expect(run.stderr).not.toContain("production build of main's tip");
    expect(existsSync(join(scratch, "merge-ran"))).toBe(false);
  });

  test("main's tip with no production build status keeps the wait, and past it nothing merges", () => {
    productionServes(baseCommit);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      {
        LAND_DEPLOY_WAIT_S: "0",
        TIP_STATUSES: JSON.stringify([{ context: "check", state: "success" }]),
      },
    );

    expect(run.status).toBe(4);
    expect(run.stderr).not.toContain("production build of main's tip");
    expect(existsSync(join(scratch, "merge-ran"))).toBe(false);
  });

  test("an unreadable production build status of main's tip keeps the wait, and past it nothing merges", () => {
    productionServes(baseCommit);
    const run = landAfterFailedMerge(
      { ...merged, mergeCommit: { oid: mergeCommit } },
      { LAND_DEPLOY_WAIT_S: "0", STATUSES_FAIL: "1" },
    );

    expect(run.status).toBe(4);
    expect(run.stderr).not.toContain("production build of main's tip");
    expect(existsSync(join(scratch, "merge-ran"))).toBe(false);
  });
});
