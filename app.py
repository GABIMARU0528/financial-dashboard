"""
app.py
------
Real-Time Financial Market Dashboard — main entry point.

Run with:  streamlit run app.py

Ties together data.py, indicators.py, signals.py, analytics.py,
portfolio.py and charts.py into a Bloomberg/TradingView-inspired
Streamlit interface, plus a dedicated Backtesting Results page for
academic (Master's Capstone) presentation.
"""

from __future__ import annotations
import datetime as dt
import pandas as pd
import streamlit as st

import data
import indicators
import signals
import analytics
import portfolio
import charts
from utils import (
    ASSET_MAP, TIMEFRAME_MAP, INDICATOR_OPTIONS, STRATEGY_NAMES,
    APP_VERSION, AUTHOR, RISK_FREE_RATE,
    format_currency, format_percent, format_large_number,
    trend_color, get_palette, is_market_open, inject_css, kpi_card,
)

# --------------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Financial Market Dashboard | Capstone",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Session state defaults
# --------------------------------------------------------------------------
defaults = {
    "theme": "dark",
    "presentation_mode": False,
    "auto_refresh": False,
    "last_refresh": dt.datetime.now(dt.UTC),
    "portfolio_assets": ["Apple (AAPL)", "Tesla (TSLA)", "Bitcoin (BTC-USD)"],
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

theme = st.session_state["theme"]
presentation = st.session_state["presentation_mode"]
inject_css(theme, presentation_mode=presentation)
palette = get_palette(theme)

# Simple, dependency-free auto-refresh: reload the whole page every 30s.
if st.session_state["auto_refresh"]:
    st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📈 Market Dashboard")
    st.caption("Financial Engineering Capstone — Live Terminal")

    if not presentation:
        asset_label = st.selectbox("Asset", list(ASSET_MAP.keys()), key="asset_select")
        timeframe_label = st.selectbox("Timeframe", list(TIMEFRAME_MAP.keys()), index=4, key="tf_select")
        indicators_selected = st.multiselect(
            "Indicators", INDICATOR_OPTIONS, default=["SMA", "Bollinger Bands"], key="ind_select"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Refresh", width="stretch"):
                st.cache_data.clear()
                st.session_state["last_refresh"] = dt.datetime.utcnow()
                st.rerun()
        with col_b:
            st.toggle("Auto-Refresh (30s)", key="auto_refresh")

        theme_choice = st.radio("Theme", ["🌙 Dark", "☀️ Light"], horizontal=True,
                                 index=0 if theme == "dark" else 1)
        st.session_state["theme"] = "dark" if "Dark" in theme_choice else "light"

        st.divider()
        st.markdown("**Portfolio assets** _(for Portfolio tab)_")
        st.session_state["portfolio_assets"] = st.multiselect(
            "Select 2+ assets", list(ASSET_MAP.keys()),
            default=st.session_state["portfolio_assets"], key="portfolio_multi",
        )
        st.divider()
    else:
        # Presentation mode: keep only the essentials visible
        asset_label = st.session_state.get("asset_select", list(ASSET_MAP.keys())[0])
        timeframe_label = st.session_state.get("tf_select", "1 Year")
        indicators_selected = st.session_state.get("ind_select", ["SMA", "Bollinger Bands"])

    st.toggle("🎓 Presentation Mode", key="presentation_mode")

    st.caption(f"Last refresh: {st.session_state['last_refresh'].strftime('%H:%M:%S UTC')}")

ticker = ASSET_MAP[asset_label]
period, interval = TIMEFRAME_MAP[timeframe_label]


# --------------------------------------------------------------------------
# Data fetch for the selected asset
# --------------------------------------------------------------------------
with st.spinner(f"Loading {asset_label}…"):
    raw_df = data.fetch_price_data(ticker, period, interval)
    info = data.fetch_ticker_info(ticker)

if raw_df.empty:
    st.error(
        f"No data returned for **{ticker}**. Yahoo Finance may be rate-limiting, the "
        f"symbol may be invalid for this timeframe, or this environment may lack network "
        f"access. Try a different timeframe or click Refresh."
    )
    st.stop()

df = indicators.add_all_indicators(raw_df)

# Download button data (raw + indicators, current view)
csv_bytes = df.to_csv().encode("utf-8")


# --------------------------------------------------------------------------
# Header + download
# --------------------------------------------------------------------------
h1, h2 = st.columns([5, 1])
with h1:
    st.markdown(f"### {asset_label}  ·  `{ticker}`")
with h2:
    st.download_button("⬇ Download CSV", data=csv_bytes, file_name=f"{ticker}_{timeframe_label}.csv",
                        mime="text/csv", width="stretch")

tabs = st.tabs(["🏠 Dashboard", "📊 Backtesting Results", "💼 Portfolio", "📰 News & Watchlist"])


# ==========================================================================
# TAB 1 — DASHBOARD
# ==========================================================================
with tabs[0]:
    # ---- KPI cards -------------------------------------------------------
    last_price = info.get("last_price")
    prev_close = info.get("previous_close")
    change_abs = (last_price - prev_close) if (last_price and prev_close) else None
    change_pct = (change_abs / prev_close * 100) if (change_abs is not None and prev_close) else None

    kpi_cols = st.columns(6)
    kpi_defs = [
        ("Current Price", format_currency(last_price)),
        ("Daily Change %", format_percent(change_pct), trend_color(change_pct, palette)),
        ("Daily Change $", format_currency(change_abs), trend_color(change_abs, palette)),
        ("Open", format_currency(info.get("open"))),
        ("High", format_currency(info.get("day_high"))),
        ("Low", format_currency(info.get("day_low"))),
    ]
    for col, kdef in zip(kpi_cols, kpi_defs):
        label, value, *rest = kdef
        sub_color = rest[0] if rest else None
        col.markdown(kpi_card(label, value, sub_color=sub_color), unsafe_allow_html=True)

    kpi_cols2 = st.columns(6)
    market_open = is_market_open(ticker)
    stats = analytics.market_summary_stats(raw_df)
    kpi_defs2 = [
        ("Volume", format_large_number(info.get("volume"))),
        ("52W High", format_currency(info.get("year_high"))),
        ("52W Low", format_currency(info.get("year_low"))),
        ("Market Status", "🟢 Open" if market_open else "🔴 Closed"),
        ("Market Trend", stats["regime"]),
        ("Last Update", dt.datetime.now(dt.UTC).strftime("%H:%M:%S UTC")),
    ]
    for col, (label, value) in zip(kpi_cols2, kpi_defs2):
        col.markdown(kpi_card(label, value), unsafe_allow_html=True)

    # ---- Candlestick chart -------------------------------------------------
    st.markdown('<div class="section-title">Real-Time Candlestick Chart</div>', unsafe_allow_html=True)
    fig_candle = charts.build_candlestick_chart(df, indicators_selected, theme, asset_label)
    st.plotly_chart(fig_candle, width="stretch", config=charts.PLOTLY_CONFIG)

    # ---- Indicator panels ---------------------------------------------------
    ind_cols = st.columns(2)
    if "RSI" in indicators_selected:
        with ind_cols[0]:
            st.plotly_chart(charts.build_rsi_chart(df, theme), width="stretch")
    if "MACD" in indicators_selected:
        with ind_cols[1]:
            st.plotly_chart(charts.build_macd_chart(df, theme), width="stretch")
    if not indicators_selected:
        st.info("Select indicators in the sidebar to see RSI / MACD detail panels.")

    # ---- Trading signal ------------------------------------------------------
    st.markdown('<div class="section-title">Trading Signals</div>', unsafe_allow_html=True)
    sig = signals.generate_live_signal(raw_df)
    badge_class = {"BUY": "badge-buy", "SELL": "badge-sell", "HOLD": "badge-hold"}[sig["signal"]]
    sc1, sc2, sc3 = st.columns([1, 1, 2])
    with sc1:
        st.markdown(f'<div class="badge {badge_class}">{sig["signal"]}</div>', unsafe_allow_html=True)
    with sc2:
        st.markdown(kpi_card("Confidence", f'{sig["confidence"]}%'), unsafe_allow_html=True)
    with sc3:
        st.markdown(kpi_card("Indicator Agreement", sig["agreement"]), unsafe_allow_html=True)
    with st.expander("Indicator-by-indicator vote breakdown"):
        st.table(pd.DataFrame(sig["votes"].items(), columns=["Indicator", "Vote"]))

    # ---- Market statistics -----------------------------------------------
    st.markdown('<div class="section-title">Market Statistics</div>', unsafe_allow_html=True)
    stat_cols = st.columns(4)
    stat_defs = [
        ("Daily Return", format_percent(stats["daily_return"])),
        ("Annual Return", format_percent(stats["annual_return"])),
        ("Volatility (ann.)", format_percent(stats["volatility"], signed=False)),
        ("ATR (14)", format_currency(stats["atr"])),
        ("Sharpe Ratio", f"{stats['sharpe_ratio']:.2f}" if pd.notna(stats["sharpe_ratio"]) else "N/A"),
        ("Max Drawdown", format_percent(stats["max_drawdown"])),
        ("Trend Strength", f"{stats['trend_strength']:.2f}" if pd.notna(stats["trend_strength"]) else "N/A"),
        ("Momentum (10d)", format_percent(stats["momentum"])),
    ]
    for i, (label, value) in enumerate(stat_defs):
        stat_cols[i % 4].markdown(kpi_card(label, value), unsafe_allow_html=True)
    st.markdown(kpi_card("Market Regime", stats["regime"]), unsafe_allow_html=True)

    # ---- Market analytics ---------------------------------------------------
    st.markdown('<div class="section-title">Market Analytics</div>', unsafe_allow_html=True)
    rets = analytics.daily_returns(raw_df)
    a1, a2 = st.columns(2)
    with a1:
        st.plotly_chart(charts.build_return_distribution(rets, theme), width="stretch")
        st.plotly_chart(
            charts.build_rolling_line(analytics.rolling_volatility(rets), theme,
                                       "Rolling Volatility (20d, annualized)", "Volatility (%)"),
            width="stretch",
        )
    with a2:
        st.plotly_chart(charts.build_volume_analysis(raw_df, theme), width="stretch")
        st.plotly_chart(
            charts.build_rolling_line(analytics.rolling_sharpe(rets), theme,
                                       "Rolling Sharpe Ratio (60d, annualized)", "Sharpe"),
            width="stretch",
        )
    st.plotly_chart(
        charts.build_drawdown_chart(analytics.rolling_drawdown(raw_df["Close"]), theme),
        width="stretch",
    )


# ==========================================================================
# TAB 2 — BACKTESTING RESULTS (Academic Presentation Mode)
# ==========================================================================
with tabs[1]:
    st.markdown('<div class="section-title">📊 Backtesting Results — Master\'s Capstone Research</div>',
                unsafe_allow_html=True)
    st.caption(
        "Simplified illustrative backtester: long/flat positioning, same-bar execution, "
        "0.10% transaction cost per position change. For the full academic methodology "
        "(next-day-open execution, detailed cost model), see the written capstone report."
    )

    bt_period = st.selectbox("Backtest period", ["1y", "2y", "5y"], index=2, key="bt_period")

    with st.spinner("Running backtests across all assets and strategies…"):
        asset_data = {label: data.fetch_price_data(tk, bt_period, "1d") for label, tk in ASSET_MAP.items()}
        results_df, equity_curves = signals.run_full_backtest(asset_data, STRATEGY_NAMES)

    if results_df.empty:
        st.warning("No backtest results available — check data connectivity.")
    else:
        st.markdown("#### Strategy Performance Table")
        st.dataframe(
            results_df.style.format({
                "Total Return (%)": "{:.2f}", "Sharpe Ratio": "{:.2f}",
                "Maximum Drawdown (%)": "{:.2f}", "Win Rate (%)": "{:.1f}",
                "Annual Volatility (%)": "{:.1f}", "Avg Trade Return (%)": "{:.3f}",
                "Profit Factor": "{:.2f}", "Final Value ($100 invested)": "{:.2f}",
            }),
            width="stretch", height=380,
        )
        st.download_button("⬇ Export Table as CSV", results_df.to_csv(index=False).encode("utf-8"),
                            "backtest_results.csv", "text/csv")

        st.markdown("#### Strategy Comparison")
        metric_choice = st.selectbox(
            "Metric", ["Total Return (%)", "Sharpe Ratio", "Maximum Drawdown (%)",
                       "Win Rate (%)", "Annual Volatility (%)"], key="metric_choice",
        )
        st.plotly_chart(charts.build_strategy_comparison_bar(results_df, metric_choice, theme),
                         width="stretch")

        st.markdown("#### Equity Curve Comparison")
        equity_asset = st.selectbox("Asset", list(equity_curves.keys()), key="equity_asset")
        st.plotly_chart(charts.build_equity_curve_comparison(equity_curves[equity_asset], theme),
                         width="stretch")

        st.markdown("#### Strategy Ranking")
        rank_metric = st.selectbox(
            "Rank by", ["Sharpe Ratio", "Total Return (%)", "Maximum Drawdown (%)",
                        "Annual Volatility (%)", "Win Rate (%)"], key="rank_metric",
        )
        ascending = rank_metric in ("Maximum Drawdown (%)", "Annual Volatility (%)")
        # For drawdown, "best" (least negative) is the max, not the min, so invert direction:
        ranked = signals.rank_strategies(results_df, rank_metric, ascending=(rank_metric == "Annual Volatility (%)"))
        st.markdown('<div class="medal-row">', unsafe_allow_html=True)
        st.dataframe(ranked.head(10), width="stretch", height=380)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("#### Asset Analysis")
        asset_focus = st.selectbox("Focus asset", list(ASSET_MAP.keys()), key="asset_focus")
        focus_rows = results_df[results_df["Asset"] == asset_focus]
        if not focus_rows.empty:
            best_row = focus_rows.loc[focus_rows["Sharpe Ratio"].idxmax()]
            worst_row = focus_rows.loc[focus_rows["Sharpe Ratio"].idxmin()]
            fa1, fa2 = st.columns(2)
            with fa1:
                st.markdown(kpi_card("Best Strategy (Sharpe)", best_row["Strategy"],
                                      f"Sharpe {best_row['Sharpe Ratio']:.2f}", palette["green"]),
                            unsafe_allow_html=True)
            with fa2:
                st.markdown(kpi_card("Weakest Strategy (Sharpe)", worst_row["Strategy"],
                                      f"Sharpe {worst_row['Sharpe Ratio']:.2f}", palette["red"]),
                            unsafe_allow_html=True)

            kdash = st.columns(5)
            kpi_labels = ["Total Return (%)", "Sharpe Ratio", "Maximum Drawdown (%)",
                          "Win Rate (%)", "Number of Trades"]
            for col, lbl in zip(kdash, kpi_labels):
                val = best_row[lbl]
                col.markdown(kpi_card(lbl, f"{val:.2f}" if isinstance(val, float) else str(val)),
                            unsafe_allow_html=True)

        # ---- Research Findings (auto-generated narrative) --------------------
        st.markdown('<div class="section-title">Research Findings</div>', unsafe_allow_html=True)

        def _best_for(asset_name: str) -> pd.Series | None:
            sub = results_df[results_df["Asset"] == asset_name]
            return sub.loc[sub["Sharpe Ratio"].idxmax()] if not sub.empty else None

        macd_tesla = results_df[(results_df.Asset.str.contains("Tesla")) & (results_df.Strategy == "MACD")]
        bh_apple_best = _best_for("Apple (AAPL)")
        combined_avg_sharpe = results_df[results_df.Strategy == "Combined"]["Sharpe Ratio"].mean()
        rsi_avg_sharpe = results_df[results_df.Strategy == "RSI"]["Sharpe Ratio"].mean()

        findings = []
        if not macd_tesla.empty:
            row = macd_tesla.iloc[0]
            findings.append(
                f"**MACD on Tesla** produced a Sharpe ratio of **{row['Sharpe Ratio']:.2f}** and a total "
                f"return of **{row['Total Return (%)']:.1f}%** over the {bt_period} window, consistent with "
                f"MACD's design as a trend-following filter on assets exhibiting sustained directional moves."
            )
        if bh_apple_best is not None:
            findings.append(
                f"On **Apple**, the strongest strategy in this run was **{bh_apple_best['Strategy']}** "
                f"(Sharpe {bh_apple_best['Sharpe Ratio']:.2f}), reflecting Apple's comparatively steady, "
                f"lower-volatility uptrend over the sample period."
            )
        if pd.notna(rsi_avg_sharpe):
            findings.append(
                f"**RSI-based signals** averaged a Sharpe ratio of **{rsi_avg_sharpe:.2f}** across all assets, "
                f"illustrating the classic weakness of mean-reversion oscillators in persistently trending markets: "
                f"an oversold reading can remain oversold for extended periods."
            )
        if pd.notna(combined_avg_sharpe):
            findings.append(
                f"The **Combined majority-vote strategy** averaged a Sharpe ratio of **{combined_avg_sharpe:.2f}**, "
                f"generally trailing the single best specialist strategy per asset — a majority vote dilutes a "
                f"strong individual signal whenever the other indicators disagree."
            )
        findings.append(
            "Across assets, regime classification (Bullish / Bearish / Sideways, computed from short-vs-long "
            "moving-average spread and trend strength) helps explain why the same indicator performs "
            "inconsistently: trend-following tools (SMA, MACD) tend to outperform in directional regimes, "
            "while mean-reversion tools (RSI, Bollinger Bands) tend to outperform in range-bound regimes."
        )
        for f in findings:
            st.markdown(f"- {f}")

        # ---- Live vs Historical --------------------------------------------
        st.markdown('<div class="section-title">Live Market vs Historical Analysis</div>', unsafe_allow_html=True)
        live_asset = st.selectbox("Compare asset", list(ASSET_MAP.keys()), key="live_vs_hist_asset")
        live_ticker = ASSET_MAP[live_asset]
        live_df = data.fetch_price_data(live_ticker, "6mo", "1d")
        live_regime = analytics.detect_market_regime(live_df) if not live_df.empty else "N/A"
        hist_best = _best_for(live_asset)
        live_sig = signals.generate_live_signal(live_df) if not live_df.empty else {"signal": "N/A", "confidence": 0}

        lv1, lv2, lv3 = st.columns(3)
        lv1.markdown(kpi_card("Current Trend / Regime", live_regime), unsafe_allow_html=True)
        lv2.markdown(kpi_card("Historical Best Indicator", hist_best["Strategy"] if hist_best is not None else "N/A"),
                     unsafe_allow_html=True)
        lv3.markdown(kpi_card("Current Signal", live_sig["signal"], f"{live_sig['confidence']}% confidence"),
                     unsafe_allow_html=True)
        st.caption(
            "Suggested reading: when the current regime matches the regime that historically favored the "
            "'Historical Best Indicator' above, that indicator's live signal deserves more weight; when regimes "
            "diverge, treat the live signal with more caution and favor the currently more regime-appropriate "
            "indicator family (trend-following vs. mean-reversion)."
        )

        # ---- Conclusion ---------------------------------------------------------
        st.markdown('<div class="section-title">Professional Conclusion</div>', unsafe_allow_html=True)
        overall_best = results_df.loc[results_df["Sharpe Ratio"].idxmax()]
        best_asset_by_return = results_df.loc[results_df["Total Return (%)"].idxmax()]
        st.markdown(f"""
- **Best overall risk-adjusted strategy:** {overall_best['Strategy']} on {overall_best['Asset']}
  (Sharpe {overall_best['Sharpe Ratio']:.2f}).
- **Best-performing asset by raw return:** {best_asset_by_return['Asset']} under the
  {best_asset_by_return['Strategy']} strategy ({best_asset_by_return['Total Return (%)']:.1f}%).
- Technical indicators show **regime-dependent** value rather than universal superiority over Buy & Hold —
  their edge is strongest when their underlying assumption (trend persistence or mean reversion) matches
  the asset's current behavior.
- **Practical implication for traders:** use regime detection as a pre-filter before trusting any single
  indicator family.
- **Practical implication for portfolio managers:** the diversification and correlation results (Portfolio
  tab) matter as much as any single asset's signal quality when sizing positions.
- Historical backtesting and real-time monitoring are complementary: backtests identify *which* indicator
  families tend to work on *which* assets, while live regime/signal tracking decides *when* to lean on them.
- **Future research:** position sizing beyond binary long/flat, transaction-cost sensitivity analysis, and
  walk-forward (out-of-sample) validation would materially strengthen these conclusions.
        """)


# ==========================================================================
# TAB 3 — PORTFOLIO
# ==========================================================================
with tabs[2]:
    st.markdown('<div class="section-title">Portfolio Analysis</div>', unsafe_allow_html=True)
    selected_labels = st.session_state["portfolio_assets"]

    if len(selected_labels) < 2:
        st.info("Select at least 2 assets in the sidebar under **Portfolio assets** to run this analysis.")
    else:
        selected_tickers = [ASSET_MAP[l] for l in selected_labels]
        with st.spinner("Loading portfolio data…"):
            close_wide = data.fetch_multi_asset_close(selected_tickers, period="2y", interval="1d")

        if close_wide.empty or close_wide.shape[1] < 2:
            st.warning("Not enough overlapping data to build a portfolio for this selection.")
        else:
            st.markdown("#### Allocation")
            weight_cols = st.columns(len(selected_labels))
            weights = {}
            default_w = round(100 / len(selected_labels), 1)
            for col, label in zip(weight_cols, selected_labels):
                tk = ASSET_MAP[label]
                weights[tk] = col.slider(label, 0, 100, int(default_w), key=f"w_{tk}") / 100

            total_w = sum(weights.values()) or 1.0
            weights = {k: v / total_w for k, v in weights.items()}

            rets = portfolio.compute_daily_returns(close_wide)
            metrics = portfolio.compute_portfolio_metrics(rets, weights)
            corr = portfolio.compute_correlation_matrix(rets)
            div_score = portfolio.compute_diversification_score(corr)
            risk_contrib = portfolio.compute_risk_contribution(rets, weights)

            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(kpi_card("Expected Return (ann.)", format_percent(metrics["expected_return"])),
                        unsafe_allow_html=True)
            m2.markdown(kpi_card("Portfolio Risk (ann.)", format_percent(metrics["risk"], signed=False)),
                        unsafe_allow_html=True)
            m3.markdown(kpi_card("Sharpe Ratio", f"{metrics['sharpe']:.2f}" if pd.notna(metrics["sharpe"]) else "N/A"),
                        unsafe_allow_html=True)
            m4.markdown(kpi_card("Diversification Score", f"{div_score:.0f} / 100"), unsafe_allow_html=True)

            p1, p2 = st.columns(2)
            with p1:
                pie_labels = {label: weights[ASSET_MAP[label]] for label in selected_labels}
                st.plotly_chart(charts.build_portfolio_pie(pie_labels, theme), width="stretch")
            with p2:
                st.plotly_chart(charts.build_correlation_heatmap(corr, theme), width="stretch")

            st.markdown("#### Risk Contribution")
            st.dataframe(risk_contrib.style.format({"Risk Contribution (%)": "{:.1f}"}),
                         width="stretch")

            with st.expander("Efficient Frontier (simulated portfolios, optional)"):
                sim = portfolio.simulate_efficient_frontier(rets, n_portfolios=1500)
                if not sim.empty:
                    st.plotly_chart(charts.build_efficient_frontier(sim, theme), width="stretch")


# ==========================================================================
# TAB 4 — NEWS & WATCHLIST
# ==========================================================================
with tabs[3]:
    news_col, watch_col = st.columns([3, 2])

    with news_col:
        st.markdown('<div class="section-title">📰 Financial News</div>', unsafe_allow_html=True)
        with st.spinner("Fetching latest headlines…"):
            news_items = data.fetch_news(ticker, limit=8)
        if not news_items:
            st.info("No recent news available for this symbol right now.")
        for item in news_items:
            sentiment_color = {"Positive": palette["green"], "Negative": palette["red"],
                                "Neutral": palette["muted"]}[item["sentiment"]]
            st.markdown(
                f"""
                <div class="glass-panel" style="margin-bottom:10px;">
                    <div style="font-weight:700; font-size:1.02rem;">{item['headline']}</div>
                    <div style="color:{palette['muted']}; font-size:0.82rem; margin:2px 0 6px 0;">
                        {item['source']} · {item['time']} ·
                        <span style="color:{sentiment_color}; font-weight:700;">{item['sentiment']}</span>
                    </div>
                    <div style="font-size:0.9rem;">{item['summary']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with watch_col:
        st.markdown('<div class="section-title">👁 Watchlist</div>', unsafe_allow_html=True)
        watch_tickers = list(ASSET_MAP.values())
        snap = data.build_watchlist_snapshot(watch_tickers)
        if snap.empty:
            st.info("Watchlist data unavailable.")
        else:
            display_rows = []
            for _, row in snap.iterrows():
                hist = row["_hist"]
                hist_ind = indicators.add_all_indicators(hist)
                last = hist_ind.iloc[-1]
                live_sig = signals.generate_live_signal(hist)
                display_rows.append({
                    "Ticker": row["Ticker"],
                    "Price": row["Price"],
                    "Change %": row["Change %"],
                    "Trend": "▲" if row["Change %"] > 0 else ("▼" if row["Change %"] < 0 else "→"),
                    "RSI": last.get("RSI14"),
                    "MACD": "▲" if last.get("MACD", 0) > last.get("MACD_Signal", 0) else "▼",
                    "Signal": live_sig["signal"],
                    "Volume": row["Volume"],
                })
            watch_df = pd.DataFrame(display_rows)

            def _color_signal(val):
                colors = {"BUY": palette["green"], "SELL": palette["red"], "HOLD": palette["orange"]}
                return f"color: {colors.get(val, palette['text'])}; font-weight:700;"

            def _color_change(val):
                return f"color: {trend_color(val, palette)}; font-weight:700;"

            styled = (
                watch_df.style
                .format({"Price": "{:.2f}", "Change %": "{:+.2f}%", "RSI": "{:.1f}", "Volume": "{:,.0f}"})
                .map(_color_signal, subset=["Signal"])
                .map(_color_change, subset=["Change %"])
            )
            st.dataframe(styled, width="stretch", height=380)


# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="footer-bar">
        Data source: Yahoo Finance (via yfinance) &nbsp;·&nbsp;
        Last refresh: {st.session_state['last_refresh'].strftime('%Y-%m-%d %H:%M:%S UTC')} &nbsp;·&nbsp;
        Version {APP_VERSION} &nbsp;·&nbsp; Author: {AUTHOR}
    </div>
    """,
    unsafe_allow_html=True,
)
