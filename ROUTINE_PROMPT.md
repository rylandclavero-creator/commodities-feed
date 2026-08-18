# Claude routine prompt (paste into the routine, once the repo exists)

Configure the routine with:
  sources:        https://github.com/<YOU>/commodities-feed
  allowed_tools:  Bash, Read, WebSearch
  cron:           45 10 * * 1-5   (UTC = 06:45 America/Toronto during EDT)
  model:          claude-sonnet-5

Prompt:

---
You are producing a pre-market commodities brief. You have no memory of
previous runs. Complete this in one pass - nobody can answer questions.

STEP 1 - Read the data. The repo commodities-feed is cloned into this sandbox.
Find and read data/prices.json (use: find / -name prices.json 2>/dev/null).
This file is refreshed by GitHub Actions before you run.

Do NOT attempt to fetch prices from any website. The sandbox blocks all
market-data hosts. prices.json is your only price source.

STEP 2 - Check freshness. Compare fetched_at_utc to now. If the data is more
than 6 hours old, say so prominently at the top of the brief - it means the
GitHub Action did not run and these numbers are stale.

STEP 3 - Check completeness. If ok_count < total_count, list which commodities
failed and their error text. Never omit a failed commodity silently.

STEP 4 - Write the brief:

# Commodities Brief - <date>

| Commodity | Price | Change | Contract | Quote time (UTC) |

Use price, change_pct, contract and quote_time_utc exactly as given. Do not
round beyond 2 decimals. Do not invent figures for anything with "ok": false.

## What moved
2-4 sentences on the largest movers. Flag any move beyond +/-3% explicitly.
You may use WebSearch ONLY to explain *why* something moved - never to source
a price. Cite any article you rely on.

## Watch today
Scheduled releases or events affecting these five (EIA petroleum status,
EIA natural gas storage, FOMC, CPI). Say "none identified" if you find none.

## Data quality
State the fetch timestamp, ok_count/total_count, and that prices are delayed
and unsuitable for trading decisions. Note anything stale or missing.

Keep under 400 words.
---
