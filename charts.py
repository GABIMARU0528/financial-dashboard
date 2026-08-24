"""
charts.py
---------
All Plotly figure construction lives here so app.py stays focused on
layout/state. Every function returns a `go.Figure` ready for
`st.plotly_chart(fig, width="stretch")`.

Charts respect the active theme via `template` (plotly_dark / plotly_white)
and the shared color palette from utils.get_palette so the whole app is
visually consistent.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from utils import get_palette


PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def _layout(fig: go.Figure, theme: str, title: str = "", height: int = 480) -> go.Figure:
    p = get_palette(theme)
    fig.update_layout(
        template="plotly_dark" if theme == "dark" else "plotly_white",
        title=title,
        height=height,
        margin=dict(l=40, r=20, t=50 if title else 20, b=30),
        paper_bgcolor=p["panel"],
        plot_bgcolor=p["panel"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return fig


def build_candlestick_chart(
    df: pd.DataFrame, indicators_selected: list[str], theme: str, asset_label: str
) -> go.Figure:
    """Main price chart: candlesticks + volume + selected overlays (SMA/Bollinger)."""
    p = get_palette(theme)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.03
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name=asset_label, increasing_line_color=p["green"], decreasing_line_color=p["red"],
        ),
        row=1, col=1,
    )

    if "SMA" in indicators_selected and "SMA20" in df:
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], name="SMA 20",
                                  line=dict(color=p["blue"], width=1.4)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA 50",
                                  line=dict(color=p["orange"], width=1.4)), row=1, col=1)

    if "Bollinger Bands" in indicators_selected and "BB_Upper" in df:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
                                  line=dict(color=p["accent"], width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                                  line=dict(color=p["accent"], width=1, dash="dot"),
                                  fill="tonexty", fillcolor="rgba(124,92,255,0.08)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Mid"], name="BB Mid",
                                  line=dict(color=p["muted"], width=1)), row=1, col=1)

    if "Volume" in df:
        vol_colors = np.where(df["Close"] >= df["Open"], p["green"], p["red"])
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", marker_color=vol_colors,
                              opacity=0.6), row=2, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return _layout(fig, theme, height=560)


def build_rsi_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    p = get_palette(theme)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI14"], name="RSI (14)", line=dict(color=p["blue"])))
    fig.add_hline(y=70, line=dict(color=p["red"], dash="dash"), annotation_text="Overbought (70)")
    fig.add_hline(y=30, line=dict(color=p["green"], dash="dash"), annotation_text="Oversold (30)")
    fig.update_yaxes(range=[0, 100])
    return _layout(fig, theme, height=260)


def build_macd_chart(df: pd.DataFrame, theme: str) -> go.Figure:
    p = get_palette(theme)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color=p["blue"])))
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal", line=dict(color=p["orange"])))
    hist_colors = np.where(df["MACD_Hist"] >= 0, p["green"], p["red"])
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], name="Histogram", marker_color=hist_colors, opacity=0.6))
    return _layout(fig, theme, height=260)


def build_return_distribution(returns: pd.Series, theme: str) -> go.Figure:
    p = get_palette(theme)
    fig = px.histogram(returns * 100, nbins=60, color_discrete_sequence=[p["blue"]])
    fig.update_layout(showlegend=False, xaxis_title="Daily Return (%)", yaxis_title="Frequency")
    return _layout(fig, theme, title="Daily Return Distribution", height=340)


def build_rolling_line(series: pd.Series, theme: str, title: str, y_title: str) -> go.Figure:
    p = get_palette(theme)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series, line=dict(color=p["accent"]), fill="tozeroy",
                              fillcolor="rgba(124,92,255,0.10)"))
    fig.update_yaxes(title_text=y_title)
    return _layout(fig, theme, title=title, height=300)


def build_correlation_heatmap(corr: pd.DataFrame, theme: str) -> go.Figure:
    fig = px.imshow(
        corr, text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, aspect="auto"
    )
    return _layout(fig, theme, title="Correlation Matrix", height=420)


def build_volume_analysis(df: pd.DataFrame, theme: str) -> go.Figure:
    p = get_palette(theme)
    colors = np.where(df["Close"] >= df["Open"], p["green"], p["red"])
    fig = go.Figure(go.Bar(x=df.index, y=df["Volume"], marker_color=colors, opacity=0.75))
    fig.update_yaxes(title_text="Volume")
    return _layout(fig, theme, title="Volume Analysis", height=300)


def build_strategy_comparison_bar(results_df: pd.DataFrame, metric: str, theme: str) -> go.Figure:
    p = get_palette(theme)
    fig = px.bar(
        results_df, x="Asset", y=metric, color="Strategy", barmode="group",
        color_discrete_sequence=[p["blue"], p["green"], p["orange"], p["accent"], p["red"]],
    )
    return _layout(fig, theme, title=f"{metric} by Strategy", height=420)


def build_equity_curve_comparison(curves: dict[str, pd.Series], theme: str) -> go.Figure:
    p = get_palette(theme)
    palette_cycle = [p["blue"], p["green"], p["orange"], p["accent"], p["red"], p["muted"]]
    fig = go.Figure()
    for i, (name, series) in enumerate(curves.items()):
        if series is None or series.empty:
            continue
        style = dict(width=3, dash="dash") if name == "Buy & Hold" else dict(width=2)
        fig.add_trace(go.Scatter(x=series.index, y=(series - 1) * 100, name=name,
                                  line=dict(color=palette_cycle[i % len(palette_cycle)], **style)))
    fig.update_yaxes(title_text="Cumulative Return (%)")
    return _layout(fig, theme, title="Equity Curve Comparison", height=460)


def build_drawdown_chart(drawdown: pd.Series, theme: str) -> go.Figure:
    p = get_palette(theme)
    fig = go.Figure(go.Scatter(x=drawdown.index, y=drawdown, fill="tozeroy",
                                line=dict(color=p["red"]), fillcolor="rgba(239,83,80,0.15)"))
    fig.update_yaxes(title_text="Drawdown (%)")
    return _layout(fig, theme, title="Rolling Drawdown", height=300)


def build_portfolio_pie(weights: dict[str, float], theme: str) -> go.Figure:
    p = get_palette(theme)
    labels = list(weights.keys())
    values = list(weights.values())
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.45,
                            marker=dict(colors=[p["blue"], p["green"], p["orange"], p["accent"], p["red"]])))
    return _layout(fig, theme, title="Portfolio Allocation", height=380)


def build_efficient_frontier(sim_df: pd.DataFrame, theme: str) -> go.Figure:
    fig = px.scatter(
        sim_df, x="Risk", y="Return", color="Sharpe", color_continuous_scale="Viridis",
        labels={"Risk": "Annualized Risk (%)", "Return": "Annualized Return (%)"},
    )
    return _layout(fig, theme, title="Efficient Frontier (Simulated Portfolios)", height=440)
