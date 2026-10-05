#!/usr/bin/env bash
# Copy one reviewer's own records from production into a prototype's preview deployment.
# It reads production, so the lead runs it from the main checkout's root, where the host's
# Convex login reaches production; a deploy key in scope would send --prod to its own
# deployment. The tables are the client-approved allowlist on the project card; the read
# function refuses any table the copy does not carry. The write takes every table in one
# transaction, so the ids rows share across tables are remapped together, and it lands
# once per preview deployment. The rows travel as one command-line argument, so a copy is
# capped by the OS argument limit (about 1 MiB on macOS, 128 KiB per argument on Linux).
#
# usage: scripts/prototype-copy.sh <preview deployment name> <owner> <table>...
set -euo pipefail

READ_FUNCTION="<internal query, e.g. prototype/copy:read>"    # {owner, table} -> rows
WRITE_FUNCTION="<internal mutation, e.g. prototype/copy:write>" # {owner, tables}, refuses outside a preview

[ $# -ge 3 ] || { echo "usage: $0 <preview deployment name> <owner> <table>..." >&2; exit 64; }
if [ -n "${CONVEX_DEPLOY_KEY:-}" ] || grep -qs '^CONVEX_DEPLOY_KEY=' .env.local; then
  echo "$0: a CONVEX_DEPLOY_KEY is in scope, so --prod would not reach production; run it from the main checkout" >&2
  exit 1
fi
target=$1 owner=$2
shift 2

tables='{}'
for table in "$@"; do
  args=$(jq -nc --arg owner "$owner" --arg table "$table" '{owner: $owner, table: $table}')
  rows=$(pnpm exec convex run --prod "$READ_FUNCTION" "$args")
  echo "$table: $(jq 'length' <<<"$rows") read"
  tables=$(jq -c --arg table "$table" --argjson rows "$rows" '. + {($table): $rows}' <<<"$tables")
done

pnpm exec convex run --deployment "$target" "$WRITE_FUNCTION" \
  "$(jq -nc --arg owner "$owner" --argjson tables "$tables" '{owner: $owner, tables: $tables}')"
