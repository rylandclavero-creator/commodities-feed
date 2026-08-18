# commodities-feed

Data feed for the Claude "Commodities Morning Brief" routine.

## Why this exists

Claude cloud routines run in a sandbox behind a network egress proxy that
**allowlists** outbound hosts. Every market-data host tested was refused with
`CONNECT tunnel failed, response 403` - Yahoo, stooq, Alpha Vantage, and even
the US government APIs (FRED, EIA). `api.github.com` was the only host
reachable, and `Bash curl` does not bypass the proxy either.

So GitHub Actions does the fetching (unrestricted network) and commits the
result here. The routine clones this repo and reads `data/prices.json`.

    GitHub Actions  --fetch-->  Yahoo Finance
           |
           +--commit-->  data/prices.json
                              |
                     clone (allowlisted)
                              |
                        Claude routine  -->  brief  -->  phone push

## Files

| Path | Purpose |
|---|---|
| `fetch.py` | **Active.** 5 commodities from Yahoo's chart API -> `data/prices.json` |
| `fetch_te.py` | Unused alternative - Trading Economics. See "Source choice" below |
| `.github/workflows/fetch.yml` | Runs `fetch.py` weekdays 10:30 UTC, commits changes |
| `data/prices.json` | Latest quotes - what the routine reads |
| `ROUTINE_PROMPT.md` | The prompt to paste into the Claude routine |

## Symbols

`CL=F` WTI - `NG=F` Henry Hub - `HG=F` Copper - `GC=F` Gold - `SI=F` Silver

These are **front-month futures contracts**, not spot. Label them that way in
the brief - the routine prompt emits a Contract column for exactly this reason.

## Source choice: why Yahoo, not Trading Economics

TE's API now requires a paid plan (guest tier returns HTTP 410). Their public
page is scrapeable, but that is a terms-of-service question for commercial use,
and HTML parsing is more brittle than a JSON API. `fetch_te.py` is kept as a
working reference in case the TE API is licensed later - it emits the identical
`prices.json` shape, so swapping is a one-line change in the workflow.

The two sources disagree and must never be blended. Measured 2026-08-18:

| | Trading Economics (spot) | Yahoo (futures) |
|---|---|---|
| Gold | 4353.99 | 4412.50 (~$60 higher) |
| Crude | +0.55% | -0.51% (opposite sign) |

## Behaviour notes

- Each symbol retries 3x with backoff. Failures are recorded per-commodity as
  `"ok": false` with the error text; they are **not** silently dropped.
- The Action fails only if *all five* fail, so partial data still ships.
- `ok_count` / `total_count` let the routine report degradation honestly.
- Change % is derived from the **daily close series**, not
  `meta.chartPreviousClose` - that field is the close *before the requested
  range window* and reported WTI +3.51% on a day it actually fell 0.47%.
- Prices are delayed. Not suitable for trading decisions.
- Cron is UTC and does not follow DST - revisit this schedule and the Claude
  routine's when the clocks change in November.
