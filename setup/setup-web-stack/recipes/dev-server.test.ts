// @vitest-environment node
import { ChildProcess, spawn, spawnSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  realpathSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { createServer } from "node:net";
import { basename, join } from "node:path";
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  test,
} from "vitest";

const scriptsDir = import.meta.dirname;

// A port the script's own start check finds free: one the system just handed
// out and released, outside the <lowest dev-server port, e.g. 6110> to <highest dev-server port, e.g. 6199> a worktree's server may use, so
// no worktree holds its listener or its PID file.
const releasedPort = async () => {
  const server = createServer();
  await new Promise<void>((resolve) => server.listen(0, resolve));
  const address = server.address();
  await new Promise((resolve) => server.close(resolve));
  if (address === null || typeof address === "string") {
    throw new Error("the released port has no number");
  }
  return String(address.port);
};
let freePort: string;
let otherFreePort: string;
beforeAll(async () => {
  freePort = await releasedPort();
  do {
    otherFreePort = await releasedPort();
  } while (otherFreePort === freePort);
});

// The host state every checkout of a test shares: the claims of
// scripts/host-claims.sh live under its XDG_STATE_HOME.
let stateHome: string;
beforeEach(() => {
  stateHome = mkdtempSync(join(tmpdir(), "<project name>-dev-server-state-"));
});

// Puts the scripts under the checkout's scripts/ and a bin dir that a test
// puts first on the script's PATH to stand in for a host tool.
let checkouts: Array<string> = [];
const withScripts = (root: string) => {
  mkdirSync(join(root, "scripts"));
  for (const name of ["dev-server.sh", "host-claims.sh"]) {
    copyFileSync(join(scriptsDir, name), join(root, "scripts", name));
  }
  mkdirSync(join(root, "host-bin"));
  return root;
};

const newCheckout = () => {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "<project name>-dev-server-")));
  checkouts.push(root);
  return withScripts(root);
};

// A fresh repository with one commit, whose root is its main checkout.
const newRepository = () => {
  const repo = realpathSync(
    mkdtempSync(join(tmpdir(), "<project name>-dev-server-repo-")),
  );
  checkouts.push(repo);
  const git = (...args: Array<string>) =>
    spawnSync("git", ["-C", repo, ...args], { encoding: "utf8" });
  git("init", "-q");
  git(
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@t",
    "commit",
    "-q",
    "--allow-empty",
    "-m",
    "root",
  );
  return { git, repo };
};

const newMainCheckout = () => withScripts(newRepository().repo);

// A checkout that is a linked worktree of a fresh repository, as teardown
// requires.
const newWorktreeCheckout = () => {
  const { git, repo } = newRepository();
  const root = join(repo, "..", `${basename(repo)}-wt`);
  git("worktree", "add", "-q", "--detach", root);
  checkouts.push(root);
  return withScripts(root);
};

// The test's own checkout, with a .next holding the dev types a `next dev`
// writes beside its lockfile.
let checkout: string;
let devTypes: string;
beforeEach(() => {
  checkout = newCheckout();
  devTypes = join(checkout, ".next", "dev", "types");
  mkdirSync(devTypes, { recursive: true });
  writeFileSync(join(devTypes, "validator.ts"), "export {};\n");
});
let holders: Array<ChildProcess> = [];
afterEach(() => {
  for (const holder of holders) {
    holder.kill();
  }
  holders = [];
});

// The lockfile `next dev` writes in .next/dev, naming the server's pid.
const writeDevLock = (pid: number) => {
  writeFileSync(
    join(checkout, ".next", "dev", "lock"),
    JSON.stringify({ appUrl: "http://localhost:6100", pid }),
  );
};

// The pid of a live process that holds the given lockfile open, as the
// `next dev` that wrote it does while it runs.
const lockHolder = async (lock: string) => {
  const holder = spawn(
    "bash",
    ["-c", 'exec 3<"$0"; echo; exec sleep 60', lock],
    {
      stdio: ["ignore", "pipe", "ignore"],
    },
  );
  holders.push(holder);
  await new Promise((resolve) => holder.stdout.once("data", resolve));
  return holder.pid!;
};

// The pid of the checkout's running next dev: a process holding its lockfile.
const checkoutServerPid = async () => {
  writeDevLock(0);
  const pid = await lockHolder(join(checkout, ".next", "dev", "lock"));
  writeDevLock(pid);
  return pid;
};

// The pid of a process that has exited.
const exitedPid = () => {
  const run = spawnSync("bash", ["-c", "echo $$"], { encoding: "utf8" });
  return Number(run.stdout.trim());
};

const scriptEnv = (root: string, env: Record<string, string>) => ({
  ...process.env,
  PATH: `${join(root, "host-bin")}:${process.env.PATH}`,
  XDG_STATE_HOME: stateHome,
  ...env,
});

const devServerIn = (
  root: string,
  args: Array<string>,
  env: Record<string, string> = {},
) => {
  const run = spawnSync(join(root, "scripts", "dev-server.sh"), args, {
    encoding: "utf8",
    env: scriptEnv(root, env),
  });
  return { status: run.status, stderr: run.stderr, stdout: run.stdout };
};

const devServer = (...args: Array<string>) => devServerIn(checkout, args);

// Runs the script without blocking, so two checkouts can run it at once.
const devServerAsync = (
  root: string,
  args: Array<string>,
  env: Record<string, string> = {},
) =>
  new Promise<{ status: number | null; stderr: string; stdout: string }>(
    (resolve) => {
      const run = spawn(join(root, "scripts", "dev-server.sh"), args, {
        env: scriptEnv(root, env),
        stdio: ["ignore", "pipe", "pipe"],
      });
      let stdout = "";
      let stderr = "";
      run.stdout.on("data", (chunk) => (stdout += chunk));
      run.stderr.on("data", (chunk) => (stderr += chunk));
      run.on("close", (status) => resolve({ status, stderr, stdout }));
    },
  );

// The files `start` writes outside the checkout, read from its ready line.
const serverFiles = (stdout: string) => {
  const ready = /\(pid (\d+), log (\S+)\)/.exec(stdout);
  if (ready === null) {
    throw new Error(`no ready line in: ${stdout}`);
  }
  return { log: ready[2], pid: Number(ready[1]) };
};

afterEach(() => {
  for (const root of checkouts) {
    if (existsSync(join(root, ".convex", "convex-dev.pid"))) {
      devServerIn(root, ["convex-stop"]);
    }
    if (
      existsSync(join(root, ".next", "dev", "lock")) ||
      existsSync(`/tmp/<project name>-dev-${basename(root)}-${freePort}.pid`)
    ) {
      devServerIn(root, ["stop", freePort]);
    }
    for (const port of [freePort, otherFreePort]) {
      for (const suffix of ["pid", "log"]) {
        rmSync(`/tmp/<project name>-dev-${basename(root)}-${port}.${suffix}`, {
          force: true,
        });
      }
    }
    rmSync(root, { force: true, recursive: true });
  }
  checkouts = [];
  rmSync(stateHome, { force: true, recursive: true });
});

const waitFor = async (done: () => boolean) => {
  for (let tries = 0; !done(); tries++) {
    if (tries === 100) {
      throw new Error("the condition did not hold within 10s");
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
};

const executable = (path: string, body: string) => {
  writeFileSync(path, body);
  chmodSync(path, 0o755);
};

const localConfig = (root: string) =>
  join(root, ".convex", "local", "default", "config.json");

const writeLocalConfig = (
  root: string,
  ports: { cloud: number; site: number },
) =>
  writeFileSync(
    localConfig(root),
    JSON.stringify({
      adminKey: "local-admin-key",
      deploymentName: "local-test",
      ports,
    }),
  );

// A checkout on a local deployment whose last convex dev logged its ready
// line, on a host slow to start a process, with a `convex dev` that saves the
// backend ports it is given to the config, names its deployment in .env.local
// and then pushes, as the CLI's does, and appends its start and its push to
// the file TIMELINE names, when set. Like the CLI's, it leaves the URLs in
// .env.local as they are while another line repeats their value. Returns the
// file that `convex dev` writes once it has pushed.
const givenLocalCheckout = (pushAfterMs = 500, root = checkout) => {
  const hostBin = join(root, "host-bin");
  mkdirSync(join(root, ".convex", "local", "default"), { recursive: true });
  writeLocalConfig(root, { cloud: 3210, site: 3211 });
  writeFileSync(
    join(root, ".env.local"),
    "NEXT_PUBLIC_CONVEX_URL=http://127.0.0.1:1\n",
  );
  writeFileSync(
    join(root, ".convex", "convex-dev.log"),
    "Convex functions ready! (1s)\n",
  );
  const jq = spawnSync("bash", ["-c", "command -v jq"], { encoding: "utf8" });
  executable(
    join(hostBin, "jq"),
    `#!/usr/bin/env bash\nsleep 1\nexec ${jq.stdout.trim()} "$@"\n`,
  );
  const cli = join(root, "node_modules", "convex", "bin");
  mkdirSync(cli, { recursive: true });
  const pushed = join(root, ".convex", "pushed");
  writeFileSync(
    join(cli, "main.js"),
    `const fs = require("node:fs");
const mark = (event) => {
  if (process.env.TIMELINE) {
    fs.appendFileSync(process.env.TIMELINE, event + " " + process.cwd() + "\\n");
  }
};
mark("start");
const port = (flag) => process.argv.includes(flag) && Number(process.argv[process.argv.indexOf(flag) + 1]);
if (port("--local-cloud-port")) {
  const config = JSON.parse(fs.readFileSync(".convex/local/default/config.json", "utf8"));
  config.ports = { cloud: port("--local-cloud-port"), site: port("--local-site-port") };
  fs.writeFileSync(".convex/local/default/config.json", JSON.stringify(config));
}
process.on("SIGINT", () => process.exit(0));
setTimeout(() => {
  fs.appendFileSync(
    ".env.local",
    "\\n# Deployment used by \`npx convex dev\`\\nCONVEX_DEPLOYMENT=" + process.env.CONVEX_DEPLOYMENT + "\\n",
  );
  mark("ready");
  console.log("Convex functions ready! (1s)");
  fs.writeFileSync(${JSON.stringify(pushed)}, "");
}, ${pushAfterMs});
setInterval(() => {}, 1000);
`,
  );
  mkdirSync(join(root, "node_modules", ".bin"));
  executable(
    join(root, "node_modules", ".bin", "convex"),
    `#!/usr/bin/env bash\nexec node ${JSON.stringify(join(cli, "main.js"))} "$@"\n`,
  );
  return pushed;
};

// Starts the given command as a checkout's convex dev from a shell that exits
// at once, so the host reaps it when it stops while this test's synchronous
// runs block Node's own reaping, and records its pid in the checkout's
// pidfile. Returns that pid.
const convexDevStartedIn = (
  root: string,
  command: string,
  env: Record<string, string> = {},
) => {
  const started = spawnSync(
    "bash",
    [
      "-c",
      `${command} dev >.convex/convex-dev.log 2>&1 & echo $! >.convex/convex-dev.pid`,
    ],
    {
      cwd: root,
      env: { ...process.env, CONVEX_DEPLOYMENT: "local:local-test", ...env },
    },
  );
  expect(started.status).toBe(0);
  return readFileSync(join(root, ".convex", "convex-dev.pid"), "utf8").trim();
};

const alive = (pid: number) => {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
};

// A checkout on a cloud deployment whose one push takes a second, with a
// `next dev` that holds the checkout's .next/dev/lock and serves the port it
// is given, as Next's does, or exits when that port is taken. Its `next build`
// writes .next/BUILD_ID, and its `next start` serves the port with no lockfile
// and exits without that build, as Next's do.
const givenServableCheckout = (root: string) => {
  const server = join(root, "next-dev.cjs");
  writeFileSync(
    server,
    `const fs = require("node:fs");
const http = require("node:http");
const command = process.argv[2];
if (command === "build") {
  fs.mkdirSync(".next", { recursive: true });
  fs.writeFileSync(".next/BUILD_ID", "test-build");
  process.exit(0);
}
if (command === "start" && !fs.existsSync(".next/BUILD_ID")) {
  console.log("no production build");
  process.exit(1);
}
const port = Number(process.argv[process.argv.indexOf("-p") + 1]);
if (command === "dev") {
  fs.mkdirSync(".next/dev", { recursive: true });
  fs.writeFileSync(".next/dev/lock", JSON.stringify({ appUrl: "http://localhost:" + port, pid: process.pid }));
  fs.openSync(".next/dev/lock", "r");
}
http
  .createServer((request, response) => response.end("ok"))
  .on("error", (error) => {
    console.log(error.code);
    process.exit(1);
  })
  .listen(port, () => console.log("serving " + process.cwd()));
`,
  );
  mkdirSync(join(root, "node_modules", ".bin"), { recursive: true });
  executable(
    join(root, "node_modules", ".bin", "next"),
    `#!/usr/bin/env bash\nexec node ${JSON.stringify(server)} "$@"\n`,
  );
  executable(join(root, "host-bin", "pnpm"), "#!/usr/bin/env bash\nsleep 1\n");
};

// Another checkout's local backend: a process serving the given port that
// answers /instance_name with that checkout's deployment.
const otherBackend = async (port: number) => {
  const backend = spawn(
    "node",
    [
      "-e",
      `require("node:http").createServer((q, r) => r.end(q.url === "/instance_name" ? "other-checkout" : "")).listen(${port}, "127.0.0.1", () => console.log("listening"))`,
    ],
    { stdio: ["ignore", "pipe", "ignore"] },
  );
  holders.push(backend);
  await new Promise((resolve) => backend.stdout.once("data", resolve));
};

// The .env.local of a local checkout held to its backend on the given ports.
const heldEnvLocal = (cloud: number, site: number) =>
  [
    `NEXT_PUBLIC_CONVEX_URL=http://127.0.0.1:${cloud}`,
    `NEXT_PUBLIC_CONVEX_SITE_URL=http://127.0.0.1:${site}`,
    "# The Convex CLI of this checkout reaches only its local backend (scripts/dev-server.sh).",
    `CONVEX_SELF_HOSTED_URL=http://127.0.0.1:${cloud}`,
    "CONVEX_SELF_HOSTED_ADMIN_KEY=local-admin-key",
    "CONVEX_OVERRIDE_ACCESS_TOKEN=checkout-holds-no-convex-login",
    "",
  ].join("\n");

const envValue = (root: string, name: string) =>
  new RegExp(`^${name}=(.*)$`, "m").exec(
    readFileSync(join(root, ".env.local"), "utf8"),
  )?.[1];

describe("scripts/dev-server.sh", () => {
  test("start of one port from two checkouts at once serves one and refuses the other, leaving the served one's pid and log files as they were", async () => {
    const other = newCheckout();
    givenServableCheckout(checkout);
    givenServableCheckout(other);

    const runs = await Promise.all(
      [checkout, other].map((root) =>
        devServerAsync(root, ["start", freePort]),
      ),
    );

    expect(runs.map((run) => run.status).toSorted()).toEqual([0, 1]);
    const servedAt = runs.findIndex((run) => run.status === 0);
    const refused = runs[1 - servedAt];
    expect(refused.stderr).toContain(`port ${freePort} is claimed by`);
    const served = serverFiles(runs[servedAt].stdout);
    expect(readFileSync(served.log, "utf8")).toBe(
      `serving ${[checkout, other][servedAt]}\n`,
    );
    expect(
      readFileSync(served.log.replace(/\.log$/, ".pid"), "utf8").trim(),
    ).toBe(String(served.pid));
    expect(alive(served.pid)).toBe(true);
  }, 30_000);

  test("start reports a failed start when another process takes the port before its next dev listens", () => {
    givenServableCheckout(checkout);
    // The taker writes its pid only once it holds the port, and the step
    // before next dev waits for that file, so next dev always finds the port
    // taken.
    const taker = join(checkout, "taker.pid");
    executable(
      join(checkout, "host-bin", "pnpm"),
      `#!/usr/bin/env bash
nohup node -e 'require("node:http").createServer((q, r) => r.end("other")).listen(${freePort}, () => require("node:fs").writeFileSync(${JSON.stringify(taker)}, String(process.pid)))' >/dev/null 2>&1 &
for _ in $(seq 1 100); do
  [ -s ${JSON.stringify(taker)} ] && break
  sleep 0.1
done
`,
    );
    try {
      const run = devServer("start", freePort);

      expect(run.status).toBe(1);
      expect(run.stdout).not.toContain("ready on");
    } finally {
      process.kill(Number(readFileSync(taker, "utf8")));
    }
  }, 30_000);

  test("stop from another checkout leaves running the next dev whose listener holds the first checkout's lockfile", () => {
    const other = newCheckout();
    givenServableCheckout(checkout);
    const started = devServer("start", freePort);
    expect(started.status, started.stderr).toBe(0);
    const { pid } = serverFiles(started.stdout);

    const stop = devServerIn(other, ["stop", freePort]);

    expect(stop.status).toBe(0);
    expect(alive(pid)).toBe(true);
  }, 30_000);

  test("start in another checkout takes a port whose claiming next dev has gone", async () => {
    const other = newCheckout();
    givenServableCheckout(checkout);
    givenServableCheckout(other);
    const first = devServer("start", freePort);
    expect(first.status, first.stderr).toBe(0);
    const { pid } = serverFiles(first.stdout);
    process.kill(pid, "SIGKILL");
    await waitFor(() => !alive(pid));

    const second = devServerIn(other, ["start", freePort]);

    expect(second.status, second.stderr).toBe(0);
    expect(readFileSync(serverFiles(second.stdout).log, "utf8")).toBe(
      `serving ${other}\n`,
    );
  }, 30_000);

  test("serve-build serves a fresh build and refuses a second serve-build of its port from either checkout", () => {
    const other = newCheckout();
    givenServableCheckout(checkout);
    givenServableCheckout(other);
    writeFileSync(join(checkout, ".next", "BUILD_ID"), "stale-build");

    const served = devServer("serve-build", freePort);
    const again = devServer("serve-build", freePort);
    const fromOther = devServerIn(other, ["serve-build", freePort]);

    expect(served.status, served.stderr).toBe(0);
    expect(readFileSync(join(checkout, ".next", "BUILD_ID"), "utf8")).toBe(
      "test-build",
    );
    const { log, pid } = serverFiles(served.stdout);
    expect(readFileSync(log, "utf8")).toContain(`serving ${checkout}\n`);
    expect(alive(pid)).toBe(true);
    expect(again.status).toBe(1);
    expect(again.stderr).toContain("already running");
    expect(fromOther.status).toBe(1);
    expect(fromOther.stderr).toContain(`port ${freePort} is claimed by`);
    expect(devServer("free", freePort).status).toBe(1);
  }, 30_000);

  test("a serve-build port is free again once its server exits, and stop releases it", async () => {
    const other = newCheckout();
    givenServableCheckout(checkout);
    givenServableCheckout(other);
    const first = devServer("serve-build", freePort);
    expect(first.status, first.stderr).toBe(0);
    const { pid } = serverFiles(first.stdout);
    process.kill(pid, "SIGKILL");
    await waitFor(() => !alive(pid));

    const freed = devServer("free", freePort);
    const second = devServerIn(other, ["serve-build", freePort]);
    const stop = devServerIn(other, ["stop", freePort]);

    expect(freed.status).toBe(0);
    expect(second.status, second.stderr).toBe(0);
    const server = serverFiles(second.stdout);
    expect(readFileSync(server.log, "utf8")).toContain(`serving ${other}\n`);
    expect(stop.status).toBe(0);
    expect(alive(server.pid)).toBe(false);
    expect(existsSync(join(stateHome, "<project name>", "ports", freePort))).toBe(
      false,
    );
  }, 30_000);

  test("teardown stops a serve-build server of the checkout and frees its port", () => {
    const worktree = newWorktreeCheckout();
    givenServableCheckout(worktree);
    const served = devServerIn(worktree, ["serve-build", freePort]);
    expect(served.status, served.stderr).toBe(0);
    const { pid } = serverFiles(served.stdout);

    const teardown = devServerIn(worktree, ["teardown"]);

    expect(teardown.status, teardown.stderr).toBe(0);
    expect(alive(pid)).toBe(false);
    expect(devServerIn(worktree, ["free", freePort]).status).toBe(0);
  }, 30_000);

  test("teardown removes the checkout's pid and log files and Playwright output, and keeps another checkout's", () => {
    const worktree = newWorktreeCheckout();
    const own = `/tmp/<project name>-dev-${basename(worktree)}-${freePort}`;
    const other = `/tmp/<project name>-dev-${basename(worktree)}-u1-${freePort}`;
    const files = [`${own}.pid`, `${own}.log`, `${own}.log.mark`, `${other}.log`];
    for (const file of files) {
      writeFileSync(file, "999999\n");
    }
    const ownOutput = `/tmp/<project name>-journeys-${basename(worktree)}`;
    const otherOutput = `/tmp/<project name>-journeys-u1-${basename(worktree)}`;
    const dirs = [ownOutput, otherOutput];
    for (const dir of dirs) {
      mkdirSync(dir, { recursive: true });
    }
    try {
      const teardown = devServerIn(worktree, ["teardown"]);

      expect(teardown.status, teardown.stderr).toBe(0);
      expect(files.map((file) => existsSync(file))).toEqual([false, false, false, true]);
      expect(dirs.map((dir) => existsSync(dir))).toEqual([false, true]);
    } finally {
      for (const file of files) {
        rmSync(file, { force: true });
      }
      for (const dir of dirs) {
        rmSync(dir, { force: true, recursive: true });
      }
    }
  }, 30_000);

  test("serve-build and start on another port refuse while a serve-build of the checkout runs, and keep its build", () => {
    givenServableCheckout(checkout);
    const served = devServer("serve-build", freePort);
    expect(served.status, served.stderr).toBe(0);
    const { pid } = serverFiles(served.stdout);
    try {
      const build = devServer("serve-build", otherFreePort);
      const dev = devServer("start", otherFreePort);

      for (const run of [build, dev]) {
        expect(run.status).toBe(1);
        expect(run.stderr).toContain(
          `a server of this checkout is running (pid ${pid}, port ${freePort})`,
        );
      }
      expect(readFileSync(join(checkout, ".next", "BUILD_ID"), "utf8")).toBe(
        "test-build",
      );
      expect(alive(pid)).toBe(true);
    } finally {
      devServer("stop", otherFreePort);
    }
  }, 30_000);

  test("convex-start in two checkouts at once starts the second convex dev only once the first has pushed", async () => {
    const other = newCheckout();
    givenLocalCheckout(500, checkout);
    givenLocalCheckout(500, other);
    const timeline = join(stateHome, "timeline");

    const runs = await Promise.all(
      [checkout, other].map((root) =>
        devServerAsync(root, ["convex-start"], { TIMELINE: timeline }),
      ),
    );

    expect(runs.map((run) => run.status)).toEqual([0, 0]);
    const events = readFileSync(timeline, "utf8")
      .trim()
      .split("\n")
      .map((line) => line.split(" ")[0]);
    expect(events).toEqual(["start", "ready", "start", "ready"]);
  }, 30_000);

  test("start on a free port refuses while a next dev of the checkout runs on another port, and keeps its .next", async () => {
    const pid = await checkoutServerPid();

    const run = devServer("start", freePort);

    expect(run.status).toBe(1);
    expect(run.stderr).toContain(
      `a next dev of this checkout is running (pid ${pid})`,
    );
    expect(existsSync(join(devTypes, "validator.ts"))).toBe(true);
  });

  test("site-url prints the local deployment's origin and none of its admin key", () => {
    const local = join(checkout, ".convex", "local", "default");
    mkdirSync(local, { recursive: true });
    writeFileSync(
      join(local, "config.json"),
      JSON.stringify({ adminKey: "secret-key", ports: { cloud: 3210, site: 3211 } }),
    );

    const run = devServer("site-url");

    expect(run.status).toBe(0);
    expect(run.stdout.trim()).toBe("http://127.0.0.1:3211");
    expect(run.stdout).not.toContain("secret-key");
  });

  test("site-url refuses a checkout with no local deployment", () => {
    const run = devServer("site-url");

    expect(run.status).toBe(1);
    expect(run.stderr).toContain("no local deployment");
  });

  test("clear-stale-types removes the dev types when no next dev of the checkout runs", () => {
    writeDevLock(exitedPid());

    const run = devServer("clear-stale-types");

    expect(run.status).toBe(0);
    expect(existsSync(devTypes)).toBe(false);
  });

  test("clear-stale-types removes the dev types when the lockfile's pid names a live process that does not hold it", () => {
    writeDevLock(process.pid);

    const run = devServer("clear-stale-types");

    expect(run.status).toBe(0);
    expect(existsSync(devTypes)).toBe(false);
  });

  test("clear-stale-types removes the dev types when the lockfile's pid holds another checkout's lockfile", async () => {
    const other = mkdtempSync(join(tmpdir(), "<project name>-dev-server-other-"));
    try {
      writeFileSync(join(other, "lock"), "{}");
      writeDevLock(await lockHolder(join(other, "lock")));

      const run = devServer("clear-stale-types");

      expect(run.status).toBe(0);
      expect(existsSync(devTypes)).toBe(false);
    } finally {
      rmSync(other, { force: true, recursive: true });
    }
  });

  test("clear-stale-types keeps the dev types of a running next dev", async () => {
    await checkoutServerPid();

    const run = devServer("clear-stale-types");

    expect(run.status).toBe(0);
    expect(existsSync(join(devTypes, "validator.ts"))).toBe(true);
  });

  test("clear-stale-types removes dev types that have no lockfile beside them", () => {
    const run = devServer("clear-stale-types");

    expect(run.status).toBe(0);
    expect(existsSync(devTypes)).toBe(false);
  });

  // The fixture's jq takes a second on each call: the convex dev start, each
  // poll before the push and the hold after it.
  test("convex-start holds .env.local after the convex dev it starts names its deployment, past an earlier run's ready line", async () => {
    const pushed = givenLocalCheckout();

    const run = devServer("convex-start");
    await waitFor(() => existsSync(pushed));

    expect(run.status).toBe(0);
    expect(readFileSync(join(checkout, ".env.local"), "utf8")).not.toMatch(
      /^CONVEX_DEPLOYMENT=/m,
    );
  }, 30_000);

  test("convex-start beside a running convex dev holds .env.local after that convex dev names its deployment", async () => {
    const pushed = givenLocalCheckout(3000);
    const pid = convexDevStartedIn(
      checkout,
      "node node_modules/convex/bin/main.js",
    );

    const run = devServer("convex-start");
    await waitFor(() => existsSync(pushed));

    expect(run.status).toBe(0);
    expect(run.stdout).toContain(
      `convex dev already serves this checkout (pid ${pid}`,
    );
    expect(readFileSync(join(checkout, ".env.local"), "utf8")).not.toMatch(
      /^CONVEX_DEPLOYMENT=/m,
    );
  }, 15_000);

  test("convex-start beside a convex dev still in its shell wrapper keeps that convex dev and its pidfile", async () => {
    const pushed = givenLocalCheckout();
    const wrapper = join(checkout, "node_modules", ".bin", "convex");
    executable(
      wrapper,
      `#!/bin/sh\nsleep 2\nexec node node_modules/convex/bin/main.js "$@"\n`,
    );
    const timeline = join(stateHome, "timeline");
    const pid = convexDevStartedIn(checkout, "node_modules/.bin/convex", {
      TIMELINE: timeline,
    });

    const run = devServerIn(checkout, ["convex-start"], { TIMELINE: timeline });
    await waitFor(() => existsSync(pushed));

    expect(run.status, run.stderr).toBe(0);
    expect(run.stdout).toContain(
      `convex dev already serves this checkout (pid ${pid}`,
    );
    expect(
      readFileSync(join(checkout, ".convex", "convex-dev.pid"), "utf8").trim(),
    ).toBe(pid);
    expect(readFileSync(timeline, "utf8")).toBe(
      `start ${checkout}\nready ${checkout}\n`,
    );
  }, 15_000);

  test("convex-start whose pidfile names another checkout's convex dev starts its own and leaves the other running", async () => {
    const other = newCheckout();
    givenLocalCheckout(500, checkout);
    givenLocalCheckout(500, other);
    const otherPid = convexDevStartedIn(
      other,
      "node node_modules/convex/bin/main.js",
    );
    writeFileSync(join(checkout, ".convex", "convex-dev.pid"), otherPid);

    const run = devServer("convex-start");

    expect(run.status, run.stderr).toBe(0);
    expect(run.stdout).toContain("convex dev serves");
    expect(
      readFileSync(join(checkout, ".convex", "convex-dev.pid"), "utf8").trim(),
    ).not.toBe(otherPid);
    expect(alive(Number(otherPid))).toBe(true);
  }, 15_000);

  test("convex-start after another checkout's backend took the backend's port serves new ports and points .env.local at them", async () => {
    const pushed = givenLocalCheckout();
    const taken = Number(freePort);
    const site = Number(otherFreePort);
    await otherBackend(taken);
    writeLocalConfig(checkout, { cloud: taken, site });
    writeFileSync(join(checkout, ".env.local"), heldEnvLocal(taken, site));

    const run = devServer("convex-start");
    await waitFor(() => existsSync(pushed));

    expect(run.status, run.stderr).toBe(0);
    const { ports } = JSON.parse(readFileSync(localConfig(checkout), "utf8"));
    expect(ports.cloud).not.toBe(taken);
    expect(ports.site).not.toBe(ports.cloud);
    expect(
      [
        "NEXT_PUBLIC_CONVEX_URL",
        "CONVEX_SELF_HOSTED_URL",
        "NEXT_PUBLIC_CONVEX_SITE_URL",
      ].map((name) => envValue(checkout, name)),
    ).toEqual([
      `http://127.0.0.1:${ports.cloud}`,
      `http://127.0.0.1:${ports.cloud}`,
      `http://127.0.0.1:${ports.site}`,
    ]);
  }, 30_000);

  test("convex-start whose convex dev exits before its backend answers, while another checkout's backend holds the config's port, exits 2 and leaves .env.local naming no backend URL", async () => {
    givenLocalCheckout();
    const taken = Number(freePort);
    await otherBackend(taken);
    writeLocalConfig(checkout, { cloud: taken, site: Number(otherFreePort) });
    writeFileSync(
      join(checkout, ".env.local"),
      heldEnvLocal(taken, Number(otherFreePort)),
    );
    writeFileSync(
      join(checkout, "node_modules", "convex", "bin", "main.js"),
      "process.exit(1);\n",
    );

    const run = devServer("convex-start");

    expect(run.status).toBe(2);
    expect(run.stderr).toContain("the local Convex backend did not start");
    expect(readFileSync(join(checkout, ".env.local"), "utf8")).not.toMatch(
      /^(NEXT_PUBLIC_CONVEX_URL|NEXT_PUBLIC_CONVEX_SITE_URL|CONVEX_SELF_HOSTED_URL)=/m,
    );
  }, 30_000);

  test("convex-start in a main checkout with stray local state refuses, names the recovery, and leaves .env.local byte for byte", () => {
    const main = newMainCheckout();
    givenLocalCheckout(500, main);
    const envLocal =
      "CONVEX_DEPLOYMENT=dev:shared-otter-100 # team: team-a, project: proj-b\nNEXT_PUBLIC_CONVEX_URL=https://shared-otter-100.convex.cloud\n";
    writeFileSync(join(main, ".env.local"), envLocal);
    const timeline = join(stateHome, "timeline");

    const run = devServerIn(main, ["convex-start"], { TIMELINE: timeline });

    expect(run.status).toBe(1);
    expect(run.stderr).toContain(".convex/local is stray state");
    expect(run.stderr).toContain('docs/agents/dev-loop.md "Main checkout"');
    expect(readFileSync(join(main, ".env.local"), "utf8")).toBe(envLocal);
    expect(existsSync(timeline)).toBe(false);
  });

  test("start in a main checkout with stray local state pushes once to its cloud deployment and starts no convex dev", () => {
    const main = newMainCheckout();
    givenLocalCheckout(500, main);
    givenServableCheckout(main);
    const calls = join(stateHome, "pnpm-calls");
    executable(
      join(main, "host-bin", "pnpm"),
      `#!/usr/bin/env bash\necho "pnpm $*" >>${JSON.stringify(calls)}\n`,
    );
    const timeline = join(stateHome, "timeline");

    const run = devServerIn(main, ["start", freePort], { TIMELINE: timeline });

    expect(run.status, run.stderr).toBe(0);
    expect(readFileSync(calls, "utf8")).toBe("pnpm exec convex dev --once\n");
    expect(existsSync(timeline)).toBe(false);
    expect(existsSync(join(main, ".convex", "convex-dev.pid"))).toBe(false);
  }, 30_000);

  test("clear-stale-types in a checkout without .next changes nothing", () => {
    rmSync(join(checkout, ".next"), { force: true, recursive: true });

    const run = devServer("clear-stale-types");

    expect(run.status).toBe(0);
    expect(existsSync(join(checkout, ".next"))).toBe(false);
  });
});
