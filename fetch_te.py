#!/usr/bin/env python3
"""Alternative fetcher: Trading Economics public commodities page.

WHY THIS EXISTS
TE's API now requires a paid plan - the guest tier returns HTTP 410
("the guest account has been discontinued") and unauthenticated returns 401.
This script parses their public HTML page instead.

READ BEFORE USING COMMERCIALLY
TE sells this data as an API product. Scraping the free page to power a
paid client deliverable is a terms-of-service question, not a technical one.
For a client engagement either license the TE API and swap in the endpoint
below, or use fetch.py (Yahoo) instead. This file is fine for a demo.

TE quotes SPOT for the metals; fetch.py (Yahoo) quotes FUTURES contracts.
They disagree - gold differed by ~$60 and crude by opposite sign on
2026-08-18. Never blend the two in one brief.
"""
import html, json, re, sys, time, urllib.request
from datetime import datetime, timezone

URL = "https://tradingeconomics.com/commodities"
UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126 Safari/537.36")}
WANT = ["Crude Oil", "Natural gas", "Copper", "Gold", "Silver"]


def get_page(attempts=3):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(URL, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"could not fetch {URL}: {last}")


def parse_row(page, name):
    m = re.search(r'<tr[^>]*>(?:(?!</tr>).)*?>' + re.escape(name)
                  + r'\s*<(?:(?!</tr>).)*?</tr>', page, re.S | re.I)
    if not m:
        return {"ok": False, "error": "row not found - TE markup may have changed"}
    cells = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip()
             for c in re.findall(r'<td[^>]*>(.*?)</td>', m.group(0), re.S)]
    cells = [c for c in cells if c]
    if len(cells) < 4:
        return {"ok": False, "error": f"only {len(cells)} cells parsed"}
    label = re.sub(r'\s+', ' ', cells[0])
    unit = label.split()[-1] if "/" in label.split()[-1] else None
    try:
        price = float(cells[1].replace(",", ""))
        chg_pct = float(cells[3].rstrip("%"))
    except ValueError as e:
        return {"ok": False, "error": f"unparseable numbers {cells[1:4]}: {e}"}
    return {"ok": True, "price": price, "change_pct": chg_pct,
            "abs_change": cells[2], "unit": unit, "quote_convention": "spot"}


def main():
    out = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(),
           "source": "Trading Economics public page (delayed, spot)",
           "change_basis": "TE daily % as published",
           "commodities": {}}
    try:
        page = get_page()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    for name in WANT:
        rec = parse_row(page, name)
        rec["name"] = name
        out["commodities"][name] = rec
        print(f"{name:14} {'OK ' if rec['ok'] else 'FAIL'} "
              f"{rec.get('price', rec.get('error'))} "
              f"{str(rec.get('change_pct',''))+'%' if rec['ok'] else ''}",
              file=sys.stderr)
    ok = sum(1 for c in out["commodities"].values() if c["ok"])
    out["ok_count"], out["total_count"] = ok, len(WANT)
    with open("data/prices.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote data/prices.json ({ok}/{len(WANT)} ok)", file=sys.stderr)
    return 1 if ok == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
