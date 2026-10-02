"""
utils.py
--------
Shared constants, formatting helpers, and CSS/theme injection utilities
used across the whole Financial Market Dashboard application.

Keeping these in one module avoids duplicating "magic numbers" (tickers,
timeframe maps, colors) across data.py, charts.py and app.py.
"""

from __future__ import annotations
import datetime as dt
import streamlit as st


# --------------------------------------------------------------------------
# Static configuration
# --------------------------------------------------------------------------

# Human-readable label -> Yahoo Finance ticker
ASSET_MAP: dict[str, str] = {
    "Apple (AAPL)": "AAPL",
    "Tesla (TSLA)": "TSLA",
    "S&P 500 (^GSPC)": "^GSPC",
    "Bitcoin (BTC-USD)": "BTC-USD",
    "EUR/USD (EURUSD=X)": "EURUSD=X",
}

# Human-readable label -> (yfinance period, yfinance interval)
TIMEFRAME_MAP: dict[str, tuple[str, str]] = {
    "1 Day": ("1d", "5m"),
    "5 Days": ("5d", "15m"),
    "1 Month": ("1mo", "1h"),
    "3 Months": ("3mo", "1d"),
    "6 Months": ("6mo", "1d"),
    "1 Year": ("1y", "1d"),
    "5 Years": ("5y", "1wk"),
}

INDICATOR_OPTIONS: list[str] = ["SMA", "RSI", "MACD", "Bollinger Bands"]

STRATEGY_NAMES: list[str] = ["SMA", "RSI", "MACD", "Bollinger Bands", "Combined"]

# Assets that trade 24/7 (crypto, FX) vs. exchange-hours assets (equities/index)
CONTINUOUS_MARKETS = {"BTC-USD", "EURUSD=X"}

# Risk-free rate assumption used for Sharpe-ratio style calculations (annualized)
RISK_FREE_RATE = 0.0

# Transaction cost assumption for the simplified in-app backtester
TRANSACTION_COST = 0.001  # 0.10% per trade, round turn approximated per side

APP_VERSION = "1.0.0"
AUTHOR = "KIRUA"

DARK_COLORS = {
    "bg": "#0e1117",
    "panel": "#161b22",
    "border": "#2a2f3a",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "green": "#26a69a",
    "red": "#ef5350",
    "orange": "#f5a623",
    "blue": "#4c8bf5",
    "accent": "#7c5cff",
}

LIGHT_COLORS = {
    "bg": "#f5f6f8",
    "panel": "#ffffff",
    "border": "#e0e2e7",
    "text": "#1a1d23",
    "muted": "#5c6370",
    "green": "#0d9488",
    "red": "#dc2626",
    "orange": "#d97706",
    "blue": "#2563eb",
    "accent": "#6d28d9",
}


def get_palette(theme: str) -> dict:
    """Return the color palette dict for the given theme ('dark' or 'light')."""
    return DARK_COLORS if theme == "dark" else LIGHT_COLORS


def plotly_template(theme: str) -> str:
    """Map our theme name to a Plotly built-in template name."""
    return "plotly_dark" if theme == "dark" else "plotly_white"


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------

def format_currency(value: float | None, symbol: str = "$", decimals: int = 2) -> str:
    """Format a numeric value as currency, gracefully handling None/NaN."""
    if value is None:
        return "N/A"
    try:
        if value != value:  # NaN check without importing numpy here
            return "N/A"
        return f"{symbol}{value:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def format_percent(value: float | None, decimals: int = 2, signed: bool = True) -> str:
    """Format a fractional or already-percent numeric value as a percent string."""
    if value is None:
        return "N/A"
    try:
        if value != value:
            return "N/A"
        sign = "+" if (signed and value > 0) else ""
        return f"{sign}{value:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def format_large_number(value: float | None) -> str:
    """Format large numbers (e.g. volume) using K / M / B suffixes."""
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    abs_v = abs(value)
    if abs_v >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs_v >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs_v >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:.0f}"


def trend_color(value: float | None, palette: dict) -> str:
    """Return green/red/muted hex depending on the sign of `value`."""
    if value is None or value != value:
        return palette["muted"]
    if value > 0:
        return palette["green"]
    if value < 0:
        return palette["red"]
    return palette["muted"]


def is_market_open(ticker: str) -> bool:
    """
    Very lightweight market-hours heuristic.
    Crypto and FX trade continuously; equities/index are approximated as
    open Mon-Fri 13:30-20:00 UTC (i.e. 9:30-16:00 US Eastern, ignoring DST
    edge cases -- a full exchange-calendar lookup is out of scope here).
    """
    if ticker in CONTINUOUS_MARKETS:
        return True
    now = dt.datetime.utcnow()
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=13, minute=30, second=0, microsecond=0)
    close_t = now.replace(hour=20, minute=0, second=0, microsecond=0)
    return open_t <= now <= close_t


# --------------------------------------------------------------------------
# CSS / theming
# --------------------------------------------------------------------------

def inject_css(theme: str, presentation_mode: bool = False) -> None:
    """Inject custom CSS to give the app a Bloomberg/TradingView-inspired look."""
    p = get_palette(theme)
    kpi_font = "2.6rem" if presentation_mode else "1.65rem"
    label_font = "1rem" if presentation_mode else "0.78rem"
    pad = "1.6rem" if presentation_mode else "1rem"

    css = f"""
    <style>
        .stApp {{
            background-color: {p['bg']};
            color: {p['text']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {p['panel']};
            border-right: 1px solid {p['border']};
        }}
        /* Native Streamlit text follows Streamlit's own theme, not ours: force readable colors */
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stWidgetLabel"],
        .stApp [data-testid="stWidgetLabel"] p,
        .stApp label, .stApp label p,
        .stApp [data-testid="stExpander"] summary,
        .stApp [data-testid="stMetricLabel"],
        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stText"],
        .stApp [data-testid="stTable"],
        .stApp button[data-baseweb="tab"] p,
        section[data-testid="stSidebar"] * {{
            color: {p['text']};
        }}
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] p,
        .stApp small {{
            color: {p['muted']};
        }}
        .stApp button[data-baseweb="tab"][aria-selected="true"] p {{
            color: {p['accent']};
            font-weight: 700;
        }}
        /* Inputs, select boxes and their dropdown menus */
        .stApp div[data-baseweb="select"] > div,
        .stApp div[data-baseweb="input"] > div,
        .stApp input, .stApp textarea {{
            background-color: {p['panel']};
            color: {p['text']};
            border-color: {p['border']};
        }}
        .stApp div[data-baseweb="select"] span,
        .stApp div[data-baseweb="select"] svg,
        .stApp div[data-baseweb="tag"] span {{
            color: {p['text']};
            fill: {p['text']};
        }}
        div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li {{
            background-color: {p['panel']};
            color: {p['text']};
        }}
        .stApp [data-testid="stHeader"] {{
            background-color: {p['bg']};
        }}
        .stApp .stButton button, .stApp .stDownloadButton button {{
            background-color: {p['panel']};
            color: {p['text']};
            border: 1px solid {p['border']};
        }}
        .stApp .stButton button:hover {{
            border-color: {p['accent']};
            color: {p['accent']};
        }}
        div[data-testid="stMetric"], .kpi-card {{
            background: linear-gradient(145deg, {p['panel']}, {p['bg']});
            border: 1px solid {p['border']};
            border-radius: 14px;
            padding: {pad};
            box-shadow: 0 4px 18px rgba(0,0,0,0.18);
        }}
        .kpi-label {{
            font-size: {label_font};
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {p['muted']};
            margin-bottom: 4px;
        }}
        .kpi-value {{
            font-size: {kpi_font};
            font-weight: 700;
            color: {p['text']};
        }}
        .kpi-sub {{
            font-size: 0.85rem;
            font-weight: 600;
        }}
        .badge {{
            display: inline-block;
            padding: 0.55em 1.4em;
            border-radius: 999px;
            font-weight: 800;
            font-size: {"1.6rem" if presentation_mode else "1.1rem"};
            letter-spacing: 0.05em;
            text-align: center;
        }}
        .badge-buy {{ background: rgba(38,166,154,0.18); color: {p['green']}; border: 2px solid {p['green']}; }}
        .badge-sell {{ background: rgba(239,83,80,0.18); color: {p['red']}; border: 2px solid {p['red']}; }}
        .badge-hold {{ background: rgba(245,166,35,0.18); color: {p['orange']}; border: 2px solid {p['orange']}; }}
        .section-title {{
            font-size: {"2rem" if presentation_mode else "1.3rem"};
            font-weight: 700;
            border-left: 4px solid {p['accent']};
            padding-left: 0.6em;
            margin: 1.2em 0 0.6em 0;
        }}
        .glass-panel {{
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(6px);
            border: 1px solid {p['border']};
            border-radius: 14px;
            padding: 1rem 1.2rem;
        }}
        .footer-bar {{
            border-top: 1px solid {p['border']};
            margin-top: 2rem;
            padding-top: 0.8rem;
            color: {p['muted']};
            font-size: 0.8rem;
        }}
        .medal-row {{ font-size: 1.4rem; }}
        div[data-baseweb="tab-list"] {{
            gap: 4px;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", sub_color: str | None = None) -> str:
    """Return HTML for a single custom KPI card (used instead of st.metric for full styling control)."""
    sub_html = f'<div class="kpi-sub" style="color:{sub_color or "inherit"}">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {sub_html}
    </div>
    """
