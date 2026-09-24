"""Original Hermes ETF scoring model, isolated from the OpenD transport."""
import math
import numpy as np
import pandas as pd

UNIVERSE = {
    "Broad": "SPY QQQ DIA IWM MDY RSP VTI",
    "Sector": "XLK XLC XLY XLI XLF XLE XLB XLP XLV XLRE XLU",
    "Industry": "SMH SOXX IGV CIBR SKYY BOTZ ROBO ARKK IBB XBI KRE KBE ITA PPA XRT IYT JETS",
    "RealAsset": "GLD SLV GDX GDXJ COPX URA TAN ICLN DBC DBA USO UNG",
    "Factor": "MTUM QUAL USMV VLUE VUG VTV IWF IWD",
    "Bond": "TLT IEF SHY HYG LQD TIP",
    "International": "EFA EEM EWJ EWY EWT INDA MCHI FXI VGK EWZ",
}


def atr14(frame: pd.DataFrame) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - prev).abs(), (frame["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(14).mean()


def metrics(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    spy = frames["SPY"]
    spy_r = {n: spy["close"].iloc[-1] / spy["close"].iloc[-1 - n] - 1 for n in (20, 60, 120)}
    rows = []
    group_lookup = {
        ticker: group for group, tickers in UNIVERSE.items() for ticker in tickers.split()
    }
    for ticker, frame in frames.items():
        close = frame["close"].astype(float)
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        volume = frame["volume"].astype(float)
        atr = float(atr14(frame).iloc[-1])
        last = float(close.iloc[-1])
        r = {n: last / float(close.iloc[-1 - n]) - 1 for n in (20, 60, 120)}
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        sma120 = float(close.rolling(120).mean().iloc[-1])
        high20_prev = float(high.iloc[-21:-1].max())
        high120 = float(high.iloc[-120:].max())
        low10 = float(low.iloc[-10:].min())
        vol20 = float(close.pct_change().iloc[-20:].std() * math.sqrt(252))
        adtv20 = float((close * volume).iloc[-20:].mean())
        dist_ema_atr = (last - ema20) / atr if atr else np.nan
        stop = min(ema20, low10) - 0.5 * atr
        rows.append(
            {
                "ticker": ticker,
                "group": group_lookup[ticker],
                "date": frame["time_key"].iloc[-1].date().isoformat(),
                "close": last,
                "r20": r[20],
                "r60": r[60],
                "r120": r[120],
                "rs20": r[20] - spy_r[20],
                "rs60": r[60] - spy_r[60],
                "rs120": r[120] - spy_r[120],
                "ema20": ema20,
                "sma50": sma50,
                "sma120": sma120,
                "atr14": atr,
                "atr_pct": atr / last,
                "vol20_ann": vol20,
                "dist_ema_atr": dist_ema_atr,
                "from_high120": last / high120 - 1,
                "high20_prev": high20_prev,
                "breakout_trigger": high20_prev + 0.1 * atr,
                "pullback_low": ema20 - 0.5 * atr,
                "pullback_high": ema20 + 0.5 * atr,
                "stop_ref": stop,
                "stop_pct": stop / last - 1,
                "adtv20": adtv20,
                "trend_aligned": last > ema20 > sma50 > sma120,
            }
        )
    result = pd.DataFrame(rows)
    for n, weight in ((20, 0.30), (60, 0.40), (120, 0.30)):
        result[f"rank{n}"] = result[f"r{n}"].rank(pct=True)
        result[f"w{n}"] = weight * result[f"rank{n}"]
    result["score"] = 100 * (result["w20"] + result["w60"] + result["w120"])
    result["score"] += np.where(result["trend_aligned"], 5, 0)
    result["score"] += np.where(result["rs60"] > 0, 3, 0)
    result["score"] -= np.where(result["dist_ema_atr"] > 2.5, 8, 0)
    result["setup"] = "Avoid / broken"
    strong = (
        (result[["r20", "r60", "r120"]] > 0).all(axis=1)
        & result["trend_aligned"]
        & (result["rs60"] > 0)
    )
    result.loc[strong & (result["dist_ema_atr"] <= 2.5), "setup"] = "Momentum"
    result.loc[strong & (result["dist_ema_atr"] > 2.5), "setup"] = "Strong / wait pullback"
    pullback = (
        (result["r60"] > 0)
        & (result["r120"] > 0)
        & (result["close"] > result["sma50"])
        & ~strong
    )
    result.loc[pullback, "setup"] = "Pullback watch"
    return result.sort_values("score", ascending=False).reset_index(drop=True)



