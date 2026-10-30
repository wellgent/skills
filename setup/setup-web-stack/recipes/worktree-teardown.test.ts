// @vitest-environment node
import { type ChildProcess, spawn, spawnSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  realpathSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, expect, test } from "vitest";

const scriptsDir = import.meta.dirname;

const git = (cwd: string, ...args: Array<string>) => {
  const run = spawnSync(
    "git",
    ["-c", "user.name=t", "-c", "user.email=t@t", ...args],
    { cwd, encoding: "utf8" },
  );
  expect(run.status, run.stderr).toBe(0);
};

// A main checkout whose committed scripts are the teardown under test and a
// stub `scripts/dev-server.sh` that only logs, and a linked worktree of it.
let scratch: string;
let main: string;
let worktree: string;
let log: string;
const processes: Array<ChildProcess> = [];
beforeEach(() => {
  scratch = realpathSync(
    mkdtempSync(join(tmpdir(), "<project name>-worktree-teardown-")),
  );
  main = join(scratch, "main");
  worktree = join(scratch, "worktree");
  log = join(scratch, "calls.log");
  mkdirSync(join(main, "scripts"), { recursive: true });
  copyFileSync(
    join(scriptsDir, "worktree-teardown.sh"),
    join(main, "scripts", "worktree-teardown.sh"),
  );
  writeFileSync(
    join(main, "scripts", "dev-server.sh"),
    `#!/usr/bin/env bash\necho "dev-server.sh $*" >>${JSON.stringify(log)}\n`,
  );
  chmodSync(join(main, "scripts", "dev-server.sh"), 0o755);
  git(main, "init", "-q");
  git(main, "add", ".");
  git(main, "commit", "-q", "-m", "root");
  git(main, "worktree", "add", "-q", "--detach", worktree);
});

afterEach(() => {
  for (const child of processes.splice(0)) {
    if (child.pid !== undefined && alive(child.pid)) {
      process.kill(child.pid, "SIGKILL");
    }
  }
  rmSync(scratch, { force: true, recursive: true });
});

const alive = (pid: number) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
};

// A long-lived process the test owns, as a test run or a `convex dev` left
// behind would be.
const start = (cwd: string, script: string, ...args: Array<string>) => {
  const child = spawn("sh", ["-c", script, "sh", ...args], {
    cwd,
    detached: true,
    stdio: "ignore",
  });
  processes.push(child);
  return child.pid!;
};

const waitGone = async (pid: number) => {
  for (let i = 0; i < 50 && alive(pid); i++) {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return !alive(pid);
};

test("teardown stops every process still running from the tree and spares the rest", async () => {
  const inTree = start(worktree, "exec sleep 300");
  const namesTree = start(
    scratch,
    'trap "" TERM; while :; do sleep 1; done',
    join(worktree, "e2e", "playwright.config.ts"),
  );
  const outside = start(scratch, "exec sleep 300");
  const sibling = start(scratch, "exec sleep 300", `${worktree}-other/x`);

  const teardown = spawnSync("bash", ["scripts/worktree-teardown.sh"], {
    cwd: worktree,
    encoding: "utf8",
  });

  expect(teardown.status, teardown.stderr).toBe(0);
  expect(teardown.stdout).toContain("stray process");
  expect(await waitGone(inTree)).toBe(true);
  // It ignores TERM, so only the KILL after the grace period stops it.
  expect(await waitGone(namesTree)).toBe(true);
  expect(alive(outside)).toBe(true);
  expect(alive(sibling)).toBe(true);
  expect(existsSync(worktree)).toBe(false);
}, 30_000);

test("teardown piped through a command started in the tree spares that command", () => {
  const teardown = spawnSync(
    "bash",
    ["-c", "bash scripts/worktree-teardown.sh | cat"],
    { cwd: worktree, encoding: "utf8" },
  );

  expect(teardown.status, teardown.stderr).toBe(0);
  expect(teardown.stdout).not.toContain("stray process");
  expect(teardown.stdout).toContain(`removed worktree ${worktree}`);
  expect(existsSync(worktree)).toBe(false);
});

test("teardown removes the worktrees' directory with its last worktree", () => {
  const trees = join(scratch, "project-wt");
  const first = join(trees, "feature", "one");
  const second = join(trees, "two");
  git(main, "worktree", "add", "-q", "--detach", first);
  git(main, "worktree", "add", "-q", "--detach", second);
  const teardown = (cwd: string) =>
    spawnSync("bash", ["scripts/worktree-teardown.sh"], {
      cwd,
      encoding: "utf8",
    });

  const one = teardown(first);
  expect(one.status, one.stderr).toBe(0);
  expect(existsSync(join(trees, "feature"))).toBe(false);
  expect(existsSync(second)).toBe(true);

  const two = teardown(second);
  expect(two.status, two.stderr).toBe(0);
  expect(two.stdout).toContain(`removed empty ${trees}`);
  expect(existsSync(trees)).toBe(false);
  expect(existsSync(main)).toBe(true);
  expect(existsSync(scratch)).toBe(true);
});

test("teardown with nothing left running removes the tree and reports no strays", () => {
  const teardown = spawnSync("bash", ["scripts/worktree-teardown.sh"], {
    cwd: worktree,
    encoding: "utf8",
  });

  expect(teardown.status, teardown.stderr).toBe(0);
  expect(teardown.stdout).not.toContain("stray process");
  expect(teardown.stdout).toContain(`removed worktree ${worktree}`);
  expect(existsSync(worktree)).toBe(false);
});
