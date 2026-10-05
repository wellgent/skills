#!/usr/bin/env bash
# Copy one reviewer's own records from production into a prototype's preview deployment.
# It reads production, so the lead runs it. The tables are the client-approved allowlist
# on the project card; the read function refuses any table outside it.
#
# usage: scripts/prototype-copy.sh <preview deployment name> <owner> <table>...
set -euo pipefail

READ_FUNCTION="<internal query, e.g. prototype/copy:read>"    # {owner, table} -> rows
WRITE_FUNCTION="<internal mutation, e.g. prototype/copy:write>" # {owner, table, rows}, refuses outside a preview

[ $# -ge 3 ] || { echo "usage: $0 <preview deployment name> <owner> <table>..." >&2; exit 64; }
target=$1 owner=$2
shift 2

for table in "$@"; do
  args=$(jq -nc --arg owner "$owner" --arg table "$table" '{owner: $owner, table: $table}')
  rows=$(pnpm exec convex run --prod "$READ_FUNCTION" "$args")
  count=$(jq 'length' <<<"$rows")
  pnpm exec convex run --deployment "$target" "$WRITE_FUNCTION" \
    "$(jq -nc --argjson base "$args" --argjson rows "$rows" '$base + {rows: $rows}')" >/dev/null
  echo "$table: $count"
done
