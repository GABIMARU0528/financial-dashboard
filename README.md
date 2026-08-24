# 📈 Real-Time Financial Market Dashboard

A Bloomberg/TradingView-inspired financial market monitoring platform built with
**Streamlit** and **Plotly**, covering four technical indicators (SMA, RSI, MACD,
Bollinger Bands) across five assets (Apple, Tesla, S&P 500, Bitcoin, EUR/USD).

Built as both:
1. A real-time market monitoring dashboard.
2. A presentation tool for a Financial Engineering BACHELOR's Capstone defense.

---

## 1. Project structure

```
app.py            Main Streamlit entry point (layout, tabs, sidebar, state)
data.py           Yahoo Finance data access layer (caching, news, watchlist)
indicators.py     SMA / RSI / MACD / Bollinger Bands / ATR calculations
signals.py        Live BUY/SELL/HOLD signal engine + simplified backtester
portfolio.py      Multi-asset portfolio metrics (risk, correlation, frontier)
analytics.py      Rolling stats, return distribution, regime detection
charts.py         All Plotly figure builders
utils.py          Constants, formatting helpers, CSS/theme injection
requirements.txt  Python dependencies
README.md         This file
```

---

## 2. Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

---

## 4. Using the dashboard

- **Sidebar** — pick an asset, timeframe, and which indicators to overlay on the
  candlestick chart. Toggle dark/light theme, auto-refresh, and Presentation Mode.
- **🏠 Dashboard tab** — KPI cards, candlestick + volume chart, RSI/MACD panels,
  a live BUY/SELL/HOLD signal with confidence and indicator-agreement score,
  market statistics, and market analytics (return distribution, rolling
  volatility/Sharpe/drawdown, volume analysis).
- **📊 Backtesting Results tab** — the academic presentation page: a sortable
  strategy performance table across all assets/strategies, comparison bar
  charts, equity curve comparison, a medal-based strategy ranking, per-asset
  best/worst analysis, auto-generated Research Findings, a Live vs Historical
  comparison, and a Professional Conclusion.
- **💼 Portfolio tab** — select 2+ assets in the sidebar, set weights, and see
  expected return/risk, Sharpe ratio, a diversification score, correlation
  heatmap, risk-contribution breakdown, and an optional simulated efficient
  frontier.
- **📰 News & Watchlist tab** — recent headlines (via `yfinance`'s free news
  feed, no API key required) with a lightweight keyword-based sentiment tag,
  plus a color-coded multi-asset watchlist (price, change %, RSI, MACD
  direction, live signal, volume).

Use **🎓 Presentation Mode** to hide secondary sidebar controls, enlarge fonts/
KPI cards, and present the current view full-screen on a projector.

---

## 5. Design notes & known simplifications

This project favors a working, well-documented dashboard over a 1:1
reproduction of every possible institutional-terminal feature. Notable
simplifications, called out explicitly rather than hidden:

- **Auto-refresh** reloads the whole page every 30 seconds via a lightweight
  `<meta http-equiv="refresh">` tag — simple and dependency-free, at the cost
  of a full page reload rather than a partial/live websocket update.
- **Backtesting methodology** on the "Backtesting Results" page is an
  intentionally simplified long/flat engine (same-bar execution, flat 0.10%
  transaction cost) for fast, interactive exploration. It does **not**
  reproduce the exact capstone report methodology (next-day-open execution,
  detailed cost modeling) — refer to the written capstone for the
  authoritative empirical results.
- **News sentiment** is a small keyword lexicon, not a trained NLP model —
  it's a quick visual cue, not a rigorous sentiment classifier.
- **Market hours** are approximated (continuous for crypto/FX, Mon–Fri
  13:30–20:00 UTC for equities/index) rather than pulled from a full
  exchange calendar (holidays, early closes are not modeled).
- **Chart "fullscreen"/"drawing tools"** use Plotly's built-in modebar
  (zoom, pan, box/lasso select, draw line/path, erase, export PNG) rather
  than a custom-built charting engine.
- **Efficient frontier** is a Monte-Carlo simulation of random long-only
  portfolio weights, not a full quadratic-programming optimizer — sufficient
  to visualize the risk/return trade-off shape for a defense presentation.

## 6. Data source & disclaimer

All market data is sourced from Yahoo Finance via the `yfinance` library.
Data may be delayed and is provided for educational/academic purposes only —
this dashboard is not investment advice.

---

**Author:** KIRUA · **Version:** 1.0.0
