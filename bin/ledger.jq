# Shared jq definitions for flow cost and flow ledger.

# The price entry for a model id: an exact key, or a key followed by a release date.
# A ":fast" suffix applies the entry's fast_multiplier. null when the table has no price.
def price_of($prices; $model):
  ($model | endswith(":fast")) as $fast
  | ($model | sub(":fast$"; "")) as $id
  | ([$prices.models | to_entries[]
      | select(.key as $k | $id == $k or ($id | startswith($k + "-") and (ltrimstr($k + "-") | test("^[0-9]{8}$"))))]
     | sort_by(.key | length) | last) as $entry
  | if $entry == null then null
    else $entry.value as $p
      | (if $fast then $p.fast_multiplier else 1 end) as $m
      | if $m == null then null
        else {input: $p.input, cache_write_5m: ($p.cache_write_5m // 0), cache_write_1h: ($p.cache_write_1h // 0),
              cache_read: $p.cache_read, output: $p.output} | map_values(. * $m)
        end
    end;

# Input: {<model>: {input, cache_write_5m, cache_write_1h, cache_read, output}} in tokens.
# Output: the cost object of a ledger row. usd covers the priced models only.
def priced($prices):
  with_entries(.key as $model | price_of($prices; $model) as $p
    | .value += {usd: (if $p == null then null
        else ((.value.input * $p.input + .value.cache_write_5m * $p.cache_write_5m
               + .value.cache_write_1h * $p.cache_write_1h + .value.cache_read * $p.cache_read
               + .value.output * $p.output) / 1000000 * 10000 | round / 10000)
        end)})
  | {usd: ([.[].usd | select(. != null)] | add // 0 | . * 10000 | round / 10000),
     tokens: {input: ([.[].input] | add // 0),
              cache_write: ([.[] | .cache_write_5m + .cache_write_1h] | add // 0),
              cache_read: ([.[].cache_read] | add // 0),
              output: ([.[].output] | add // 0)},
     models: .,
     unpriced: [to_entries[] | select(.value.usd == null) | .key],
     prices_as_of: $prices.as_of};

def epoch: sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601;
