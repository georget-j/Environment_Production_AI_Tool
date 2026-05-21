"""Fetch + bundle the market-data CSVs used by the Quant track.

Run when the dataset needs refreshing (annually is plenty):

    source apps/api/.venv/bin/activate  # has yfinance
    python scripts/fetch_quant_data.py

Writes one CSV per ticker into apps/web/public/data/quant/, plus a
README.md noting provenance. Each CSV has the same columns:

    date,open,high,low,close,adj_close,volume

so lessons can pd.read_csv("/data/quant/spy.csv") and not worry about
adapter shims. Daily resolution, UTC.

yfinance is a dev/build-time dependency only — it is NOT in the API's
production requirements.txt, only installed into the local venv so this
script can run.
"""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "apps" / "web" / "public" / "data" / "quant"

# 2015-01-01 → end of 2025 gives ~10 years of daily data per ticker.
# 5 broad-market ETFs + Apple + crypto = a useful palette for lessons.
START = date(2015, 1, 1)
END = date(2026, 1, 1)
TICKERS: list[tuple[str, str]] = [
    ("SPY", "spy"),       # S&P 500 ETF
    ("AAPL", "aapl"),     # Apple, the single-stock example
    ("QQQ", "qqq"),       # Nasdaq-100 ETF (tech-heavy)
    ("TLT", "tlt"),       # 20+ year Treasury bond ETF (low-correlation w/ SPY)
    ("GLD", "gld"),       # Gold ETF
    ("BTC-USD", "btcusd"),  # Bitcoin (high-vol comparator)
]


def fetch_one(symbol: str) -> "yf.utils.pd.DataFrame":
    """Pull daily OHLCV for a single symbol."""
    df = yf.download(
        symbol,
        start=START.isoformat(),
        end=END.isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned no rows for {symbol}")
    # yfinance returns MultiIndex columns when multiple tickers are passed;
    # for a single symbol we may still get one — flatten it.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    return df[["date", "open", "high", "low", "close", "adj_close", "volume"]]


def write_readme(out_dir: Path, tickers: list[str], start: date, end: date) -> None:
    out_dir.joinpath("README.md").write_text(
        f"""# Quant track sample data

Daily OHLCV bars for these tickers, {start.isoformat()} → {end.isoformat()}:

{chr(10).join(f"- `{t}.csv`" for t in tickers)}

**Source.** Yahoo Finance via the `yfinance` Python package.
**License.** Public market data; Yahoo's redistribution terms allow
educational use. We snapshot rather than calling Yahoo at lesson time
so learners don't hit rate limits or CORS.

**Schema.**

| column      | type    | notes                                       |
| ----------- | ------- | ------------------------------------------- |
| `date`      | date    | trading day, ISO-8601                       |
| `open`      | float   | opening price (USD)                         |
| `high`      | float   | session high                                |
| `low`       | float   | session low                                 |
| `close`     | float   | closing price                               |
| `adj_close` | float   | dividend/split-adjusted close (use this!)   |
| `volume`    | int     | share volume (BTC: trade count)             |

**Refresh.**

```bash
source apps/api/.venv/bin/activate
python scripts/fetch_quant_data.py
```
""",
        encoding="utf-8",
    )


def main() -> int:
    if OUT_DIR.exists() and any(OUT_DIR.glob("*.csv")):
        # Don't blow away existing CSVs by accident — require an explicit clean.
        print(
            f"{OUT_DIR.relative_to(ROOT)} already has CSVs. Pass --force to overwrite.",
            file=sys.stderr,
        )
        if "--force" not in sys.argv:
            return 1
        for f in OUT_DIR.glob("*.csv"):
            f.unlink()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written_slugs: list[str] = []
    for symbol, slug in TICKERS:
        print(f"fetching {symbol} ...", flush=True)
        df = fetch_one(symbol)
        # Float formatting: 4 decimals is plenty for backtest lessons.
        out = OUT_DIR / f"{slug}.csv"
        df.to_csv(out, index=False, float_format="%.4f")
        size_kb = out.stat().st_size / 1024
        print(f"  wrote {out.relative_to(ROOT)}  ({len(df):,} rows, {size_kb:.0f} KB)")
        written_slugs.append(slug)

    write_readme(OUT_DIR, written_slugs, START, END)
    total_kb = sum(p.stat().st_size for p in OUT_DIR.glob("*.csv")) / 1024
    print(f"\nDone. {len(written_slugs)} CSVs, {total_kb:.0f} KB total.")
    print(f"Serve under /data/quant/<slug>.csv from public/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
