import { basename } from "node:path";
import { fileURLToPath } from "node:url";

// Copied to e2e/support/output-dir.ts by setup-web-stack, with <project> filled.
const checkout = basename(fileURLToPath(new URL("../..", import.meta.url)));

/**
 * The Playwright output directory of one suite, named by the checkout, so the
 * runs of two worktrees never write into one directory.
 */
const outputDir = (suite: string) => `/tmp/<project>-${suite}-${checkout}`;

export { outputDir };
