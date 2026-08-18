#!/usr/bin/env python3
"""Fetch commodity quotes from Yahoo Finance and write data/prices.json.

Runs on GitHub Actions (unrestricted network). The Claude routine clones this
repo and reads the JSON, because the routine sandbox cannot reach any
market-data host directly.

NOTE ON CHANGE CALCULATION
Do NOT use meta.chartPreviousClose - it is the close *before the requested
range window*, not the prior trading day. With range=5d it reported WTI
+3.51% on a day the contract actually fell 0.47%. We therefore derive the
prior close from the daily close series instead.
"""
import json, sys, time, urllib.request
from datetime import datetime, timezone

SYMBOLS = {
    "CL=F": ("Crude Oil (WTI)", "USD/bbl"),
    "NG=F": ("Natural Gas (Henry Hub)", "USD/MMBtu"),
    "HG=F": ("Copper", "USD/lb"),
    "GC=F": ("Gold", "USD/oz"),
    "SI=F": ("Silver", "USD/oz"),
}
URL = ("https://query1.finance.yahoo.com/v8/finance/chart/"
       "{sym}?interval=1d&range=10d")
UA = {"User-Agent": "Mozilla/5.0 (commodities-feed; +github-actions)"}


def prior_close(result):
    """Last completed daily close before today's session.

    Returns (close, iso_date) or (None, None). Today's candle is still open,
    so if the final bar is dated today we step back one bar.
    """
    ts = result.get("timestamp") or []
    closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    bars = [(t, c) for t, c in zip(ts, closes) if c is not None]
    if len(bars) < 2:
        return None, None
    today = datetime.now(timezone.utc).date()
    if datetime.fromtimestamp(bars[-1][0], timezone.utc).date() == today:
        bars = bars[:-1]          # drop today's partial bar
    if not bars:
        return None, None
    t, c = bars[-1]
    return c, datetime.fromtimestamp(t, timezone.utc).date().isoformat()


def fetch(sym, attempts=3):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(URL.format(sym=sym), headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                result = json.load(r)["chart"]["result"][0]
            meta = result["meta"]
            price = meta.get("regularMarketPrice")
            if price is None:
                raise ValueError("no regularMarketPrice in response")
            prev, prev_date = prior_close(result)
            chg = round((price - prev) / prev * 100, 2) if prev else None
            return {
                "ok": True,
                "price": round(price, 4),
                "prev_close": round(prev, 4) if prev else None,
                "prev_close_date": prev_date,
                "change_pct": chg,
                "exchange": meta.get("fullExchangeName"),
                "contract": meta.get("shortName"),
                "quote_time_utc": datetime.fromtimestamp(
                    meta["regularMarketTime"], timezone.utc
                ).isoformat() if meta.get("regularMarketTime") else None,
            }
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (i + 1))
    return {"ok": False, "error": last}


def main():
    out = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance chart API (delayed)",
        "change_basis": "vs last completed daily close (see prev_close_date)",
        "commodities": {},
    }
    for sym, (name, unit) in SYMBOLS.items():
        rec = fetch(sym)
        rec.update({"symbol": sym, "name": name, "unit": unit})
        out["commodities"][name] = rec
        detail = (f"{rec['price']:>10}  {rec['change_pct']:>6}%  vs {rec['prev_close']}"
                  f" ({rec['prev_close_date']})" if rec["ok"] else rec["error"])
        print(f"{name:26} {'OK ' if rec['ok'] else 'FAIL'} {detail}", file=sys.stderr)

    ok = sum(1 for c in out["commodities"].values() if c["ok"])
    out["ok_count"], out["total_count"] = ok, len(SYMBOLS)
    with open("data/prices.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote data/prices.json ({ok}/{len(SYMBOLS)} ok)", file=sys.stderr)
    return 1 if ok == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
