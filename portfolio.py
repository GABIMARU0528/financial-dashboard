"""
portfolio.py
------------
Multi-asset portfolio analytics: allocation, expected return/risk,
correlation, diversification score, risk contribution, and a simple
Monte-Carlo efficient frontier.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def compute_daily_returns(close_prices: pd.DataFrame) -> pd.DataFrame:
    """Wide DataFrame of Close prices (columns = tickers) -> daily pct-change returns."""
    return close_prices.pct_change().dropna(how="all")


def compute_correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix of asset daily returns."""
    return returns.corr()


def compute_portfolio_metrics(returns: pd.DataFrame, weights: dict[str, float]) -> dict:
    """
    Compute annualized expected return and risk (volatility) for a weighted
    portfolio, plus the resulting Sharpe ratio (risk-free = 0).
    """
    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return {"expected_return": np.nan, "risk": np.nan, "sharpe": np.nan}

    w = np.array([weights[t] for t in tickers])
    w = w / w.sum() if w.sum() != 0 else w

    r = returns[tickers].dropna()
    mean_daily = r.mean().values
    cov = r.cov().values

    port_daily_return = float(np.dot(w, mean_daily))
    port_daily_var = float(np.dot(w.T, np.dot(cov, w)))
    port_daily_vol = np.sqrt(max(port_daily_var, 0))

    expected_return = port_daily_return * TRADING_DAYS_PER_YEAR * 100
    risk = port_daily_vol * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
    sharpe = (expected_return / risk) if risk > 0 else np.nan

    return {"expected_return": expected_return, "risk": risk, "sharpe": sharpe}


def compute_diversification_score(corr_matrix: pd.DataFrame) -> float:
    """
    Simple diversification score in [0, 100]: 100 means fully uncorrelated
    (or negatively correlated) assets, 0 means perfectly correlated.
    Defined as 100 * (1 - average off-diagonal correlation), clipped to [0, 100].
    """
    if corr_matrix.empty or corr_matrix.shape[0] < 2:
        return np.nan
    n = corr_matrix.shape[0]
    off_diag_sum = corr_matrix.values.sum() - np.trace(corr_matrix.values)
    avg_corr = off_diag_sum / (n * (n - 1))
    score = 100 * (1 - avg_corr)
    return float(np.clip(score, 0, 100))


def compute_risk_contribution(returns: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    """
    Percentage contribution of each asset to total portfolio variance
    (Euler / marginal risk contribution decomposition).
    """
    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return pd.DataFrame(columns=["Asset", "Risk Contribution (%)"])

    w = np.array([weights[t] for t in tickers])
    w = w / w.sum() if w.sum() != 0 else w
    cov = returns[tickers].cov().values

    port_var = float(np.dot(w.T, np.dot(cov, w)))
    if port_var <= 0:
        contrib = np.zeros(len(tickers))
    else:
        marginal = np.dot(cov, w)
        contrib = w * marginal / port_var * 100

    return pd.DataFrame({"Asset": tickers, "Risk Contribution (%)": contrib}).sort_values(
        "Risk Contribution (%)", ascending=False
    )


def simulate_efficient_frontier(returns: pd.DataFrame, n_portfolios: int = 3000, seed: int = 42) -> pd.DataFrame:
    """
    Simple Monte-Carlo simulation of random long-only portfolios to sketch
    an approximate efficient frontier (return vs. risk scatter).
    """
    tickers = list(returns.columns)
    n = len(tickers)
    if n < 2:
        return pd.DataFrame(columns=["Return", "Risk", "Sharpe"])

    rng = np.random.default_rng(seed)
    mean_daily = returns.mean().values
    cov = returns.cov().values

    results = []
    for _ in range(n_portfolios):
        w = rng.random(n)
        w /= w.sum()
        port_return = float(np.dot(w, mean_daily)) * TRADING_DAYS_PER_YEAR * 100
        port_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w)))) * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
        sharpe = port_return / port_vol if port_vol > 0 else np.nan
        results.append({"Return": port_return, "Risk": port_vol, "Sharpe": sharpe})

    return pd.DataFrame(results)
