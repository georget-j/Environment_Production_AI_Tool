/**
 * Per-lesson walkthroughs. A walkthrough is a sequence of (caption, lines[])
 * pairs that annotate the lesson's worked Example code. Rendered as the
 * "Example" stage of the lesson wizard. Authored by hand — only added for
 * lessons where the worked Example is genuinely different from the
 * problem the learner solves (fillblank + matplot modes). Predict mode's
 * `code` IS the problem; debug / skeleton / apifetch have no separable
 * Example block — those modes skip the Example stage entirely.
 */

import type { WalkthroughStep } from "@/components/lesson-walkthrough";

type WalkthroughEntry = {
  code: string;
  steps: WalkthroughStep[];
};

export const WALKTHROUGHS: Record<string, WalkthroughEntry> = {
  "quant-02-creating-arrays": {
    code: [
      "import numpy as np",
      "# A literal list — known coupon rates on three bonds.",
      "coupons = np.array([0.025, 0.032, 0.041])",
      "# Pre-allocated buffer for tomorrow's signals.",
      "signals = np.zeros(252)",
      "# Evenly-spaced strikes for an IV surface — 80% to 120% of spot.",
      "strikes = np.linspace(80, 120, 5)",
      "print(coupons, signals[:3], strikes, sep=' | ')",
    ].join("\n"),
    steps: [
      {
        caption:
          "Import numpy as `np` — the only sensible alias; every quant codebase uses it.",
        lines: [1],
      },
      {
        caption:
          "`np.array([...])` lifts a Python list into a fixed-size, contiguous numeric array. Use this when you already have the values in hand — here, three known coupon rates.",
        lines: [2, 3],
      },
      {
        caption:
          "`np.zeros(n)` pre-allocates a vector of `n` zeros. Use this as a *buffer* — somewhere to drop values you'll fill in later (e.g., tomorrow's daily signals across 252 trading days).",
        lines: [4, 5],
      },
      {
        caption:
          "`np.linspace(start, stop, n)` returns `n` evenly-spaced points *including both endpoints*. Use this for grids: strikes for an IV surface, parameter sweeps, plot x-axes.",
        lines: [6, 7],
      },
      {
        caption:
          "Print all three so you can see their shapes side-by-side. The `sep=' | '` separator just keeps the output readable. In the next stage you'll write two of these constructors yourself from scratch.",
        lines: [8],
      },
    ],
  },

  "quant-05-boolean-masks": {
    code: [
      "import numpy as np",
      "# Six minutes of mid-quote returns.",
      "r = np.array([-0.02, 0.01, -0.005, 0.015, 0.0, 0.03])",
      "# Keep only minutes the price strictly went up.",
      "up_only = r[r > 0]",
      "print(up_only)",
      "print(f'kept {len(up_only)} of {len(r)} minutes')",
    ].join("\n"),
    steps: [
      { caption: "Import numpy.", lines: [1] },
      {
        caption:
          "Six minute-bar returns — three positive, two negative, one exactly zero. We'll use this as a tiny stand-in for a day of tick data.",
        lines: [2, 3],
      },
      {
        caption:
          "`r > 0` returns a boolean array of the same shape — `[False, True, False, True, False, True]`. Indexing `r[mask]` keeps only the True entries. Comparison AND indexing both run in C — zero Python iteration.",
        lines: [4, 5],
      },
      {
        caption:
          "Print the filtered values and a count. This same pattern scales: swap `> 0` for `> 2 * arr.std()` and you have an outlier filter.",
        lines: [6, 7],
      },
    ],
  },

  "quant-08-reproducible-random-numbers": {
    code: [
      "import numpy as np",
      "# Two researchers, same seed, must get the same sample.",
      "alice = np.random.default_rng(42).normal(size=3)",
      "bob   = np.random.default_rng(42).normal(size=3)",
      "print('alice:', alice)",
      "print('bob:  ', bob)",
      "print('identical:', np.array_equal(alice, bob))",
    ].join("\n"),
    steps: [
      { caption: "Import numpy.", lines: [1] },
      {
        caption:
          "Alice creates a fresh `Generator` seeded with 42 and draws 3 samples from a standard normal.",
        lines: [2, 3],
      },
      {
        caption:
          "Bob does the exact same thing — same seed (42), same number of draws. Same draws.",
        lines: [4],
      },
      {
        caption:
          "Print each researcher's samples — they should be identical floats. `default_rng` is deterministic, thread-safe, and the modern API; prefer it over the legacy `np.random.seed(...)`.",
        lines: [5, 6],
      },
      {
        caption:
          "`np.array_equal` confirms the two arrays match bit-for-bit. This is what makes a backtest reproducible — same seed today, same numbers next month, same numbers when your senior risk officer re-runs it.",
        lines: [7],
      },
    ],
  },

  "quant-13-plot-a-price-path": {
    code: [
      "import numpy as np, matplotlib.pyplot as plt",
      "rng = np.random.default_rng(0)",
      "# 252 trading days of small daily shocks (~1% daily vol).",
      "shocks = rng.normal(0, 0.01, 252)",
      "# GBM: log-returns sum, prices are the exp.",
      "price = 100 * np.exp(np.cumsum(shocks))",
      "plt.plot(price)",
      "plt.title('Simulated price path')",
      "plt.xlabel('trading day')",
      "plt.ylabel('price (USD)')",
      "print('plotted')",
    ].join("\n"),
    steps: [
      {
        caption:
          "Standard imports — numpy + pyplot under their conventional aliases. You'll type this combo a thousand times.",
        lines: [1],
      },
      {
        caption:
          "Seed a Generator, then draw 252 i.i.d. normal shocks — that's one year of trading days at ~1% daily vol (σ = 0.01).",
        lines: [2, 3, 4],
      },
      {
        caption:
          "Geometric Brownian motion in one line: cumulative-sum the log-shocks, exponentiate, scale by initial price 100. The result is a 252-element price series.",
        lines: [5, 6],
      },
      {
        caption:
          "`plt.plot(price)` draws the line — x-axis is the array index, y-axis is the value.",
        lines: [7],
      },
      {
        caption:
          "Always label your axes. The reviewer's first question on any chart is 'what am I looking at' — title + xlabel + ylabel answers it.",
        lines: [8, 9, 10],
      },
    ],
  },

  "quant-14-dataframes-from-csv": {
    code: [
      "import pandas as pd",
      "# Bundled tape: SPY 2015-01-01 → 2025-12-31, daily OHLCV.",
      "# 7 columns: date, open, high, low, close, volume, adj_close.",
      "df = pd.read_csv('/data/quant/spy.csv')",
      "# Almost exactly 252 trading days × 11 years.",
      "print(df.shape)",
    ].join("\n"),
    steps: [
      {
        caption: "Import pandas under its standard `pd` alias.",
        lines: [1],
      },
      {
        caption:
          "`pd.read_csv(path)` returns a DataFrame — pandas's tabular workhorse. The bundled SPY tape covers 2015 through end-of-2025: date + OHLCV + adjusted close = 7 columns.",
        lines: [2, 3, 4],
      },
      {
        caption:
          "`df.shape` is `(rows, cols)`. Eleven years × ~252 trading days ≈ 2,766 rows. Knowing the shape before any analysis catches off-by-decade errors fast.",
        lines: [5, 6],
      },
    ],
  },

  "quant-17-daily-and-log-returns": {
    code: [
      "import pandas as pd, numpy as np, matplotlib.pyplot as plt",
      "df = pd.read_csv('/data/quant/spy.csv')",
      "# pct_change: (p_t / p_{t-1}) - 1  — strategy-team convention.",
      "simple = df['adj_close'].pct_change().dropna()",
      "# log(p_t / p_{t-1}) — risk/research convention because it sums.",
      "log_r = np.log(df['adj_close'] / df['adj_close'].shift(1)).dropna()",
      "plt.hist(log_r, bins=60)",
      "plt.title('SPY log returns'); plt.xlabel('return'); plt.ylabel('count')",
      "# Same stdev to 4 decimals — convexity correction is small at daily horizon.",
      "print(round(simple.std(), 4), round(log_r.std(), 4))",
    ].join("\n"),
    steps: [
      {
        caption: "Standard imports + load the SPY tape.",
        lines: [1, 2],
      },
      {
        caption:
          "Simple returns: `pct_change()` does `(p_t / p_{t-1}) - 1`. Strategy/P&L teams use these because they line up with what's on the P&L sheet.",
        lines: [3, 4],
      },
      {
        caption:
          "Log returns: `log(p_t / p_{t-1})`. Risk/research uses these because `log(p_T/p_0) = sum(log_returns)` — multi-period maths becomes a sum instead of a product.",
        lines: [5, 6],
      },
      {
        caption: "Histogram of log returns with 60 bins, titled and labelled.",
        lines: [7, 8],
      },
      {
        caption:
          "Both standard deviations match to 4 decimal places. At daily horizon the convexity correction is negligible — divergence shows up at monthly or longer horizons.",
        lines: [9, 10],
      },
    ],
  },

  "quant-18-rolling-volatility": {
    code: [
      "import pandas as pd, numpy as np, matplotlib.pyplot as plt",
      "df = pd.read_csv('/data/quant/spy.csv')",
      "r = df['adj_close'].pct_change()",
      "# Rolling 30-day std, scaled by √252 → annualised vol.",
      "vol = r.rolling(30).std() * np.sqrt(252)",
      "plt.plot(vol)",
      "plt.title('SPY 30-day rolling vol'); plt.xlabel('day'); plt.ylabel('annualised vol')",
      "# Peak realised vol over the 11-year window — likely COVID-March-2020.",
      "print(round(vol.max(), 3))",
    ].join("\n"),
    steps: [
      {
        caption: "Imports + load SPY + compute simple daily returns.",
        lines: [1, 2, 3],
      },
      {
        caption:
          "`rolling(30).std()` builds a 30-day rolling-window std Series. Multiply by `√252` to annualise daily vol — std scales with `√n`, so daily-to-annual is `× √252`.",
        lines: [4, 5],
      },
      {
        caption:
          "Plot the vol series across the full 11-year window. Title + axis labels.",
        lines: [6, 7],
      },
      {
        caption:
          "Print the peak vol. Over 2015–2025 this is almost certainly the COVID spike of March 2020 — about 0.82 (82%) annualised.",
        lines: [8, 9],
      },
    ],
  },

  "quant-21-fitting-a-normal-to-returns": {
    code: [
      "import pandas as pd, numpy as np, matplotlib.pyplot as plt",
      "from scipy.stats import norm",
      "df = pd.read_csv('/data/quant/spy.csv')",
      "r = df['adj_close'].pct_change().dropna()",
      "# MLE fit of a normal — gives (mean, std) of the best-fit Gaussian.",
      "mu, sigma = norm.fit(r)",
      "xs = np.linspace(r.min(), r.max(), 200)",
      "# density=True scales the histogram so it sits on the pdf's y-axis.",
      "plt.hist(r, bins=80, density=True, alpha=0.6)",
      "plt.plot(xs, norm.pdf(xs, mu, sigma))",
      "plt.title('SPY daily returns vs normal fit')",
      "# Best-fit daily std — about 1.1%, in line with quoted index vol.",
      "print(round(sigma, 4))",
    ].join("\n"),
    steps: [
      {
        caption: "Imports + load SPY + compute simple returns.",
        lines: [1, 2, 3, 4],
      },
      {
        caption:
          "`norm.fit(data)` does maximum-likelihood estimation — returns `(mu, sigma)` of the best-fit normal distribution.",
        lines: [5, 6],
      },
      {
        caption:
          "Build a 200-point grid spanning the return range — we'll evaluate the fitted PDF on this grid.",
        lines: [7],
      },
      {
        caption:
          "Histogram with `density=True` so the y-axis is a density (area sums to 1), not raw counts. Without this the histogram and the PDF would be on totally different scales.",
        lines: [8, 9],
      },
      {
        caption:
          "Overlay the fitted normal's PDF. The body looks Gaussian; the tails are noticeably fatter — that's the gap the post-2008 risk literature is about.",
        lines: [10, 11],
      },
      {
        caption:
          "Print fitted sigma — about 0.011, i.e. ~1.1% daily vol. Matches what the index is quoted at.",
        lines: [12, 13],
      },
    ],
  },

  "quant-24-present-value-of-a-single-cash-flow": {
    code: [
      "# £1000 received in 5 years at a 4% discrete-compounding discount rate.",
      "cf, r, t = 1000, 0.04, 5",
      "# Discount factor 1/(1+r)**t shrinks the cashflow back to today.",
      "pv = cf / (1 + r)**t",
      "print(round(pv, 2))",
    ].join("\n"),
    steps: [
      {
        caption:
          "Three inputs: cashflow size, discount rate, time horizon (years).",
        lines: [1, 2],
      },
      {
        caption:
          "The discount factor `1/(1+r)**t` shrinks future money back to today. Discrete compounding — the convention on equity desks.",
        lines: [3, 4],
      },
      {
        caption:
          "£1000 in 5 years at 4% is worth about £821.93 today. Every other pricing model in finance — bond prices, DCF, option pricing — builds on this.",
        lines: [5],
      },
    ],
  },

  "quant-26-option-payoff-diagrams": {
    code: [
      "import numpy as np, matplotlib.pyplot as plt",
      "# Spot prices from 60 to 140 in 81 steps (one per unit).",
      "S = np.linspace(60, 140, 81)",
      "K, premium = 100, 5",
      "# Vectorised hockey-stick: max(S - K, 0) per element, minus premium.",
      "payoff = np.maximum(S - K, 0) - premium",
      "plt.plot(S, payoff)",
      "plt.title('Long call (K=100)'); plt.xlabel('spot'); plt.ylabel('profit')",
      "plt.axhline(0, color='gray', lw=0.5)",
      "# At S=140 the payoff is 140-100 minus 5 premium = 35.",
      "print(round(payoff[-1], 1))",
    ].join("\n"),
    steps: [
      {
        caption:
          "Build a grid of spot prices from 60 to 140 — one per unit, 81 points including both endpoints.",
        lines: [1, 2, 3],
      },
      {
        caption: "Strike 100, premium 5 — a standard ATM long call.",
        lines: [4],
      },
      {
        caption:
          "The terminal payoff: `np.maximum(S - K, 0)` is the hockey-stick shape — zero below the strike, linearly increasing above. Then subtract the 5 premium paid to get the profit.",
        lines: [5, 6],
      },
      {
        caption:
          "Plot spot on the x-axis, profit on the y-axis. The zero line makes break-even (S = K + premium = 105) visually obvious.",
        lines: [7, 8, 9],
      },
      {
        caption:
          "Sanity check the right end: at S = 140, payoff = 140 − 100 − 5 = 35.",
        lines: [10, 11],
      },
    ],
  },

  "quant-31-monte-carlo-option-pricing": {
    code: [
      "import numpy as np, matplotlib.pyplot as plt",
      "S0, K, r, sigma, T, N = 100, 100, 0.05, 0.20, 1.0, 50_000",
      "rng = np.random.default_rng(0)",
      "Z = rng.standard_normal(N)",
      "ST = S0 * np.exp((r - sigma**2/2)*T + sigma*np.sqrt(T)*Z)",
      "payoffs = np.exp(-r*T) * np.maximum(ST - K, 0)",
      "running = np.cumsum(payoffs) / np.arange(1, N+1)",
      "plt.plot(running)",
      "plt.axhline(10.4506, color='red', lw=0.5, label='Black-Scholes')",
      "plt.legend(); plt.title('MC call price convergence')",
      "print(round(running[-1], 3))",
    ].join("\n"),
    steps: [
      {
        caption:
          "Standard ATM call parameters: spot = strike = 100, r = 5%, σ = 20%, T = 1 year, N = 50,000 sample paths.",
        lines: [1, 2],
      },
      {
        caption:
          "Seed a Generator, draw N standard normal Z's — one per Monte Carlo path.",
        lines: [3, 4],
      },
      {
        caption:
          "Risk-neutral GBM closed form: `S_T = S0 · exp((r − σ²/2)T + σ√T · Z)`. One line, vectorised over all N paths.",
        lines: [5],
      },
      {
        caption:
          "Discounted payoff per path: `exp(-rT) · max(S_T − K, 0)`. Zero where the call expires OTM, positive elsewhere.",
        lines: [6],
      },
      {
        caption:
          "Running mean = `cumsum(payoffs) / (1, 2, ..., N)`. Standard error shrinks as `1/√N` — quadrupling N halves the error, but never faster.",
        lines: [7],
      },
      {
        caption:
          "Plot the running estimate. Red line at 10.4506 is the Black-Scholes closed-form for comparison — the MC estimate should settle close to it after enough paths.",
        lines: [8, 9, 10],
      },
      {
        caption:
          "Final estimate after 50,000 paths — should be within a few cents of BS (about 10.48).",
        lines: [11],
      },
    ],
  },

  "quant-32-mean-variance-frontier": {
    code: [
      "import pandas as pd, numpy as np, matplotlib.pyplot as plt",
      "def ret(t): return pd.read_csv(f'/data/quant/{t}.csv')['adj_close'].pct_change().dropna().values[-1000:]",
      "R = np.column_stack([ret('spy'), ret('aapl'), ret('tlt')])",
      "mu, S = R.mean(axis=0), np.cov(R, rowvar=False)",
      "Sinv = np.linalg.inv(S); ones = np.ones(3)",
      "a = ones @ Sinv @ ones; b = mu @ Sinv @ ones; c = mu @ Sinv @ mu",
      "targets = np.linspace(mu.min(), mu.max(), 50)",
      "vars_ = (a*targets**2 - 2*b*targets + c) / (a*c - b**2)",
      "plt.plot(np.sqrt(vars_), targets); plt.xlabel('vol'); plt.ylabel('return')",
      "print(round(float(np.sqrt(vars_).min()), 4))",
    ].join("\n"),
    steps: [
      {
        caption:
          "Load three series (SPY, AAPL, TLT), take the most recent 1000 daily returns of each, stack into an N×3 returns matrix.",
        lines: [1, 2, 3],
      },
      {
        caption:
          "Compute mean vector `mu` (length 3) and covariance matrix `S` (3×3). `rowvar=False` tells np.cov that each column is a variable (an asset), not each row.",
        lines: [4],
      },
      {
        caption:
          "Pre-compute three scalar constants from the Markowitz closed form: `a = 1ᵀΣ⁻¹1`, `b = μᵀΣ⁻¹1`, `c = μᵀΣ⁻¹μ`. Three matrix-vector products — that's the whole optimisation.",
        lines: [5, 6],
      },
      {
        caption:
          "Sweep target returns from the min to the max sample mean; the closed-form variance at each target is `(at² − 2bt + c) / (ac − b²)`.",
        lines: [7, 8],
      },
      {
        caption:
          "Plot vol (x-axis) vs target return (y-axis) — that's the efficient frontier. Print the global minimum-vol point (the leftmost vertex).",
        lines: [9, 10],
      },
    ],
  },

  "quant-34-sklearn-fit-and-predict": {
    code: [
      "import numpy as np",
      "from sklearn.linear_model import LinearRegression",
      "# X must be 2D for sklearn — even a single feature gets reshape(-1, 1).",
      "X = np.arange(10).reshape(-1, 1)",
      "# Perfectly linear target: y = 2x + 3.",
      "y = 2 * X.ravel() + 3",
      "# Chainable .fit returns the model so you can score in one line.",
      "model = LinearRegression().fit(X, y)",
      "# R² == 1.0 confirms a perfect fit.",
      "print(round(model.score(X, y), 4))",
    ].join("\n"),
    steps: [
      {
        caption: "Import numpy and sklearn's LinearRegression.",
        lines: [1, 2],
      },
      {
        caption:
          "Build the feature matrix. `np.arange(10).reshape(-1, 1)` produces a 10×1 matrix — sklearn always wants 2D `X`, even for a single feature.",
        lines: [3, 4],
      },
      {
        caption:
          "Synthetic target: `y = 2x + 3`. Perfectly linear, so any working linear model will fit it exactly.",
        lines: [5, 6],
      },
      {
        caption:
          "`.fit(X, y)` returns the model itself — chainable. So `LinearRegression().fit(X, y)` is one expression, and you don't need a temporary variable.",
        lines: [7, 8],
      },
      {
        caption:
          "`.score(X, y)` returns R² for regressors. On clean linear data it's 1.0 exactly. Anything less is a feature-matrix bug.",
        lines: [9, 10],
      },
    ],
  },

  "quant-49-the-same-ring-buffer-in-python": {
    code: [
      "import time",
      "class RingBuffer:",
      "    def __init__(self, cap):",
      "        self.slots = [0]*cap; self.cap = cap; self.head = self.tail = self.count = 0",
      "    def push(self, x):",
      "        if self.count == self.cap: return False",
      "        self.slots[self.head] = x; self.head = (self.head + 1) % self.cap; self.count += 1",
      "        return True",
      "    def pop(self):",
      "        if self.count == 0: return None",
      "        v = self.slots[self.tail]; self.tail = (self.tail + 1) % self.cap; self.count -= 1",
      "        return v",
      "rb = RingBuffer(4)",
      "for i in (10, 20, 30, 40, 50): rb.push(i)",
      "out = []",
      "while (v := rb.pop()) is not None:",
      "    out.append(v)",
      "print(out)",
    ].join("\n"),
    steps: [
      {
        caption:
          "The class — same shape as the C version from the previous lesson. A Python list as the backing slots + three integer attributes: `head`, `tail`, `count`.",
        lines: [2, 3, 4],
      },
      {
        caption:
          "`push`: if full, refuse. Otherwise drop the value into `slots[head]`, advance head modulo cap, bump count. The modulo wrap is what makes it a ring.",
        lines: [5, 6, 7, 8],
      },
      {
        caption:
          "`pop`: if empty, return None. Otherwise read `slots[tail]`, advance tail modulo cap, decrement count.",
        lines: [9, 10, 11, 12],
      },
      {
        caption:
          "Construct a 4-slot buffer and try to push 5 values — the 5th must fail (capacity is 4). `push` returns False on overflow.",
        lines: [13, 14],
      },
      {
        caption:
          "Drain the buffer with a walrus-assignment while-loop. `out` ends up as `[10, 20, 30, 40]` — the 50 was rejected on overflow.",
        lines: [15, 16, 17, 18],
      },
    ],
  },
};
