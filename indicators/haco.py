from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


def ema(series: List[float], length: int) -> List[float]:
    if not series:
        return []
    k = 2 / (length + 1)
    result = [series[0]]
    for price in series[1:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def tema(series: List[float], length: int) -> List[float]:
    """Triple EMA."""
    if not series:
        return []
    e1 = ema(series, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    return [3 * a - 3 * b + c for a, b, c in zip(e1, e2, e3)]


def zero_lag_from_tema(tema1: List[float], tema2: List[float]) -> List[float]:
    return [a + (a - b) for a, b in zip(tema1, tema2)]


def _alert(cond: List[bool], idx: int, lookback: int) -> bool:
    start = max(0, idx - lookback)
    for j in range(start, idx + 1):
        if cond[j]:
            return True
    return False


def compute_haco(
    candles: List[Dict[str, float]],
    length_up: int = 34,
    length_down: int = 34,
    alert_lookback: int = 1,
) -> Dict[str, List[Dict[str, float]]]:
    n = len(candles)
    if n == 0:
        return {"series": [], "last": {}}

    o = [c["o"] for c in candles]
    h = [c["h"] for c in candles]
    l = [c["l"] for c in candles]
    c = [c["c"] for c in candles]
    t = [c.get("time") for c in candles]

    ha_close_raw = [(o[i] + h[i] + l[i] + c[i]) / 4 for i in range(n)]
    ha_open = [0.0] * n
    ha_open[0] = (o[0] + c[0]) / 2
    for i in range(1, n):
        ha_open[i] = (ha_open[i - 1] + ha_close_raw[i - 1]) / 2
    ha_c = [
        (ha_close_raw[i] + ha_open[i] + max(h[i], ha_open[i]) + min(l[i], ha_open[i])) / 4
        for i in range(n)
    ]
    mid = [(h[i] + l[i]) / 2 for i in range(n)]

    # Up pass zero lag lines
    tma1_u = tema(ha_c, length_up)
    tma2_u = tema(tma1_u, length_up)
    zl_ha_u = zero_lag_from_tema(tma1_u, tma2_u)

    tma1c_u = tema(mid, length_up)
    tma2c_u = tema(tma1c_u, length_up)
    zl_cl_u = zero_lag_from_tema(tma1c_u, tma2c_u)
    zl_dif_u = [a - b for a, b in zip(zl_cl_u, zl_ha_u)]

    # Down pass zero lag lines
    tma1_d = tema(ha_c, length_down)
    tma2_d = tema(tma1_d, length_down)
    zl_ha_d = zero_lag_from_tema(tma1_d, tma2_d)

    tma1c_d = tema(mid, length_down)
    tma2c_d = tema(tma1c_d, length_down)
    zl_cl_d = zero_lag_from_tema(tma1c_d, tma2c_d)
    zl_dif_d = [a - b for a, b in zip(zl_cl_d, zl_ha_d)]

    keep1u_alert_raw = [ha_c[i] >= ha_open[i] for i in range(n)]
    keep1d_raw = [ha_c[i] < ha_open[i] for i in range(n)]

    state = [0] * n
    state[0] = 1 if c[0] >= o[0] else 0
    reasons = [""] * n

    keep1u_alert = [False] * n
    keep1u_price = [False] * n
    keep2u = [False] * n
    keepingu = [False] * n
    keepallu = [False] * n
    keep3u = [False] * n
    utr = [False] * n

    keep1d = [False] * n
    keep2d = [False] * n
    keepingd = [False] * n
    keepalld = [False] * n
    keep3d = [False] * n
    dtr = [False] * n

    upw = [False] * n
    dnw = [False] * n

    for i in range(n):
        prev = i - 1
        prev_h = h[prev] if prev >= 0 else h[0]
        prev_l = l[prev] if prev >= 0 else l[0]
        prev_c = c[prev] if prev >= 0 else c[0]
        prev_o = o[prev] if prev >= 0 else o[0]

        keep1u_alert[i] = _alert(keep1u_alert_raw, i, alert_lookback)
        keep1u_price[i] = (
            c[i] >= ha_c[i]
            or h[i] > prev_h
            or l[i] > prev_l
        )
        keep2u[i] = zl_dif_u[i] >= 0 if i < len(zl_dif_u) else False
        keepingu[i] = keep1u_alert[i] or keep1u_price[i] or keep2u[i]
        prev_keepingu = keepingu[prev] if prev >= 0 else keepingu[0]
        keepallu[i] = (
            keepingu[i]
            or (prev_keepingu and (c[i] >= o[i]))
            or (c[i] >= prev_c)
        )
        keep3u[i] = False
        if h[i] != l[i]:
            keep3u[i] = abs(c[i] - o[i]) < (h[i] - l[i]) * 0.35 and h[i] >= prev_l
        prev_keepallu = keepallu[prev] if prev >= 0 else keepallu[0]
        utr[i] = keepallu[i] or (prev_keepallu and keep3u[i])

        keep1d[i] = _alert(keep1d_raw, i, alert_lookback)
        keep2d[i] = zl_dif_d[i] < 0 if i < len(zl_dif_d) else False
        keep3d[i] = False
        if h[i] != l[i]:
            keep3d[i] = abs(c[i] - o[i]) < (h[i] - l[i]) * 0.35 and l[i] <= prev_h
        keepingd[i] = keep1d[i] or keep2d[i]
        prev_keepingd = keepingd[prev] if prev >= 0 else keepingd[0]
        keepalld[i] = (
            keepingd[i]
            or (prev_keepingd and (c[i] < o[i]))
            or (c[i] < prev_c)
        )
        prev_keepalld = keepalld[prev] if prev >= 0 else keepalld[0]
        dtr[i] = keepalld[i] or (prev_keepalld and keep3d[i])

        prev_dtr = dtr[prev] if prev >= 0 else dtr[0]
        prev_utr = utr[prev] if prev >= 0 else utr[0]

        upw[i] = (not dtr[i]) and prev_dtr and utr[i]
        dnw[i] = (not utr[i]) and prev_utr and dtr[i]

        if upw[i]:
            state[i] = 1
        elif dnw[i]:
            state[i] = 0
        else:
            state[i] = state[prev] if prev >= 0 else state[0]

        reason_i = []
        if upw[i]:
            reason_i.append("upw")
        if dnw[i]:
            reason_i.append("dnw")
        if keepingu[i]:
            reason_i.append("keepingU")
        if keepingd[i]:
            reason_i.append("keepingD")
        if utr[i]:
            reason_i.append("utr")
        if dtr[i]:
            reason_i.append("dtr")
        keep1_alert = keep1u_alert[i]
        keep1_price = keep1u_price[i]
        keep1_trend = keep2u[i]
        reason_i.append(
            f"keep1={keep1_alert}/{keep1_price}/{keep1_trend} "
            f"ZlDifU={zl_dif_u[i]:.2f} ZlDifD={zl_dif_d[i]:.2f}"
        )
        reasons[i] = ", ".join(reason_i)

    series = []
    for i in range(n):
        series.append({
            "time": t[i],
            "o": o[i],
            "h": h[i],
            "l": l[i],
            "c": c[i],
            "haOpen": ha_open[i],
            "haC": ha_c[i],
            "mid": mid[i],
            "TMA1U": tma1_u[i],
            "TMA2U": tma2_u[i],
            "ZlHaU": zl_ha_u[i],
            "TMA1CU": tma1c_u[i],
            "TMA2CU": tma2c_u[i],
            "ZlClU": zl_cl_u[i],
            "ZlDifU": zl_dif_u[i],
            "TMA1D": tma1_d[i],
            "TMA2D": tma2_d[i],
            "ZlHaD": zl_ha_d[i],
            "TMA1CD": tma1c_d[i],
            "TMA2CD": tma2c_d[i],
            "ZlClD": zl_cl_d[i],
            "ZlDifD": zl_dif_d[i],
            "keep1U_alert": keep1u_alert[i],
            "keep1U_price": keep1u_price[i],
            "keep2U": keep2u[i],
            "keepingU": keepingu[i],
            "keepallU": keepallu[i],
            "keep3U": keep3u[i],
            "utr": utr[i],
            "keep1D": keep1d[i],
            "keep2D": keep2d[i],
            "keepingD": keepingd[i],
            "keepallD": keepalld[i],
            "keep3D": keep3d[i],
            "dtr": dtr[i],
            "upw": upw[i],
            "dnw": dnw[i],
            "state": state[i],
            "reason": reasons[i],
        })

    last = {
        "upw": upw[-1],
        "dnw": dnw[-1],
        "state": state[-1],
        "changed": state[-1] != state[-2] if n > 1 else False,
        "reasons": reasons[-1],
    }

    return {"series": series[-n:], "last": last}
