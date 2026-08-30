from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "technical.json"

QQQ = "QQQ"
VIX = "^VIX"


def safe_float(x):
    if x is None:
        return None
    try:
        v = float(x)
        return None if math.isnan(v) or math.isinf(v) else round(v, 4)
    except Exception:
        return None


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(100)


def get_close_frame(tickers, period="2y"):
    data = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
        multi_level_index=True,
        timeout=30,
    )
    if data is None or data.empty:
        raise RuntimeError(f"No price data returned for {tickers}")

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            close = data["Close"].copy()
        else:
            raise RuntimeError("Close field not found in downloaded data.")
    else:
        close = data[["Close"]].copy()
        if isinstance(tickers, str):
            close.columns = [tickers]
    return close.dropna(how="all")


def score_rsi(v):
    if v > 80: return 6
    if v >= 70: return 10
    if v >= 60: return 15
    if v >= 50: return 13
    if v >= 40: return 8
    if v >= 30: return 4
    return 7


def score_momentum_pct(v, strong=5):
    if v is None: return 0
    if v >= 5: return strong
    if v >= 0: return max(1, strong-1)
    if v >= -5: return 2
    return 0


def score_d20(v):
    if v is None: return 0
    if -2 <= v <= 0: return 10
    if 0 < v <= 3: return 8
    if -5 <= v < -2: return 8
    if 3 < v <= 6: return 6
    if -8 <= v < -5: return 5
    if v < -10: return 4
    if v > 8: return 2
    return 3


def score_d60(v):
    if v is None: return 0
    a = abs(v)
    if a <= 2: return 5
    if a <= 5: return 4
    if a <= 8: return 3
    if a <= 12: return 2
    return 1


def score_vix(v):
    if v is None: return 5
    if v < 13: return 5
    if v < 16: return 8
    if v < 20: return 10
    if v < 25: return 7
    if v < 30: return 5
    if v < 40: return 3
    return 5


def breadth_score(b50, b200):
    vals = [x for x in [b50, b200] if x is not None]
    if not vals:
        return 5
    b = sum(vals)/len(vals)
    if b >= 80: return 10
    if b >= 65: return 9
    if b >= 50: return 7
    if b >= 35: return 5
    if b >= 20: return 3
    return 4


def score_state(score):
    if score >= 85: return "STRONG BULL"
    if score >= 70: return "BULLISH"
    if score >= 60: return "BULL PULLBACK"
    if score >= 45: return "TRANSITION"
    if score >= 30: return "TREND BREAKDOWN"
    if score >= 15: return "BEARISH"
    return "EXTREME OVERSOLD"


def rsi_state(v):
    if v >= 80: return "Overheated"
    if v >= 70: return "Strong"
    if v >= 60: return "Healthy"
    if v >= 50: return "Neutral+"
    if v >= 40: return "Weakening"
    if v >= 30: return "Weak"
    return "Oversold"


def fetch_nasdaq100_tickers():
    # Primary: Wikipedia's current Nasdaq-100 components table.
    # If this changes or becomes unavailable, breadth will be marked unavailable
    # rather than causing the entire dashboard to fail.
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    try:
        tables = pd.read_html(url)
        candidates = []
        for table in tables:
            cols = [str(c) for c in table.columns]
            if "Ticker" in cols or "Ticker symbol" in cols:
                candidates.append(table)
        if not candidates:
            return []
        table = candidates[0]
        col = "Ticker" if "Ticker" in table.columns else "Ticker symbol"
        vals = table[col].astype(str).str.strip().str.replace(".", "-", regex=False).tolist()
        return sorted(set(x for x in vals if x and x != "nan"))
    except Exception as e:
        print("Breadth ticker fetch failed:", e)
        return []


def calc_breadth():
    tickers = fetch_nasdaq100_tickers()
    if len(tickers) < 50:
        return None, None, 0, "Breadth unavailable: constituent list could not be loaded."

    try:
        close = get_close_frame(tickers, period="2y")
        close = close.dropna(axis=1, how="all")
        latest = close.ffill().iloc[-1]
        ma50 = close.rolling(50, min_periods=50).mean().ffill().iloc[-1]
        ma200 = close.rolling(200, min_periods=200).mean().ffill().iloc[-1]

        valid50 = latest.index[latest.notna() & ma50.notna()]
        valid200 = latest.index[latest.notna() & ma200.notna()]

        b50 = (latest[valid50] > ma50[valid50]).mean() * 100 if len(valid50) else None
        b200 = (latest[valid200] > ma200[valid200]).mean() * 100 if len(valid200) else None
        count = int(max(len(valid50), len(valid200)))
        note = f"Calculated from {count} currently downloadable Nasdaq-100 constituents."
        return safe_float(b50), safe_float(b200), count, note
    except Exception as e:
        print("Breadth download failed:", e)
        return None, None, 0, "Breadth unavailable on this run; neutral breadth score applied."


def main():
    close = get_close_frame([QQQ, VIX], period="3y")
    if QQQ not in close.columns:
        raise RuntimeError("QQQ price data missing.")

    q = pd.DataFrame({"close": close[QQQ].dropna()})
    q["ma20"] = q["close"].rolling(20).mean()
    q["ma60"] = q["close"].rolling(60).mean()
    q["ma120"] = q["close"].rolling(120).mean()
    q["ma200"] = q["close"].rolling(200).mean()
    q["rsi14"] = rsi(q["close"])
    q["mom20"] = q["close"].pct_change(20) * 100
    q["mom60"] = q["close"].pct_change(60) * 100
    q["d20"] = (q["close"] / q["ma20"] - 1) * 100
    q["d60"] = (q["close"] / q["ma60"] - 1) * 100
    q["d120"] = (q["close"] / q["ma120"] - 1) * 100
    q["d200"] = (q["close"] / q["ma200"] - 1) * 100
    q = q.dropna().copy()

    cur = q.iloc[-1]
    prev = q.iloc[-2]
    vix_series = close[VIX].dropna() if VIX in close.columns else pd.Series(dtype=float)
    vix = safe_float(vix_series.iloc[-1]) if not vix_series.empty else None

    ma200_slope_20 = safe_float((cur["ma200"] / q["ma200"].iloc[-21] - 1) * 100) if len(q) >= 21 else 0
    ma20_slope_5 = safe_float((cur["ma20"] / q["ma20"].iloc[-6] - 1) * 100) if len(q) >= 6 else 0
    daily_change = safe_float((cur["close"] / prev["close"] - 1) * 100)

    trend = 0
    trend += 5 if cur["close"] > cur["ma20"] else 0
    trend += 8 if cur["close"] > cur["ma60"] else 0
    trend += 7 if cur["close"] > cur["ma120"] else 0
    trend += 10 if cur["close"] > cur["ma200"] else 0
    trend += 4 if cur["ma20"] > cur["ma60"] else 0
    trend += 3 if cur["ma60"] > cur["ma120"] else 0
    trend += 3 if cur["ma120"] > cur["ma200"] else 0

    momentum = score_rsi(cur["rsi14"]) + score_momentum_pct(cur["mom20"], 5) + score_momentum_pct(cur["mom60"], 5)
    deviation = score_d20(cur["d20"]) + score_d60(cur["d60"])
    volatility = score_vix(vix)

    b50, b200, breadth_count, breadth_note = calc_breadth()
    breadth = breadth_score(b50, b200)

    total = int(round(trend + momentum + deviation + volatility + breadth))
    total = max(0, min(100, total))

    # Rule engine
    bullish_regime = cur["close"] > cur["ma200"] and ma200_slope_20 > 0
    bear_regime = cur["close"] < cur["ma200"] and ma200_slope_20 < 0

    last5 = q.tail(5)
    five_below20 = bool((last5["close"] < last5["ma20"]).all())
    five_below60 = bool((last5["close"] < last5["ma60"]).all())

    reclaim20 = bool(cur["close"] > cur["ma20"] and prev["close"] <= prev["ma20"] and bullish_regime)
    reclaim60 = bool(cur["close"] > cur["ma60"] and prev["close"] <= prev["ma60"] and bullish_regime)
    major_reclaim = bool(cur["close"] > cur["ma200"] and prev["close"] <= prev["ma200"] and cur["ma20"] > cur["ma60"])

    if bear_regime:
        regime = "BEAR MARKET"
        action = "DEFENSIVE"
        message = "价格位于 MA200 下方且 MA200 下降：优先控制风险，等待趋势恢复。"
    elif major_reclaim:
        regime = "RECOVERY"
        action = "MAJOR BUY WATCH"
        message = "QQQ 刚重新站上 MA200，且 MA20 > MA60：进入主要趋势恢复观察区。"
    elif five_below60 and cur["ma20"] < cur["ma60"]:
        regime = "TREND BREAKDOWN"
        action = "REDUCE"
        message = "连续 5 日低于 MA60 且 MA20 < MA60：中期趋势破坏信号。"
    elif reclaim60:
        regime = "BULL PULLBACK"
        action = "BUY 2"
        message = "牛市结构中重新站回 MA60：中期回调买点信号。"
    elif reclaim20:
        regime = "BULL PULLBACK"
        action = "BUY 1"
        message = "牛市结构中重新站回 MA20：短期回调买点信号。"
    elif five_below20 and ma20_slope_5 < 0:
        regime = "WARNING"
        action = "WAIT"
        message = "连续 5 日低于 MA20 且 MA20 下行：暂停新增仓位，观察 MA60。"
    elif bullish_regime:
        regime = "BULL MARKET"
        action = "HOLD / BUY PULLBACK"
        message = "QQQ 位于上升的 MA200 上方：长期多头结构仍有效，优先等待回调买点。"
    else:
        regime = "TRANSITION"
        action = "WAIT"
        message = "长期趋势未形成明确多头或空头结构：等待确认。"

    # Score trend is deliberately simple and transparent.
    # It uses price/MA structure from 5 sessions ago as a direction proxy.
    structural_now = sum([
        cur["close"] > cur["ma20"],
        cur["close"] > cur["ma60"],
        cur["close"] > cur["ma120"],
        cur["close"] > cur["ma200"],
        cur["ma20"] > cur["ma60"],
    ])
    old = q.iloc[-6]
    structural_old = sum([
        old["close"] > old["ma20"],
        old["close"] > old["ma60"],
        old["close"] > old["ma120"],
        old["close"] > old["ma200"],
        old["ma20"] > old["ma60"],
    ])
    if structural_now > structural_old:
        score_trend = "↑ IMPROVING"
    elif structural_now < structural_old:
        score_trend = "↓ WEAKENING"
    else:
        score_trend = "→ STABLE"

    checklist = [
        {
            "title": "Price > MA200",
            "detail": f"${cur['close']:.2f} vs ${cur['ma200']:.2f}",
            "status": "ok" if cur["close"] > cur["ma200"] else "bad",
        },
        {
            "title": "MA200 slope",
            "detail": f"20-session slope {ma200_slope_20:+.2f}%",
            "status": "ok" if ma200_slope_20 > 0 else "bad",
        },
        {
            "title": "MA20 > MA60",
            "detail": f"${cur['ma20']:.2f} vs ${cur['ma60']:.2f}",
            "status": "ok" if cur["ma20"] > cur["ma60"] else "warn",
        },
        {
            "title": "MA60 > MA120",
            "detail": f"${cur['ma60']:.2f} vs ${cur['ma120']:.2f}",
            "status": "ok" if cur["ma60"] > cur["ma120"] else "warn",
        },
        {
            "title": "MA120 > MA200",
            "detail": f"${cur['ma120']:.2f} vs ${cur['ma200']:.2f}",
            "status": "ok" if cur["ma120"] > cur["ma200"] else "warn",
        },
        {
            "title": "RSI",
            "detail": f"RSI(14) = {cur['rsi14']:.1f} · {rsi_state(cur['rsi14'])}",
            "status": "ok" if 50 <= cur["rsi14"] <= 70 else "warn",
        },
        {
            "title": "Breadth > MA200",
            "detail": "Unavailable" if b200 is None else f"{b200:.1f}% of constituents",
            "status": "ok" if (b200 is not None and b200 >= 50) else "warn",
        },
    ]

    chart_rows = []
    for idx, row in q.tail(260).iterrows():
        chart_rows.append({
            "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
            "close": safe_float(row["close"]),
            "ma20": safe_float(row["ma20"]),
            "ma60": safe_float(row["ma60"]),
            "ma120": safe_float(row["ma120"]),
            "ma200": safe_float(row["ma200"]),
        })

    payload = {
        "meta": {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "price_date": pd.Timestamp(q.index[-1]).strftime("%Y-%m-%d"),
            "symbol": "QQQ",
            "method": "NASDAQ Trend System V2",
        },
        "market": {
            "close": safe_float(cur["close"]),
            "daily_change_pct": daily_change,
            "vix": vix,
            "ma20": safe_float(cur["ma20"]),
            "ma60": safe_float(cur["ma60"]),
            "ma120": safe_float(cur["ma120"]),
            "ma200": safe_float(cur["ma200"]),
            "d20": safe_float(cur["d20"]),
            "d60": safe_float(cur["d60"]),
            "d120": safe_float(cur["d120"]),
            "d200": safe_float(cur["d200"]),
            "rsi14": safe_float(cur["rsi14"]),
            "rsi_state": rsi_state(cur["rsi14"]),
            "mom20_pct": safe_float(cur["mom20"]),
            "mom60_pct": safe_float(cur["mom60"]),
            "ma200_slope20_pct": ma200_slope_20,
        },
        "score": {
            "total": total,
            "state": score_state(total),
            "trend": score_trend,
            "components": {
                "trend": trend,
                "momentum": momentum,
                "deviation": deviation,
                "volatility": volatility,
                "breadth": breadth,
            },
        },
        "signal": {
            "regime": regime,
            "action": action,
            "message": message,
            "reclaim_ma20": reclaim20,
            "reclaim_ma60": reclaim60,
            "major_reclaim_ma200": major_reclaim,
        },
        "breadth": {
            "ma50_pct": b50,
            "ma200_pct": b200,
            "constituents_used": breadth_count,
            "note": breadth_note,
        },
        "checklist": checklist,
        "chart": chart_rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Score={total}, State={score_state(total)}, Action={action}")


if __name__ == "__main__":
    main()
