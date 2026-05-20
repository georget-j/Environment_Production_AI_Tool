# Quant Programmer Roadmap

A pragmatic learning path from "I can write Python" to "I can build the systems quant teams ship to production." It assumes you've finished the [Python Basics](/tracks/python-basics) track and that you'll do the work — there's no shortcut.

**Time estimate, end to end:** 12–18 months part-time, faster if you're already coding professionally. Don't think of it as a checklist to race through. Each stage builds the foundation for the next.

**Languages:** Python for everything you can; **C** when speed matters (often). C++ is the de facto language at the lowest-latency firms, but C is the better first systems language — smaller, sharper, faster to learn well.

---

## Stage 0 — Foundations (1–2 months)

**Outcomes:** comfortable reading Python, comfortable with the maths that all of quant rests on.

You can write loops, functions, lists, and dicts (Python Basics has you here). You also need the maths. None of it is exotic, but you need fluency, not just exposure.

- **Linear algebra** — matrices, vectors, dot products, eigenvalues. Most quant maths is linear algebra in disguise.
- **Calculus** — derivatives and integrals, partial derivatives. You need them for options pricing.
- **Probability** — distributions (normal, log-normal, binomial), conditional probability, Bayes' theorem.
- **Statistics** — mean, variance, covariance, hypothesis testing, p-values. Skip nothing; financial data is statistical.

**Resources**

- [Khan Academy](https://www.khanacademy.org/math) — free, paced, excellent. Linear algebra + calculus + probability tracks.
- [3blue1brown — Essence of Linear Algebra](https://www.3blue1brown.com/topics/linear-algebra) — short videos, geometric intuition. Watch the whole series.
- [3blue1brown — Essence of Calculus](https://www.3blue1brown.com/topics/calculus) — same treatment for derivatives and integrals.

---

## Stage 1 — Numerical Python (1–2 months)

**Outcomes:** you can manipulate numerical data with numpy, plot it with matplotlib, and work in a Jupyter notebook without thinking about the tooling.

This is where you stop writing `for` loops over lists and start vectorising.

- **numpy** — arrays, broadcasting, slicing, linear algebra (`np.linalg`), random number generation.
- **matplotlib** — `plt.plot`, `plt.scatter`, `plt.hist`, subplots, axes, labels.
- **Jupyter** — running cells, magics (`%timeit`, `%matplotlib inline`), markdown cells. Notebooks are how research happens.

Don't reach for pandas yet. Master numpy first.

**Resources**

- [numpy quickstart](https://numpy.org/doc/stable/user/quickstart.html) — official, terse, complete.
- **Python Data Science Handbook** (Jake VanderPlas) — free online. Chapters 1–3 cover numpy and matplotlib thoroughly.
- [matplotlib gallery](https://matplotlib.org/stable/gallery/index.html) — copy a plot, modify it, learn by tweaking.

---

## Stage 2 — Data and statistics (1–2 months)

**Outcomes:** you can ingest, clean, transform, and statistically analyse a dataset of financial returns.

- **pandas** — DataFrames, indexing, joins (`merge`), grouping (`groupby`), time series (`resample`, `rolling`, `pct_change`), CSV/Parquet I/O.
- **scipy.stats** — distributions, statistical tests, fitting.
- **statsmodels** — linear regression, time series models (ARIMA, GARCH). Use this when you want statistical inference, not just predictions.

**Resources**

- ["10 minutes to pandas"](https://pandas.pydata.org/docs/user_guide/10min.html) — start here.
- **Python Data Science Handbook**, chapter 3 — the canonical pandas walkthrough.
- [SciPy lecture notes](https://scipy-lectures.org/) — covers scipy + statistical inference.

---

## Stage 3 — Financial foundations (2–3 months)

**Outcomes:** you understand the maths quant teams actually use day-to-day. Not because every job requires Black-Scholes, but because everyone you work with will assume you know it.

- **Time value of money** — present value, discounting, bond pricing.
- **Options** — payoff diagrams, put/call parity, the **Black-Scholes** model (derivation matters, even if you'll never re-derive it), binomial trees, the Greeks (delta, gamma, vega, theta).
- **Portfolio theory** — Markowitz mean-variance optimisation, the efficient frontier, CAPM, Sharpe ratio, drawdowns.
- **Risk** — VaR, expected shortfall, why these models fail in tails.

**Tools**

- **QuantLib** (via the `QuantLib-Python` wrapper) — open-source library for pricing fixed income, options, exotic derivatives. Knowing it pays off; reading its docs teaches you the maths too.

**Resources**

- **Options, Futures, and Other Derivatives** (John Hull) — the canonical textbook. Slow, dense, foundational.
- [QuantLib Python Cookbook](https://leanpub.com/quantlibpythoncookbook) — concrete recipes for using the library.
- [QuantStart](https://www.quantstart.com/articles/) — readable articles for context and intuition.

---

## Stage 4 — Machine learning (1–2 months)

**Outcomes:** you can train a baseline regression or classifier on financial data, evaluate it honestly, and not delude yourself with backtest-overfitting.

- **scikit-learn** — linear regression, logistic regression, random forests, gradient boosting, cross-validation, train/test split, metrics.
- **Pipeline discipline** — preprocessing, feature engineering, leakage avoidance.
- **Honest evaluation** — out-of-sample testing, walk-forward analysis. Financial ML kills you with look-ahead bias if you're sloppy.

Deep learning (PyTorch, TensorFlow) is optional at this stage and overhyped for many quant problems. Get the classical stuff right first.

**Resources**

- **Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow** (Aurélien Géron) — the practical reference.
- [scikit-learn documentation](https://scikit-learn.org/stable/user_guide.html) — surprisingly readable.
- **Advances in Financial Machine Learning** (Marcos López de Prado) — when you're ready, this is the unsparing book about doing it properly.

---

## Stage 5 — Performance: C, Cython, and profiling (2–3 months)

**Outcomes:** you know what's actually slow, what makes code fast, and how to push critical loops down to compiled code without rewriting everything in C.

This is the stage where you learn **C**. Not because you'll write a full C application — you'll write small, focused, performance-critical kernels and bind them to Python.

- **C language** — pointers, memory management (`malloc`/`free`), structs, function pointers, `stdio.h`, `stdlib.h`, `string.h`, the preprocessor. K&R is still the right book.
- **Compilation and linkage** — what the compiler, linker, and `make` actually do. Why static vs dynamic linking matters.
- **Cython** or **cffi** — bridge to call C from Python. Cython is incremental (write Python that compiles to C); cffi is direct (call a `.so` you compiled yourself).
- **numpy internals** — why vectorised operations are 100× faster than Python loops. Read the source of one numpy function.
- **Profiling** — `cProfile` for finding hot functions, `line_profiler` for finding hot lines, `memory_profiler` for finding leaks.

**Resources**

- **The C Programming Language** (Kernighan & Ritchie, "K&R") — 274 pages. Read it twice.
- [learn-c.org](https://www.learn-c.org/) — interactive intro if you want a softer start.
- **High Performance Python** (Gorelick & Ozsvald) — the practical guide to making Python fast.
- [Cython tutorial](https://cython.readthedocs.io/en/latest/src/tutorial/index.html) — official, concise.

---

## Stage 6 — Systems thinking (2–3 months)

**Outcomes:** you can navigate a Linux server, write a SQL query, query a time-series database, and use git like a professional. The "everything around the code" that quant interviews assume.

- **Linux** — shell (bash or zsh), `ssh`, file permissions, processes (`ps`, `top`, `htop`), `grep`, `awk`, `sed`, pipes. Comfort, not encyclopedic knowledge.
- **Networks** — TCP/IP basics, HTTP, sockets, why latency matters in trading.
- **SQL** — `SELECT`, joins, window functions, indexes, `EXPLAIN`. PostgreSQL is a good default.
- **Time-series databases** — `KDB+` (the quant industry standard), `InfluxDB`, `TimescaleDB`. KDB+ is its own language (q) and is worth at least skimming if you're aiming at major hedge funds.
- **git** — branches, rebase, bisect, hooks. Don't skim this.

**Resources**

- **The Linux Command Line** (William Shotts) — free online, gold-standard intro.
- [Mode Analytics SQL tutorial](https://mode.com/sql-tutorial/) — practical, free, builds to advanced topics.
- [KDB+ Q for Mortals](https://code.kx.com/q4m3/) — free online, the Q language primer.
- [Pro Git](https://git-scm.com/book/en/v2) — free, comprehensive, the only git book you need.

---

## Stage 7 — Specialisation

Once you have the foundations, **the job** decides what you specialise in.

- **HFT / low-latency** — C++ becomes essential (not just C). Lock-free data structures, kernel bypass networking (DPDK, Solarflare), FPGA exposure. Firms: Jump, Citadel Securities, Jane Street (some teams), Tower.
- **Sell-side quant** — derivatives pricing, risk models. Python + C++ + Excel. Firms: Goldman Sachs, JPMorgan, Morgan Stanley.
- **Buy-side / hedge fund quant** — strategy research, signal generation. Python + R + SQL + KDB+. Firms: AQR, Two Sigma, Renaissance, Bridgewater.
- **Quant research (academic-style)** — statistics, ML, paper-reading. Less coding ceremony, more rigour. Firms: research-oriented hedge funds, university adjacencies.

**Resources for figuring out which to chase**

- Read job listings from each kind of firm. They're remarkably specific about tools.
- Read interviews and blog posts from working quants. **Quantitative Brokers** and **Hudson River Trading**'s engineering blogs are excellent. AQR's "Research Library" is the gold standard of accessible academic-finance writing.
- Talk to people. The industry is small. LinkedIn DMs to people one or two years ahead of you, asking thoughtful questions, work surprisingly often.

---

## What this roadmap is not

- A guarantee. You can finish all of this and still not get a quant job. The market is competitive.
- A linear track. Real learning loops back constantly. Stage 5's C work will send you back to Stage 1's numpy to understand why it's so fast.
- A substitute for building things. After every stage, build a small project that uses what you learned. A backtester. A volatility-surface plotter. A toy options pricer. **The portfolio is the proof.**

The challenges in this track will roll out stage by stage. They'll lean heavily on the same in-browser format the rest of ProdReady AI uses — but with progressively richer scaffolding (numpy arrays inline, plotting in the browser, eventually small C kernels via Pyodide's WASM compiler).

For now, treat this document as the map. Open the [Python Basics](/tracks/python-basics) track and start there. When you finish it, come back and start Stage 1.
