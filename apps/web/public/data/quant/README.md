# Quant track sample data

Daily OHLCV bars for these tickers, 2015-01-01 → 2026-01-01:

- `spy.csv`
- `aapl.csv`
- `qqq.csv`
- `tlt.csv`
- `gld.csv`
- `btcusd.csv`

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
