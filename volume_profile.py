"""
Объёмный профиль (Volume Profile) и premium/discount зоны — концепции из
Smart Money Concepts. Идея: POC (Point of Control) — цена с максимальным
объёмом торгов за период, VAH/VAL (Value Area High/Low) — границы зоны,
где прошло ~70% объёма. Premium/discount — где текущая цена находится
относительно недавнего диапазона (верхняя половина = "дорого" для LONG,
нижняя = "дёшево").

Это структурный контекст, а не отдельный сигнал на покупку/продажу —
используется как небольшая поправка и как информация в алерте.
"""
import numpy as np
import pandas as pd


def compute_volume_profile(df: pd.DataFrame, bins: int = 20, value_area_pct: float = 0.7) -> dict | None:
    """Считает POC/VAH/VAL по последним свечам."""
    if len(df) < 20:
        return None

    price_min = df["low"].min()
    price_max = df["high"].max()
    if price_max <= price_min:
        return None

    bin_edges = np.linspace(price_min, price_max, bins + 1)
    vol_per_bin = np.zeros(bins)

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    bin_idx = np.clip(np.digitize(typical_price, bin_edges) - 1, 0, bins - 1)
    for idx, vol in zip(bin_idx, df["volume"]):
        vol_per_bin[idx] += vol

    total_vol = vol_per_bin.sum()
    if total_vol == 0:
        return None

    poc_bin = int(np.argmax(vol_per_bin))
    poc_price = (bin_edges[poc_bin] + bin_edges[poc_bin + 1]) / 2

    # Расширяем область вокруг POC, пока не наберём value_area_pct объёма
    order = np.argsort(vol_per_bin)[::-1]
    cum_vol = 0.0
    included_bins = []
    for idx in order:
        included_bins.append(idx)
        cum_vol += vol_per_bin[idx]
        if cum_vol >= total_vol * value_area_pct:
            break

    val_bin = min(included_bins)
    vah_bin = max(included_bins)
    val_price = bin_edges[val_bin]
    vah_price = bin_edges[vah_bin + 1]

    return {"poc": poc_price, "vah": vah_price, "val": val_price}


def premium_discount_zone(df: pd.DataFrame, lookback: int = 100) -> tuple[str, float]:
    """
    Возвращает (зона, процент_положения_в_диапазоне).
    "discount" — цена в нижней половине недавнего диапазона (обычно выгоднее для LONG)
    "premium" — в верхней половине (обычно выгоднее для SHORT)
    "equilibrium" — около середины
    """
    recent = df.iloc[-lookback:] if len(df) > lookback else df
    high = recent["high"].max()
    low = recent["low"].min()
    price = df["close"].iloc[-1]

    if high <= low:
        return "equilibrium", 50.0

    pct = (price - low) / (high - low) * 100

    if pct >= 65:
        return "premium", pct
    elif pct <= 35:
        return "discount", pct
    else:
        return "equilibrium", pct


def volume_anomaly(df: pd.DataFrame, window: int = 20, z_threshold: float = 2.5) -> tuple[bool, float]:
    """
    Детектор аномального объёма (та же идея, что у MRX Signal, но на ликвидных
    парах): z-score текущего объёма относительно скользящего среднего/std.
    Аномалия сама по себе не говорит о направлении — только о том, что
    происходит что-то нестандартное, и стоит быть внимательнее.
    """
    if len(df) < window + 1:
        return False, 0.0
    vol = df["volume"]
    baseline = vol.iloc[-window - 1:-1]
    mean = baseline.mean()
    std = baseline.std()
    if std == 0 or pd.isna(std):
        return False, 0.0
    current = vol.iloc[-1]
    z = (current - mean) / std
    return z >= z_threshold, float(z)
