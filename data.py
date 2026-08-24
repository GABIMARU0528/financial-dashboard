"""
data.py
-------
All external data access (Yahoo Finance via yfinance) lives here, wrapped
in Streamlit caching so the rest of the app never talks to the network
directly. Centralizing this also makes it trivial to swap the data
provider later without touching charts/indicators/signals.
"""

from __future__ import annotations
import datetime as dt
import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf


# --------------------------------------------------------------------------
# Price history
# --------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def fetch_price_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """
    Download OHLCV history for a single ticker.

    Returns a DataFrame with columns: Open, High, Low, Close, Volume
    indexed by datetime, with a flat (non-MultiIndex) column structure
    regardless of the yfinance version's default return shape.
    """
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if df is None or df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    # yfinance sometimes returns MultiIndex columns (Price, Ticker) when
    # downloading a single symbol depending on version -- flatten defensively.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[~df.index.duplicated(keep="last")]
    return df.dropna(how="all")


@st.cache_data(ttl=60, show_spinner=False)
def fetch_multi_asset_close(tickers: list[str], period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Download Close prices for multiple tickers and align them into a single
    wide DataFrame (columns = tickers). Used for correlation matrices and
    portfolio analysis.
    """
    frames = {}
    for t in tickers:
        d = fetch_price_data(t, period, interval)
        if not d.empty:
            frames[t] = d["Close"]
    if not frames:
        return pd.DataFrame()
    combined = pd.DataFrame(frames)
    return combined.dropna(how="all")


# --------------------------------------------------------------------------
# Ticker info / KPIs
# --------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def fetch_ticker_info(ticker: str) -> dict:
    """
    Fetch lightweight snapshot info (fast_info) plus a couple of fields
    from the heavier `.info` dict, with graceful fallbacks since Yahoo
    frequently omits fields for FX/crypto/index tickers.
    """
    info: dict = {}
    try:
        tk = yf.Ticker(ticker)
        fast = tk.fast_info
        info["last_price"] = getattr(fast, "last_price", None)
        info["previous_close"] = getattr(fast, "previous_close", None)
        info["open"] = getattr(fast, "open", None)
        info["day_high"] = getattr(fast, "day_high", None)
        info["day_low"] = getattr(fast, "day_low", None)
        info["volume"] = getattr(fast, "last_volume", None)
        info["year_high"] = getattr(fast, "year_high", None)
        info["year_low"] = getattr(fast, "year_low", None)
        info["currency"] = getattr(fast, "currency", "USD")
    except Exception:
        pass

    # Fallback: derive missing fields from recent daily history if fast_info failed.
    if not info.get("last_price"):
        hist = fetch_price_data(ticker, "5d", "1d")
        if not hist.empty:
            info["last_price"] = float(hist["Close"].iloc[-1])
            info["previous_close"] = float(hist["Close"].iloc[-2]) if len(hist) > 1 else float(hist["Close"].iloc[-1])
            info["open"] = float(hist["Open"].iloc[-1])
            info["day_high"] = float(hist["High"].iloc[-1])
            info["day_low"] = float(hist["Low"].iloc[-1])
            info["volume"] = float(hist["Volume"].iloc[-1]) if "Volume" in hist else None

    if not info.get("year_high") or not info.get("year_low"):
        yr = fetch_price_data(ticker, "1y", "1d")
        if not yr.empty:
            info["year_high"] = float(yr["High"].max())
            info["year_low"] = float(yr["Low"].min())

    return info


# --------------------------------------------------------------------------
# News (free, no API key: yfinance's built-in news feed)
# --------------------------------------------------------------------------

_POSITIVE_WORDS = {
    "surge", "soars", "gain", "gains", "rally", "beats", "beat", "record",
    "upgrade", "growth", "strong", "profit", "bullish", "outperform", "rise", "rises",
}
_NEGATIVE_WORDS = {
    "plunge", "falls", "fall", "drop", "drops", "slump", "miss", "misses",
    "downgrade", "loss", "losses", "bearish", "underperform", "cut", "warns", "warning",
    "lawsuit", "recall", "crash",
}


def _simple_sentiment(headline: str) -> str:
    """
    Very lightweight lexicon-based sentiment tag for headlines.
    Not a substitute for a real NLP model -- intended purely as a quick
    visual cue (Positive / Negative / Neutral) in the news feed.
    """
    words = {w.strip(".,!?:;\"'").lower() for w in headline.split()}
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    if pos > neg:
        return "Positive"
    if neg > pos:
        return "Negative"
    return "Neutral"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_news(ticker: str, limit: int = 8) -> list[dict]:
    """Fetch recent news headlines for a ticker via yfinance (no API key required)."""
    items = []
    try:
        tk = yf.Ticker(ticker)
        raw_news = tk.news or []
    except Exception:
        raw_news = []

    for entry in raw_news[:limit]:
        # yfinance news items may be nested under a "content" key depending on version.
        content = entry.get("content", entry)
        headline = content.get("title") or entry.get("title") or "Untitled"
        source = (
            (content.get("provider") or {}).get("displayName")
            if isinstance(content.get("provider"), dict)
            else entry.get("publisher")
        ) or "Unknown source"
        ts = content.get("pubDate") or entry.get("providerPublishTime")
        pub_time = "N/A"
        try:
            if isinstance(ts, (int, float)):
                pub_time = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC")
            elif isinstance(ts, str):
                pub_time = ts[:16].replace("T", " ")
        except Exception:
            pass
        summary = content.get("summary") or content.get("description") or ""
        items.append(
            {
                "headline": headline,
                "source": source,
                "time": pub_time,
                "summary": summary[:280],
                "sentiment": _simple_sentiment(headline),
            }
        )
    return items


# --------------------------------------------------------------------------
# Watchlist snapshot
# --------------------------------------------------------------------------

@st.cache_data(ttl=30, show_spinner=False)
def build_watchlist_snapshot(tickers: list[str]) -> pd.DataFrame:
    """Build a compact one-row-per-ticker snapshot table for the watchlist panel."""
    rows = []
    for t in tickers:
        hist = fetch_price_data(t, "3mo", "1d")
        if hist.empty or len(hist) < 2:
            continue
        last = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        change_pct = (last / prev - 1) * 100 if prev else np.nan
        rows.append(
            {
                "Ticker": t,
                "Price": last,
                "Change %": change_pct,
                "Volume": float(hist["Volume"].iloc[-1]) if "Volume" in hist else np.nan,
                "_hist": hist,
            }
        )
    return pd.DataFrame(rows)
