// Database-only timeline rows: timeline_entries rows with no bullet in their page.
//   bun timeline-db-only.ts list          rows the engine's own classifier calls materializable, one row at a time
//   bun timeline-db-only.ts drop <ids>    delete exactly those ids in one transaction, rolled back unless every id is deleted
// GBRAIN_SRC is the engine source, HEALTH_SOURCE the source id. Prints one JSON object.
import { readFileSync } from 'node:fs';

const src = process.env.GBRAIN_SRC;
const source = process.env.HEALTH_SOURCE;
const [mode, idsFile] = process.argv.slice(2);
if (!src || !source) throw new Error('GBRAIN_SRC and HEALTH_SOURCE are required');
if (mode !== 'list' && !(mode === 'drop' && idsFile)) throw new Error('usage: timeline-db-only.ts list | drop <ids.json>');

const { loadConfig, toEngineConfig } = await import(`${src}/core/config.ts`);
const { createEngine } = await import(`${src}/core/engine-factory.ts`);
const engineConfig = toEngineConfig(loadConfig());
const engine = await createEngine(engineConfig);
await engine.connect(engineConfig);

try {
  if (mode === 'list') {
    const { scanTimelineHistory } = await import(`${src}/core/repair/timeline.ts`);
    const { pendingTimelineRows } = await import(`${src}/core/persistence/canonical-projections.ts`);
    const { retractRemovedTimelineEntries } = await import(`${src}/core/timeline-extract.ts`);
    const { pages } = await scanTimelineHistory(engine, [source], 0);
    const rows: Array<{ id: number; slug: string; date: string; summary: string }> = [];
    let expected = 0, unrenderable = 0;
    for (const p of pages) {
      unrenderable += p.unrenderable;
      if (!p.materializable) continue;
      expected += p.materializable;
      const page = { ...p, timeline: p.timeline ?? '' };
      // Rows an earlier version of the page produced are removals, handled by extract, not by this rule.
      const removed = new Set((await retractRemovedTimelineEntries(engine, p.slug, p.source_id, `${p.compiled_truth}\n${page.timeline}`, { dryRun: true }))
        .map((r: { id: number }) => Number(r.id)));
      const stored = await engine.executeRaw<{ id: number; date: string; summary: string }>(
        `SELECT id, to_char(date, 'YYYY-MM-DD') AS date, summary FROM timeline_entries WHERE page_id = $1 AND event_page_id IS NULL`, [p.id]);
      const all = stored.map(r => Number(r.id));
      for (const row of stored) {
        const id = Number(row.id);
        if (removed.has(id)) continue;
        const { materializable } = await pendingTimelineRows(engine, page, new Set(all.filter(x => x !== id)));
        if (materializable === 1) rows.push({ id, slug: p.slug, date: row.date, summary: row.summary });
      }
    }
    console.log(JSON.stringify({ pages: pages.filter((p: { materializable: number }) => p.materializable).length, expected, unrenderable, rows }));
  } else {
    const ids: number[] = JSON.parse(readFileSync(idsFile, 'utf8')).map(Number);
    const deleted = await engine.transaction(async (tx: typeof engine) => {
      const gone = await tx.executeRaw<{ id: number }>(
        'DELETE FROM timeline_entries WHERE event_page_id IS NULL AND id = ANY($1::bigint[]) RETURNING id', [ids]);
      if (gone.length !== ids.length) throw new Error(`expected to delete ${ids.length} rows, matched ${gone.length}; rolled back`);
      return gone.length;
    });
    console.log(JSON.stringify({ deleted }));
  }
} finally {
  await engine.disconnect();
}
