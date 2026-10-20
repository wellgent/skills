/*
 * Copied to scripts/audit-prod.ts by setup-web-stack.
 * Reports each critical or high advisory of the production dependencies and
 * always exits 0, so a run learns of an advisory without being stopped by it.
 */
import { spawnSync } from "node:child_process";

type Advisory = {
  module_name: string;
  patched_versions: string;
  severity: string;
  title: string;
  url: string;
  vulnerable_versions: string;
};

const audit = spawnSync("pnpm", ["audit", "--prod", "--json"], {
  encoding: "utf8",
});

const readAdvisories = (stdout: string): Array<Advisory> | null => {
  try {
    const parsed = JSON.parse(stdout) as {
      advisories?: Record<string, Advisory>;
    };
    return parsed.advisories ? Object.values(parsed.advisories) : null;
  } catch {
    // A failed audit prints its error on stderr and no JSON report.
    return null;
  }
};

const serious = readAdvisories(audit.stdout)?.filter(
  (advisory) => advisory.severity === "critical" || advisory.severity === "high",
);
const report =
  serious == null
    ? [
        "advisory check could not run: pnpm audit returned no report",
        (audit.error?.message ?? audit.stderr).trim(),
      ]
    : serious.length === 0
      ? ["no critical or high advisory"]
      : serious.map(
          (advisory) =>
            `advisory (${advisory.severity}): ${advisory.module_name}, ${advisory.title}, affects ${advisory.vulnerable_versions}, fixed in ${advisory.patched_versions}, ${advisory.url}`,
        );
process.stdout.write(`${report.join("\n")}\n`);
