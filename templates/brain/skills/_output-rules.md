# Output Rules

Brain pages are durable source artifacts, not chat replies.

## Deterministic links

All links in brain pages must be deterministic and built from actual paths, slugs, commit hashes, or API responses.

- Brain page links: `[Title](../directory/page.md)` or `[Title](directory/page.md)` depending on relative location.
- Commit links: use the actual remote URL and commit hash.
- External links: use the actual URL from the source, never reconstruct it.

## No slop

- No filler phrases.
- No hedging when a fact is cited.
- No LLM preamble.
- No placeholder dates.
- Short paragraphs.
- Concrete claims.
- Inline citations on durable facts.

## Exact phrasing

When capturing original thinking, use {{owner}}'s exact words. Do not clean up grammar or sanitize the terminology when the wording is the insight.

## Title quality

Titles should be short, searchable, and specific. Avoid generic titles such as "Notes" or sentence-length titles.
