"""
indicators.py
-------------
Pure, dependency-light implementations of the four technical indicators
used throughout the app (SMA, RSI, MACD, Bollinger Bands) plus ATR for
volatility/risk stats. Implemented directly with pandas/numpy so the app
does not hard-depend on `pandas_ta` (which has had installation issues
across platforms) -- the formulas match the standard definitions used in
the accompanying capstone research.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def compute_sma(close: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average over `window` periods."""
    return close.rolling(window=window, min_periods=window).mean()


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (Wilder's smoothing), classic 0-100 oscillator.
    RSI = 100 - 100 / (1 + RS), RS = avg gain / avg loss over `period`.
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)  # neutral when undefined (e.g. no losses at all)
    return rsi


def compute_macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """
    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(signal) of MACD Line
    Histogram = MACD Line - Signal Line
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame(
        {"MACD": macd_line, "MACD_Signal": signal_line, "MACD_Hist": histogram}
    )


def compute_bollinger_bands(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands: middle = SMA(window), upper/lower = middle +/- num_std * rolling std."""
    mid = compute_sma(close, window)
    std = close.rolling(window=window, min_periods=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return pd.DataFrame({"BB_Mid": mid, "BB_Upper": upper, "BB_Lower": lower})


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range, a common volatility/risk-sizing measure."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of `df` (OHLCV) with SMA20/50, RSI14, MACD/Signal/Hist,
    Bollinger Bands and ATR14 appended as new columns. Safe to call on
    short/empty frames -- indicators will simply be NaN where insufficient
    history exists.
    """
    if df.empty or "Close" not in df:
        return df.copy()

    out = df.copy()
    close = out["Close"]

    out["SMA20"] = compute_sma(close, 20)
    out["SMA50"] = compute_sma(close, 50)
    out["RSI14"] = compute_rsi(close, 14)

    macd_df = compute_macd(close, 12, 26, 9)
    out = pd.concat([out, macd_df], axis=1)

    bb_df = compute_bollinger_bands(close, 20, 2.0)
    out = pd.concat([out, bb_df], axis=1)

    if {"High", "Low"}.issubset(out.columns):
        out["ATR14"] = compute_atr(out, 14)

    return out
