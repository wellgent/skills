import { execFileSync } from "node:child_process";
import { basename } from "node:path";

// Copied to e2e/support/output-dir.ts by setup-web-stack, with <project> filled. It asks git for
// the checkout instead of reading import.meta, so it loads whether Playwright reads the config as
// an ES module or as CommonJS.
const checkout = basename(
  execFileSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf8" }).trim(),
);

/**
 * The Playwright output directory of one suite, named by the checkout, so the
 * runs of two worktrees never write into one directory.
 */
const outputDir = (suite: string) => `/tmp/<project>-${suite}-${checkout}`;

export { outputDir };
