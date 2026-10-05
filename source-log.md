# Source log

Every upstream source the flow depends on, with the last version seen and its date.
Readiness reviews every source here against its upstream; `flow sources` runs the comparison and `flow sources seen` records a review.
A source the flow starts to depend on gets a section here in the same change.

- **Upstream** is what `flow sources` reads: `release:<owner>/<repo>` (latest release tag), `git:<owner>/<repo>[:<path>]` (latest commit, under the path when given), `npm:<package>`, `brew:<formula>`, or `url:<page>` for a page a person reads.
- **Seen** is the version last reviewed and the day of the review.
- **Pin**, on a source of pinned skills, is the commit every brain and project pins that source at.
- **Skipped** lists what the client declined, each with its reason. A skip is raised again only when upstream changes it.

## mattpocock/skills

- **Upstream:** `release:mattpocock/skills`
- **Seen:** `v1.3.1`, 2026-10-05
- **Pin:** `24fe0ef7737efae15c87225755e9f6f5965e4888`
- **Used by:** the lead (`wayfinder`, `grilling`, `research`, `triage`, `to-spec`, `retro`, `writing-for-agents`), Grooming (`to-tickets`), System design (`codebase-design`, `domain-modeling`), UX design (`prototype`), Build (`implement-spec`, `implement`, `tdd`, `code-review`, `diagnosing-bugs`), Review (`code-review`), Audit (`improve-codebase-architecture`). The required sets are in `setup/requires.json`.
- **Skipped:** `pr`: the flow lands by fast-forward, without pull requests.

## pbakaus/impeccable

- **Upstream:** `git:pbakaus/impeccable:skill`
- **Seen:** `4bc74df2e34c170fb63f106a9d80dee42e9abcc0`, 2026-10-05
- **Pin:** `4bc74df2e34c170fb63f106a9d80dee42e9abcc0`
- **Used by:** UX design (`impeccable`), and the design scanner line of `docs/agents/dev-loop.md`.

## vercel-labs/agent-skills

- **Upstream:** `git:vercel-labs/agent-skills:skills`
- **Seen:** `0c04547b953d49d5e91f512a7c4a6ecfcb3a7055`, 2026-10-05
- **Pin:** `0c04547b953d49d5e91f512a7c4a6ecfcb3a7055`
- **Used by:** the web catalog's Review and Audit lenses and the Vercel CLI skill.

## vercel/next.js

- **Upstream:** `git:vercel/next.js:skills`
- **Seen:** `3452ebbcf93236ef9b9c6c1db5e2d706d722deb9`, 2026-10-05
- **Pin:** `3452ebbcf93236ef9b9c6c1db5e2d706d722deb9`
- **Used by:** the web catalog's `next-dev-loop` QA tool and the situational Next.js skills.

## get-convex/agent-skills

- **Upstream:** `git:get-convex/agent-skills:skills`
- **Seen:** `2cfe645c87f971242cfc8ef3eb53662cbec26a53`, 2026-10-05
- **Pin:** `2cfe645c87f971242cfc8ef3eb53662cbec26a53`
- **Used by:** the web catalog's Convex must-read entries and Review lens.

## upstash/context7

- **Upstream:** `git:upstash/context7:skills`
- **Seen:** `76140fc35897cf34ca4503b726b77a90c8fa4915`, 2026-10-05
- **Pin:** `76140fc35897cf34ca4503b726b77a90c8fa4915`
- **Used by:** the web catalog's `find-docs` must-read entry.

## vercel-labs/agent-browser

- **Upstream:** `git:vercel-labs/agent-browser:skills`
- **Seen:** `021d9255e543d2f1ab66b87f338d85c3d7a910be`, 2026-10-05
- **Pin:** `021d9255e543d2f1ab66b87f338d85c3d7a910be`
- **Used by:** the web catalog's `agent-browser` QA tool (the skill stub; the CLI is its own source below).

## Claude Code

- **Upstream:** `npm:@anthropic-ai/claude-code`
- **Seen:** `2.1.289`, 2026-10-05
- **Used by:** the harness of every `claude-*` step and of the lead. Read its release notes for new native controls in a stage's area.

## Codex

- **Upstream:** `npm:@openai/codex`
- **Seen:** `0.160.0`, 2026-10-05
- **Used by:** the harness of every `gpt-*` step. Read its release notes the same way.

## herdr

- **Upstream:** `brew:herdr`
- **Seen:** `0.9.3`, 2026-10-05
- **Used by:** `flow spawn`, `flow report`, `flow ask` and `flow tick`.

## skills CLI

- **Upstream:** `npm:skills`
- **Seen:** `1.7.0`, 2026-10-05
- **Used by:** the setup skills' pins (`npx skills add <source>#<sha>`).

## agent-browser CLI

- **Upstream:** `npm:agent-browser`
- **Seen:** `0.38.2`, 2026-10-05
- **Used by:** QA's exploratory pass.

## Playwright

- **Upstream:** `npm:@playwright/test`
- **Seen:** `1.63.0`, 2026-10-05
- **Used by:** the journey tests.

## knip

- **Upstream:** `npm:knip`
- **Seen:** `6.39.0`, 2026-10-05
- **Used by:** the check command and the scanner pass.

## oxlint

- **Upstream:** `npm:oxlint`
- **Seen:** `1.87.0`, 2026-10-05
- **Used by:** the check command.

## oxfmt

- **Upstream:** `npm:oxfmt`
- **Seen:** `0.72.0`, 2026-10-05
- **Used by:** the check command.

## @nkzw/oxlint-config

- **Upstream:** `npm:@nkzw/oxlint-config`
- **Seen:** `2.0.1`, 2026-10-05
- **Used by:** the lint preset.

## dependency-cruiser

- **Upstream:** `npm:dependency-cruiser`
- **Seen:** `18.5.0`, 2026-10-05
- **Used by:** the check command's dependency rules and the scanner pass.

## jscpd

- **Upstream:** `npm:jscpd`
- **Seen:** `5.4.0`, 2026-10-05
- **Used by:** the scanner pass's duplication measures.

## react-doctor

- **Upstream:** `npm:react-doctor`
- **Seen:** `0.9.17`, 2026-10-05
- **Used by:** the scanner pass's `react_doctor` measure.

## TypeScript

- **Upstream:** `npm:typescript`
- **Seen:** `7.0.2`, 2026-10-05
- **Used by:** the check command.

## Vitest

- **Upstream:** `npm:vitest`
- **Seen:** `5.0.3`, 2026-10-05
- **Used by:** the check command's tests.

## Next.js

- **Upstream:** `npm:next`
- **Seen:** `16.3.8`, 2026-10-05
- **Used by:** the web doctrine's framework stance and its bundled agent docs.

## Convex

- **Upstream:** `npm:convex`
- **Seen:** `1.46.0`, 2026-10-05
- **Used by:** the web doctrine's data layer, the worktree and prototype recipes, and the guidelines file a toolchain sweep refreshes.

## @convex-dev/eslint-plugin

- **Upstream:** `npm:@convex-dev/eslint-plugin`
- **Seen:** `5.0.0`, 2026-10-05
- **Used by:** the Convex lint rules inside the check command.

## @convex-dev/migrations

- **Upstream:** `npm:@convex-dev/migrations`
- **Seen:** `0.3.6`, 2026-10-05
- **Used by:** production migrations and their `dryRun`.

## convex-test

- **Upstream:** `npm:convex-test`
- **Seen:** `0.0.60`, 2026-10-05
- **Used by:** the Convex seam tests.

## Vercel CLI

- **Upstream:** `npm:vercel`
- **Seen:** `62.2.0`, 2026-10-05
- **Used by:** Release and the prototype deploy.

## Vercel changelog

- **Upstream:** `url:https://vercel.com/changelog`
- **Seen:** `2026-10-05`, 2026-10-05
- **Used by:** new platform tools in the Review, QA and Release areas.

## Claude API pricing

- **Upstream:** `url:https://platform.claude.com/docs/en/about-claude/pricing`
- **Seen:** `2026-10-05`, 2026-10-05
- **Used by:** `ledger/prices.json`. A new model id needs a price entry before its runs can be costed.

## OpenAI API pricing

- **Upstream:** `url:https://developers.openai.com/api/docs/pricing`
- **Seen:** `2026-10-05`, 2026-10-05
- **Used by:** `ledger/prices.json`, the same way.
