// @vitest-environment node
import { spawn, spawnSync } from "node:child_process";
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
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, test } from "vitest";

const scriptsDir = import.meta.dirname;

const SHARED_DEPLOYMENT_LINE =
  "CONVEX_DEPLOYMENT=dev:shared-otter-100 # team: team-a, project: proj-b";

// The committed Convex team and project, from scripts/host-claims.sh.
const convexProject = (() => {
  const line = /^CONVEX_PROJECT="?([^"\s]+)"?$/m.exec(
    readFileSync(join(scriptsDir, "host-claims.sh"), "utf8"),
  );
  if (line === null) {
    throw new Error("scripts/host-claims.sh names no CONVEX_PROJECT");
  }
  return line[1];
})();
const CREATE_LOCAL = `pnpm exec convex deployment create ${convexProject}:local --select`;
const GET_DEFAULT_CRONS = `pnpm exec convex env default get CRONS --type dev --project ${convexProject}`;

// Ports the system just handed out and released, so no process holds them.
const releasedPorts = async () => {
  const servers = [createServer(), createServer()];
  await Promise.all(
    servers.map(
      (server) => new Promise<void>((resolve) => server.listen(0, resolve)),
    ),
  );
  const ports = servers.map((server) => {
    const address = server.address();
    if (address === null || typeof address === "string") {
      throw new Error("the released port has no number");
    }
    return String(address.port);
  });
  await Promise.all(
    servers.map((server) => new Promise((resolve) => server.close(resolve))),
  );
  return ports;
};

const executable = (path: string, body: string) => {
  writeFileSync(path, body);
  chmodSync(path, 0o755);
};

const git = (cwd: string, ...args: Array<string>) => {
  const run = spawnSync("git", args, { cwd, encoding: "utf8" });
  expect(run.status, run.stderr).toBe(0);
};

// A linked worktree of the main checkout holding the script and the claims it
// sources, with a stub `scripts/dev-server.sh` that logs each call, on
// convex-start names the backend it serves in .env.local as the real one does
// and, when TIMELINE names a file, appends its convex-start there after a second.
const addWorktree = (path: string) => {
  git(main, "worktree", "add", "-q", "--detach", path);
  mkdirSync(join(path, "scripts"));
  for (const name of ["worktree-setup.sh", "host-claims.sh"]) {
    copyFileSync(join(scriptsDir, name), join(path, "scripts", name));
  }
  executable(
    join(path, "scripts", "dev-server.sh"),
    `#!/usr/bin/env bash
echo "dev-server.sh $*" >>${JSON.stringify(log)}
if [ "$1" = convex-start ]; then
  echo "CONVEX_SELF_HOSTED_URL=http://127.0.0.1:$CLOUD_PORT" >>.env.local
fi
if [ -n "$TIMELINE" ]; then
  sleep 1
  echo "$(basename "$PWD") dev-server.sh $*" >>"$TIMELINE"
fi
`,
  );
};

// A main checkout on the shared cloud dev deployment and a linked worktree,
// with a `pnpm` on PATH that logs each call. The stub `convex deployment
// create` fails unless the test lets it succeed, when it writes a local
// deployment on CLOUD_PORT and SITE_PORT as the CLI does; a `server-error`
// create fails as the Convex API's 500 does, every time or
// (`server-error-once`) on the first call only. With TAKER set, another
// checkout's backend takes CLOUD_PORT once the create exits and writes its pid
// to TAKER. A `convex env` or `convex run` call on a local deployment no
// backend serves yet starts one on the config's ports with no check, as the
// CLI does: it logs that start and fails as the CLI does when another backend
// answers there. `convex env default get CRONS` prints DEFAULT_CRONS. With
// TIMELINE set, the stub appends each Convex call that starts a local backend
// there, the create after a second.
let scratch: string;
let main: string;
let worktree: string;
let hostBin: string;
let log: string;
let ports: Array<string>;
let taker: string;
beforeEach(async () => {
  ports = await releasedPorts();
  scratch = realpathSync(mkdtempSync(join(tmpdir(), "<project name>-worktree-setup-")));
  main = join(scratch, "main");
  worktree = join(scratch, "worktree");
  hostBin = join(scratch, "host-bin");
  log = join(scratch, "calls.log");
  taker = join(scratch, "taker.pid");
  mkdirSync(main);
  mkdirSync(hostBin);
  git(main, "init", "-q");
  git(
    main,
    "-c",
    "user.name=Test",
    "-c",
    "user.email=test@example.com",
    "commit",
    "-q",
    "--allow-empty",
    "-m",
    "init",
  );
  writeFileSync(join(main, ".env.local"), `${SHARED_DEPLOYMENT_LINE}\n`);
  addWorktree(worktree);
  executable(
    join(hostBin, "pnpm"),
    `#!/usr/bin/env bash
echo "pnpm $*" >>${JSON.stringify(log)}
case "$*" in
  "exec convex deployment create "*|"exec convex env set "*)
    if [ -n "$TIMELINE" ]; then
      case "$*" in *create*) sleep 1 ;; esac
      echo "$(basename "$PWD") pnpm $*" >>"$TIMELINE"
    fi
    ;;
esac
case "$*" in
  "exec convex env default get CRONS "*)
    echo "$DEFAULT_CRONS"
    ;;
  "exec convex env "*|"exec convex run "*)
    if ! grep -q '^CONVEX_SELF_HOSTED_URL=' .env.local && grep -q '^CONVEX_DEPLOYMENT=local:' .env.local; then
      port=$(jq -r .ports.cloud .convex/local/default/config.json)
      echo "pnpm $* started a backend on port $port" >>${JSON.stringify(log)}
      if other=$(curl -sf "http://127.0.0.1:$port/instance_name"); then
        echo "A different local backend $other is running on selected port $port" >&2
        exit 1
      fi
    fi
    ;;
  "exec convex deployment create "*)
    server_error() {
      echo "Error fetching POST https://api.convex.dev/api/local_deployment/start 500 Internal Server Error" >&2
      exit 1
    }
    case "$CREATE" in
      succeed) ;;
      server-error) server_error ;;
      server-error-once)
        [ -f "$SCRATCH/server-error-sent" ] || { touch "$SCRATCH/server-error-sent"; server_error; } ;;
      *) echo "create failed" >&2; exit 1 ;;
    esac
    mkdir -p .convex/local/default
    printf '{"deploymentName": "local-test", "ports": {"cloud": %s, "site": %s}}\n' "$CLOUD_PORT" "$SITE_PORT" >.convex/local/default/config.json
    echo "CONVEX_DEPLOYMENT=local:local-test # team: team-a, project: proj-b" >>.env.local
    if [ -n "$TAKER" ]; then
      nohup node -e "require('node:http').createServer((q, r) => r.end(q.url === '/instance_name' ? 'other-checkout' : '')).listen($CLOUD_PORT, '127.0.0.1', () => require('node:fs').writeFileSync('$TAKER', String(process.pid)))" >/dev/null 2>&1 3>&- &
      until [ -s "$TAKER" ]; do sleep 0.1; done
    fi
    ;;
esac
`,
  );
});
afterEach(() => {
  if (existsSync(taker)) {
    process.kill(Number(readFileSync(taker, "utf8")));
  }
  rmSync(scratch, { force: true, recursive: true });
});

type Create = "fail" | "server-error" | "server-error-once" | "succeed";

const setupEnv = (
  create: Create,
  extra: Partial<Record<"DEFAULT_CRONS" | "TAKER" | "TIMELINE", string>> = {},
) => ({
  ...process.env,
  CLOUD_PORT: ports[0],
  CREATE: create,
  DEFAULT_CRONS: "off",
  PATH: `${hostBin}:${process.env.PATH}`,
  SCRATCH: scratch,
  SITE_PORT: ports[1],
  TAKER: "",
  TIMELINE: "",
  XDG_STATE_HOME: join(scratch, "state"),
  ...extra,
});

const setup = (
  create: Create = "fail",
  extra: Parameters<typeof setupEnv>[1] = {},
) => {
  const run = spawnSync("bash", ["scripts/worktree-setup.sh"], {
    cwd: worktree,
    encoding: "utf8",
    env: setupEnv(create, extra),
  });
  return { status: run.status, stderr: run.stderr };
};

// Runs the setup without blocking, so two worktrees can run it at once.
const setupAsync = (path: string, timeline: string) =>
  new Promise<number | null>((resolve) => {
    const run = spawn("bash", ["scripts/worktree-setup.sh"], {
      cwd: path,
      env: setupEnv("succeed", { TIMELINE: timeline }),
      stdio: "ignore",
    });
    run.on("close", resolve);
  });

const calls = () =>
  existsSync(log) ? readFileSync(log, "utf8").trim().split("\n") : [];

const envLocal = () => readFileSync(join(worktree, ".env.local"), "utf8");

const creates = () =>
  calls().filter((call) =>
    call.startsWith("pnpm exec convex deployment create"),
  );

const SERVER_ERROR = "local_deployment/start 500 Internal Server Error";

const DEPLOYMENT_CALLS = [
  "pnpm exec convex env set CRONS off",
  "pnpm exec convex dev --once",
  "pnpm exec convex run <seed function, e.g. seed:run>",
];

describe("scripts/worktree-setup.sh", () => {
  test("a first setup reads CRONS=off from the project's dev defaults, creates and selects a local deployment in the committed team and project, then starts convex dev and seeds", () => {
    const run = setup("succeed");

    expect(run.status, run.stderr).toBe(0);
    expect(calls()).toEqual([
      "pnpm install --frozen-lockfile",
      GET_DEFAULT_CRONS,
      CREATE_LOCAL,
      "dev-server.sh convex-start",
      "pnpm exec convex run <seed function, e.g. seed:run>",
    ]);
    expect(envLocal()).not.toMatch(/^CONVEX_DEPLOYMENT=dev:/m);
  });

  test("a first setup completes when another checkout's backend takes the create's port before the next step, since nothing starts a backend between the create and convex-start", () => {
    const run = setup("succeed", { TAKER: taker });

    expect(run.status, run.stderr).toBe(0);
    expect(existsSync(taker)).toBe(true);
    const create = calls().indexOf(CREATE_LOCAL);
    const start = calls().indexOf("dev-server.sh convex-start");
    expect(create).toBeGreaterThan(-1);
    expect(start).toBeGreaterThan(create);
    expect(
      calls().filter((call) => call.includes("started a backend on port")),
    ).toEqual([]);
  });

  test("a first setup refuses before it creates when the project's dev defaults set no CRONS=off", () => {
    const run = setup("succeed", { DEFAULT_CRONS: "" });

    expect(run.status).toBe(1);
    expect(run.stderr).toContain("dev defaults set no CRONS=off");
    expect(calls()).toEqual([
      "pnpm install --frozen-lockfile",
      GET_DEFAULT_CRONS,
    ]);
  });

  test("a first setup creates its local deployment in the committed team and project when the main checkout's .env.local names no CONVEX_DEPLOYMENT", () => {
    writeFileSync(
      join(main, ".env.local"),
      [
        "NEXT_PUBLIC_CONVEX_URL=http://127.0.0.1:3210",
        "# The Convex CLI of this checkout reaches only its local backend (scripts/dev-server.sh).",
        "CONVEX_SELF_HOSTED_URL=http://127.0.0.1:3210",
        "",
      ].join("\n"),
    );

    const run = setup("succeed");

    expect(run.status, run.stderr).toBe(0);
    expect(creates()).toEqual([CREATE_LOCAL]);
  });

  test("a first setup whose create fails other than by a server error leaves no cloud deployment in .env.local, and its rerun creates again once without pushing or seeding", () => {
    const first = setup();

    expect(first.status).not.toBe(0);
    expect(
      existsSync(join(worktree, ".env.local")) ? envLocal() : "",
    ).not.toMatch(/^CONVEX_DEPLOYMENT=dev:/m);

    const rerun = setup();

    expect(rerun.status).not.toBe(0);
    expect(creates()).toHaveLength(2);
    expect(calls().filter((call) => DEPLOYMENT_CALLS.includes(call))).toEqual(
      [],
    );
  });

  test("a first setup whose create meets a Convex server error once creates again and completes on the local backend", () => {
    const run = setup("server-error-once");

    expect(run.status, run.stderr).toBe(0);
    expect(run.stderr).toContain(SERVER_ERROR);
    expect(calls()).toEqual([
      "pnpm install --frozen-lockfile",
      GET_DEFAULT_CRONS,
      CREATE_LOCAL,
      CREATE_LOCAL,
      "dev-server.sh convex-start",
      "pnpm exec convex run <seed function, e.g. seed:run>",
    ]);
    expect(envLocal()).toMatch(/^CONVEX_DEPLOYMENT=local:/m);
  }, 15_000);

  test("a first setup whose create meets a Convex server error twice fails with both errors and names no deployment in .env.local", () => {
    const run = setup("server-error");

    expect(run.status).not.toBe(0);
    expect(run.stderr.split(SERVER_ERROR)).toHaveLength(3);
    expect(creates()).toHaveLength(2);
    expect(calls()).not.toContain("dev-server.sh convex-start");
    expect(calls().filter((call) => DEPLOYMENT_CALLS.includes(call))).toEqual(
      [],
    );
    expect(
      existsSync(join(worktree, ".env.local")) ? envLocal() : "",
    ).not.toMatch(/^CONVEX_DEPLOYMENT=/m);
  }, 15_000);

  test("a rerun on a worktree whose .env.local names a cloud dev deployment without its own deploy key refuses before it sets env, pushes or seeds", () => {
    writeFileSync(join(worktree, ".env.local"), `${SHARED_DEPLOYMENT_LINE}\n`);

    const run = setup();

    expect(run.status).toBe(1);
    expect(run.stderr).toContain("names no deployment of this worktree's own");
    expect(calls()).toEqual(["pnpm install --frozen-lockfile"]);
  });

  test("a rerun on a worktree with a cloud dev deployment and its own deploy key sets CRONS off, pushes and seeds", () => {
    writeFileSync(
      join(worktree, ".env.local"),
      [
        "CONVEX_DEPLOYMENT=dev:own-heron-200 # team: team-a, project: proj-b",
        "CONVEX_DEPLOY_KEY=dev:own-heron-200|secret",
        "",
      ].join("\n"),
    );

    const run = setup();

    expect(run.status, run.stderr).toBe(0);
    expect(calls()).toEqual([
      "pnpm install --frozen-lockfile",
      ...DEPLOYMENT_CALLS,
    ]);
  });

  test("two first setups at once create and start one local backend at a time", async () => {
    const second = join(scratch, "second");
    addWorktree(second);
    const timeline = join(scratch, "timeline.log");

    const statuses = await Promise.all(
      [worktree, second].map((path) => setupAsync(path, timeline)),
    );

    expect(statuses).toEqual([0, 0]);
    const owners = readFileSync(timeline, "utf8")
      .trim()
      .split("\n")
      .map((line) => line.split(" ")[0]);
    expect(owners).toHaveLength(4);
    expect(owners.slice(0, 2)).toEqual(Array(2).fill(owners[0]));
    expect(owners.slice(2)).toEqual(Array(2).fill(owners[2]));
  }, 30_000);
});
