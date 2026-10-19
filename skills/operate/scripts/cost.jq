# jq definitions for the cost script.

# The price entry for a bare model id: an exact key, or a key followed by a release date. null when the table has none.
def entry_of($prices; $id):
  [$prices.models | to_entries[]
   | select(.key as $k | $id == $k or ($id | startswith($k + "-") and (ltrimstr($k + "-") | test("^[0-9]{8}$"))))]
  | sort_by(.key | length) | last | if . == null then null else .value end;

# The bucket one response is counted in: its model id (with ":fast" when it ran in fast mode),
# plus ":long" when the model has long_prompt rates and the response's prompt is over their threshold.
# Input: {model, input, cache_write_5m, cache_write_1h, cache_read, output} for one response.
def bucket($prices):
  (entry_of($prices; .model | sub(":fast$"; "")) | .long_prompt?) as $long
  | if $long != null and (.input + .cache_write_5m + .cache_write_1h + .cache_read) > $long.over
    then .model + ":long" else .model end;

# The per-token prices for a bucket. ":long" takes the entry's long_prompt rates and ":fast" its
# fast_multiplier. null when the table has no price.
def price_of($prices; $bucket):
  ($bucket | endswith(":long")) as $long
  | ($bucket | sub(":long$"; "")) as $model
  | ($model | endswith(":fast")) as $fast
  | entry_of($prices; $model | sub(":fast$"; "")) as $entry
  | if $entry == null then null
    else (if $long then $entry.long_prompt else $entry end) as $p
      | (if $fast then $entry.fast_multiplier else 1 end) as $m
      | if $m == null or $p == null then null
        else {input: $p.input, cache_write_5m: ($p.cache_write_5m // 0), cache_write_1h: ($p.cache_write_1h // 0),
              cache_read: $p.cache_read, output: $p.output} | map_values(. * $m)
        end
    end;

# Input: {<bucket>: {input, cache_write_5m, cache_write_1h, cache_read, output}} in tokens.
# Output: usd over the priced buckets, token totals, the per-bucket breakdown and the unpriced buckets.
def priced($prices):
  with_entries(.key as $bucket | price_of($prices; $bucket) as $p
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
