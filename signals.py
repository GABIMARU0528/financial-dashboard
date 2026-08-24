"""
signals.py
----------
Two related but distinct responsibilities:

1. `generate_live_signal` — turns the *latest* row of indicator data into a
   BUY / SELL / HOLD badge with a confidence % and indicator-agreement
   score, for the real-time dashboard.

2. `backtest_strategy` / `run_full_backtest` — a SIMPLIFIED historical
   backtester (long/flat, same-day close execution, flat transaction cost)
   used to power the "Backtesting Results" page. This intentionally does
   NOT reproduce the exact capstone methodology (next-day-open execution,
   0.10% cost model, etc.) -- it is a lighter-weight illustrative engine
   for the live dashboard, per project scope.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

from indicators import add_all_indicators
from utils import TRANSACTION_COST, RISK_FREE_RATE

TRADING_DAYS_PER_YEAR = 252


# --------------------------------------------------------------------------
# Live signal (dashboard badge)
# --------------------------------------------------------------------------

def generate_live_signal(df: pd.DataFrame) -> dict:
    """
    Evaluate the four capstone indicators on the most recent bar and combine
    them into a single BUY / SELL / HOLD call.

    Rules (majority vote across 4 independent conditions):
      BUY  vote if SMA20 > SMA50, RSI < 30, MACD > Signal, Close <= BB_Lower
      SELL vote if SMA20 < SMA50, RSI > 70, MACD < Signal, Close >= BB_Upper
    """
    if df.empty or len(df) < 2:
        return {"signal": "HOLD", "confidence": 0.0, "agreement": "0/4", "votes": {}}

    d = add_all_indicators(df)
    last = d.iloc[-1]

    votes = {}
    buy_votes = sell_votes = 0

    if pd.notna(last.get("SMA20")) and pd.notna(last.get("SMA50")):
        if last["SMA20"] > last["SMA50"]:
            votes["SMA"] = "BUY"
            buy_votes += 1
        elif last["SMA20"] < last["SMA50"]:
            votes["SMA"] = "SELL"
            sell_votes += 1
        else:
            votes["SMA"] = "NEUTRAL"
    else:
        votes["SMA"] = "N/A"

    if pd.notna(last.get("RSI14")):
        if last["RSI14"] < 30:
            votes["RSI"] = "BUY"
            buy_votes += 1
        elif last["RSI14"] > 70:
            votes["RSI"] = "SELL"
            sell_votes += 1
        else:
            votes["RSI"] = "NEUTRAL"
    else:
        votes["RSI"] = "N/A"

    if pd.notna(last.get("MACD")) and pd.notna(last.get("MACD_Signal")):
        if last["MACD"] > last["MACD_Signal"]:
            votes["MACD"] = "BUY"
            buy_votes += 1
        elif last["MACD"] < last["MACD_Signal"]:
            votes["MACD"] = "SELL"
            sell_votes += 1
        else:
            votes["MACD"] = "NEUTRAL"
    else:
        votes["MACD"] = "N/A"

    if pd.notna(last.get("BB_Lower")) and pd.notna(last.get("BB_Upper")):
        if last["Close"] <= last["BB_Lower"]:
            votes["Bollinger Bands"] = "BUY"
            buy_votes += 1
        elif last["Close"] >= last["BB_Upper"]:
            votes["Bollinger Bands"] = "SELL"
            sell_votes += 1
        else:
            votes["Bollinger Bands"] = "NEUTRAL"
    else:
        votes["Bollinger Bands"] = "N/A"

    total_active = sum(1 for v in votes.values() if v != "N/A")
    if total_active == 0:
        return {"signal": "HOLD", "confidence": 0.0, "agreement": "0/4", "votes": votes}

    if buy_votes > sell_votes:
        signal = "BUY"
        confidence = 100 * buy_votes / total_active
        agreement = f"{buy_votes}/{total_active}"
    elif sell_votes > buy_votes:
        signal = "SELL"
        confidence = 100 * sell_votes / total_active
        agreement = f"{sell_votes}/{total_active}"
    else:
        signal = "HOLD"
        confidence = 100 * max(buy_votes, sell_votes) / total_active if total_active else 0.0
        agreement = f"{max(buy_votes, sell_votes)}/{total_active}"

    return {"signal": signal, "confidence": round(confidence, 1), "agreement": agreement, "votes": votes}


# --------------------------------------------------------------------------
# Simplified backtesting engine
# --------------------------------------------------------------------------

def _positions_from_rule(d: pd.DataFrame, strategy: str) -> pd.Series:
    """Return a 0/1 long-flat position series (shifted by 1 bar to avoid look-ahead)."""
    if strategy == "SMA":
        raw = (d["SMA20"] > d["SMA50"]).astype(int)
    elif strategy == "RSI":
        # Long while RSI below 50 after having dipped under 30 is more elaborate;
        # keep it simple & transparent: long when RSI < 50 (momentum recovering from oversold),
        # flat when RSI > 70 (overbought).
        pos = pd.Series(np.nan, index=d.index)
        pos[d["RSI14"] < 30] = 1
        pos[d["RSI14"] > 70] = 0
        raw = pos.ffill().fillna(0).astype(int)
    elif strategy == "MACD":
        raw = (d["MACD"] > d["MACD_Signal"]).astype(int)
    elif strategy == "Bollinger Bands":
        pos = pd.Series(np.nan, index=d.index)
        pos[d["Close"] <= d["BB_Lower"]] = 1
        pos[d["Close"] >= d["BB_Upper"]] = 0
        raw = pos.ffill().fillna(0).astype(int)
    elif strategy == "Combined":
        votes = pd.DataFrame(
            {
                "SMA": (d["SMA20"] > d["SMA50"]).astype(int),
                "MACD": (d["MACD"] > d["MACD_Signal"]).astype(int),
            }
        )
        rsi_pos = pd.Series(np.nan, index=d.index)
        rsi_pos[d["RSI14"] < 30] = 1
        rsi_pos[d["RSI14"] > 70] = 0
        votes["RSI"] = rsi_pos.ffill().fillna(0).astype(int)

        bb_pos = pd.Series(np.nan, index=d.index)
        bb_pos[d["Close"] <= d["BB_Lower"]] = 1
        bb_pos[d["Close"] >= d["BB_Upper"]] = 0
        votes["BB"] = bb_pos.ffill().fillna(0).astype(int)

        raw = (votes.mean(axis=1) >= 0.5).astype(int)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return raw.shift(1).fillna(0).astype(int)  # act on *next* bar's return


def backtest_strategy(df: pd.DataFrame, strategy: str, cost: float = TRANSACTION_COST) -> dict:
    """
    Simplified long/flat backtest for a single (asset, strategy) pair.

    Execution model: position decided at bar close is applied to the
    *following* bar's return (no look-ahead), a flat proportional
    transaction cost is charged whenever the position changes.

    Returns a dict of metrics plus the equity curve (pd.Series) and
    Buy & Hold equity curve for comparison.
    """
    d = add_all_indicators(df)
    d = d.dropna(subset=["Close"])
    if len(d) < 60:
        return _empty_backtest_result()

    position = _positions_from_rule(d, strategy)
    asset_returns = d["Close"].pct_change().fillna(0)

    strat_returns = position * asset_returns
    trades = position.diff().abs().fillna(0)
    strat_returns = strat_returns - trades * cost

    equity = (1 + strat_returns).cumprod()
    bh_equity = (1 + asset_returns).cumprod()

    total_return = (equity.iloc[-1] - 1) * 100 if len(equity) else np.nan
    ann_vol = strat_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
    mean_ann_return = strat_returns.mean() * TRADING_DAYS_PER_YEAR
    sharpe = (
        (mean_ann_return - RISK_FREE_RATE) / (strat_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        if strat_returns.std() > 0
        else np.nan
    )

    running_max = equity.cummax()
    drawdown = (equity / running_max - 1) * 100
    max_dd = drawdown.min()

    trade_entries = trades[trades > 0]
    num_trades = int(trade_entries.sum())
    winning_days = (strat_returns > 0).sum()
    active_days = (position != 0).sum()
    win_rate = (winning_days / active_days * 100) if active_days > 0 else 0.0

    gains = strat_returns[strat_returns > 0].sum()
    losses = -strat_returns[strat_returns < 0].sum()
    profit_factor = (gains / losses) if losses > 0 else np.nan
    avg_trade_return = (strat_returns[position != 0].mean() * 100) if active_days > 0 else 0.0

    return {
        "total_return": total_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "annual_volatility": ann_vol,
        "num_trades": num_trades,
        "avg_trade_return": avg_trade_return,
        "profit_factor": profit_factor,
        "final_value": equity.iloc[-1] * 100,  # per $100 invested
        "equity_curve": equity,
        "buy_hold_curve": bh_equity,
        "drawdown_curve": drawdown,
        "daily_returns": strat_returns,
    }


def _empty_backtest_result() -> dict:
    empty = pd.Series(dtype=float)
    return {
        "total_return": np.nan, "sharpe_ratio": np.nan, "max_drawdown": np.nan,
        "win_rate": np.nan, "annual_volatility": np.nan, "num_trades": 0,
        "avg_trade_return": np.nan, "profit_factor": np.nan, "final_value": np.nan,
        "equity_curve": empty, "buy_hold_curve": empty, "drawdown_curve": empty,
        "daily_returns": empty,
    }


def run_full_backtest(asset_data: dict[str, pd.DataFrame], strategies: list[str]) -> tuple[pd.DataFrame, dict]:
    """
    Run every (asset, strategy) combination.

    `asset_data` maps display ticker -> OHLCV DataFrame (already fetched).
    Returns:
        results_df: one row per (Asset, Strategy) with performance metrics
        equity_curves: nested dict {asset: {strategy: equity_series}} incl. "Buy & Hold"
    """
    rows = []
    equity_curves: dict[str, dict[str, pd.Series]] = {}

    for asset, df in asset_data.items():
        if df.empty:
            continue
        equity_curves[asset] = {}
        for strat in strategies:
            res = backtest_strategy(df, strat)
            rows.append(
                {
                    "Asset": asset,
                    "Strategy": strat,
                    "Total Return (%)": res["total_return"],
                    "Sharpe Ratio": res["sharpe_ratio"],
                    "Maximum Drawdown (%)": res["max_drawdown"],
                    "Win Rate (%)": res["win_rate"],
                    "Annual Volatility (%)": res["annual_volatility"],
                    "Number of Trades": res["num_trades"],
                    "Avg Trade Return (%)": res["avg_trade_return"],
                    "Profit Factor": res["profit_factor"],
                    "Final Value ($100 invested)": res["final_value"],
                }
            )
            equity_curves[asset][strat] = res["equity_curve"]
        if equity_curves[asset]:
            any_strat = next(iter(equity_curves[asset]))
            # buy & hold curve is identical regardless of strategy chosen
            equity_curves[asset]["Buy & Hold"] = backtest_strategy(df, strategies[0])["buy_hold_curve"]

    results_df = pd.DataFrame(rows)
    return results_df, equity_curves


def rank_strategies(results_df: pd.DataFrame, metric: str, ascending: bool = False) -> pd.DataFrame:
    """Rank all (Asset, Strategy) rows by a chosen metric and attach medal emojis to the top 3."""
    if results_df.empty or metric not in results_df.columns:
        return results_df
    ranked = results_df.sort_values(metric, ascending=ascending).reset_index(drop=True)
    medals = ["🥇", "🥈", "🥉"]
    ranked["Rank"] = [medals[i] if i < 3 else str(i + 1) for i in range(len(ranked))]
    cols = ["Rank"] + [c for c in ranked.columns if c != "Rank"]
    return ranked[cols]
