// Read-only engine proof for the reconciler: the source's indexed commit and path, and its stale chunk count.
// Stale chunks come from the engine's own predicate, the one `embed --stale` works from,
// so embed_skip pages and pages held for spend approval do not count. No migrations, no writes.
import { SQL } from 'bun';

const src = process.env.GBRAIN_SRC;
const source = process.env.RECONCILER_SOURCE;
if (!src || !source) throw new Error('GBRAIN_SRC and RECONCILER_SOURCE are required');
const { loadConfig } = await import(`${src}/core/config.ts`);
const { countStaleChunks } = await import(`${src}/core/engine-sql/chunks.ts`);
const { resolveActiveEmbeddingColumnFromEngine } = await import(`${src}/core/search/embedding-column.ts`);

const config = loadConfig();
if (config?.engine !== 'postgres' || !config.database_url) throw new Error('Postgres host required');
const sql = new SQL({ url: config.database_url, max: 1 });
const read = {
  executeRaw: (text: string, params: unknown[] = []) => sql.unsafe(text, params),
  unsafe: async (text: string, params: unknown[] = []) => ({ rows: await sql.unsafe(text, params) }),
};
try {
  const rows = await sql`SELECT last_commit, local_path FROM sources WHERE id = ${source}`;
  const column = await resolveActiveEmbeddingColumnFromEngine(read, { fallbackToLegacy: true });
  const stale = await countStaleChunks(read, column.name, { sourceId: source });
  console.log(JSON.stringify({ indexed_commit: rows[0]?.last_commit, source_path: rows[0]?.local_path, stale_chunks: stale }));
} finally {
  await sql.close();
}
