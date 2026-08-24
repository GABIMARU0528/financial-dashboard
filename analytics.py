"""
analytics.py
------------
Market Analytics helpers: return distributions, rolling risk metrics,
trend/momentum/regime classification. These feed the "Market Analytics"
and "Market Statistics" sections of the dashboard.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def daily_returns(df: pd.DataFrame) -> pd.Series:
    """Daily percentage returns from a Close price series."""
    if df.empty or "Close" not in df:
        return pd.Series(dtype=float)
    return df["Close"].pct_change().dropna()


def annualized_return(returns: pd.Series) -> float:
    if returns.empty:
        return np.nan
    return float(returns.mean() * TRADING_DAYS_PER_YEAR * 100)


def annualized_volatility(returns: pd.Series) -> float:
    if returns.empty:
        return np.nan
    return float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100)


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    if returns.empty or returns.std() == 0:
        return np.nan
    ann_ret = returns.mean() * TRADING_DAYS_PER_YEAR
    ann_vol = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    return float((ann_ret - risk_free) / ann_vol)


def max_drawdown(close: pd.Series) -> float:
    if close.empty:
        return np.nan
    cummax = close.cummax()
    dd = (close / cummax - 1) * 100
    return float(dd.min())


def rolling_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    """Rolling annualized volatility (%)."""
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100


def rolling_sharpe(returns: pd.Series, window: int = 60, risk_free: float = 0.0) -> pd.Series:
    """Rolling annualized Sharpe ratio."""
    roll_mean = returns.rolling(window).mean() * TRADING_DAYS_PER_YEAR
    roll_std = returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    return (roll_mean - risk_free) / roll_std.replace(0, np.nan)


def rolling_drawdown(close: pd.Series) -> pd.Series:
    """Point-in-time drawdown (%) from the running maximum, over the full series."""
    cummax = close.cummax()
    return (close / cummax - 1) * 100


def trend_strength(df: pd.DataFrame, window: int = 20) -> float:
    """
    Simple proxy for trend strength: R^2 of a linear fit of Close price
    over the last `window` bars (0 = no trend / pure noise, 1 = perfectly linear trend).
    """
    if df.empty or len(df) < window:
        return np.nan
    y = df["Close"].tail(window).values
    x = np.arange(len(y))
    if np.std(y) == 0:
        return 0.0
    coeffs = np.polyfit(x, y, 1)
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(np.clip(r2, 0, 1))


def momentum(df: pd.DataFrame, period: int = 10) -> float:
    """Percentage price change over the last `period` bars."""
    if df.empty or len(df) <= period:
        return np.nan
    close = df["Close"]
    return float((close.iloc[-1] / close.iloc[-1 - period] - 1) * 100)


def detect_market_regime(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> str:
    """
    Classify the current regime as Bullish / Bearish / Sideways using the
    slope of a short SMA relative to a long SMA plus recent trend strength.
    """
    if df.empty or len(df) < long_window + 5:
        return "Insufficient data"

    close = df["Close"]
    sma_short = close.rolling(short_window).mean()
    sma_long = close.rolling(long_window).mean()

    spread_now = (sma_short.iloc[-1] - sma_long.iloc[-1]) / sma_long.iloc[-1] * 100
    strength = trend_strength(df, window=short_window)

    if strength < 0.15:
        return "Sideways"
    if spread_now > 0.5:
        return "Bullish"
    if spread_now < -0.5:
        return "Bearish"
    return "Sideways"


def market_summary_stats(df: pd.DataFrame) -> dict:
    """Bundle of headline Market Statistics section values."""
    from indicators import compute_atr  # local import avoids a circular import at module load

    r = daily_returns(df)
    atr = compute_atr(df).iloc[-1] if len(df) > 14 else np.nan
    return {
        "daily_return": float(r.iloc[-1] * 100) if not r.empty else np.nan,
        "annual_return": annualized_return(r),
        "volatility": annualized_volatility(r),
        "atr": float(atr) if pd.notna(atr) else np.nan,
        "sharpe_ratio": sharpe_ratio(r),
        "max_drawdown": max_drawdown(df["Close"]) if "Close" in df else np.nan,
        "trend_strength": trend_strength(df),
        "momentum": momentum(df),
        "regime": detect_market_regime(df),
    }
