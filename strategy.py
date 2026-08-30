"""
Логика генерации сигналов, версия 3.

ВАЖНО (честно): это скоринговая эвристика, а НЕ система с доказанной
статистической точностью 90%+. Скор 0-100 — внутренняя мера согласованности
сигналов, а не вероятность. Реальную эффективность можно узнать только
по логам сделок (signals_log.csv / analyze_performance.py).

Что нового в v3 по сравнению с v2:
  1. Объёмный профиль (POC/VAH/VAL) и premium/discount зона — небольшая
     поправка к score + контекст в причинах (SMC-подход: LONG выгоднее
     из discount-зоны, SHORT — из premium)
  2. Детектор аномального объёма (как у сервисов вроде MRX Signal, но
     применяется к ликвидным парам, а не к микрокапам) — не меняет score,
     только предупреждает в причинах
  3. Конкретные уровни входа/TP1-3/SL прямо в сигнале — для ручного
     использования, не только для авто-сделок на демо
"""
from dataclasses import dataclass, field

import pandas as pd

from indicators import add_all_indicators
from volume_profile import compute_volume_profile, premium_discount_zone, volume_anomaly
from risk_levels import compute_levels


HIGHER_TIMEFRAME_MAP = {
    "5m": "1h",
    "15m": "1h",
    "1h": "4h",
    "4h": "1d",
}


@dataclass
class Signal:
    symbol: str
    direction: str
    score: float
    price: float
    atr: float
    reasons: list = field(default_factory=list)
    exchanges_confirming: int = 0
    exchanges_total: int = 0
    filtered_out_reason: str | None = None
    levels: dict | None = None
    volume_profile: dict | None = None
    zone: str | None = None


def _score_single_exchange(df: pd.DataFrame) -> tuple[float, str, list]:
    d = add_all_indicators(df)
    last = d.iloc[-1]
    reasons = []
    score = 0.0

    if not pd.isna(last.get("ema200", float("nan"))):
        if last["close"] > last["ema200"]:
            score += 15
            reasons.append("цена выше EMA200 (восходящий тренд)")
        else:
            score -= 15
            reasons.append("цена ниже EMA200 (нисходящий тренд)")

    if last["ema20"] > last["ema50"]:
        score += 15
        reasons.append("EMA20 > EMA50 (краткосрочный аптренд)")
    else:
        score -= 15
        reasons.append("EMA20 < EMA50 (краткосрочный даунтренд)")

    if last["rsi14"] < 30:
        score += 20
        reasons.append(f"RSI={last['rsi14']:.0f} — перепроданность")
    elif last["rsi14"] > 70:
        score -= 20
        reasons.append(f"RSI={last['rsi14']:.0f} — перекупленность")
    elif last["rsi14"] > 50:
        score += 5
    else:
        score -= 5

    if last["macd_hist"] > 0 and last["macd"] > last["macd_signal"]:
        score += 15
        reasons.append("MACD бычий кроссовер")
    elif last["macd_hist"] < 0 and last["macd"] < last["macd_signal"]:
        score -= 15
        reasons.append("MACD медвежий кроссовер")

    if not pd.isna(last.get("vol_sma20", float("nan"))) and last["vol_sma20"] > 0:
        if last["volume"] > 1.5 * last["vol_sma20"]:
            reasons.append("объём выше среднего (движение подтверждено)")
            score += 5 if score > 0 else (-5 if score < 0 else 0)

    direction = "LONG" if score > 0 else ("SHORT" if score < 0 else "NONE")
    return score, direction, reasons


def _higher_timeframe_trend(df_htf: pd.DataFrame) -> str:
    if df_htf is None or len(df_htf) < 25:
        return "NONE"
    d = add_all_indicators(df_htf)
    last = d.iloc[-1]
    if last["ema20"] > last["ema50"]:
        return "LONG"
    elif last["ema20"] < last["ema50"]:
        return "SHORT"
    return "NONE"


def _volatility_regime_ok(df: pd.DataFrame) -> tuple[bool, str]:
    d = add_all_indicators(df)
    if len(d) < 30 or d["atr14"].isna().all():
        return True, ""
    atr_now = d["atr14"].iloc[-1]
    atr_avg = d["atr14"].iloc[-30:].mean()
    if atr_avg == 0 or pd.isna(atr_avg):
        return True, ""
    ratio = atr_now / atr_avg
    if ratio < 0.4:
        return False, f"волатильность аномально низкая (ATR={ratio:.2f}x от средней) — рынок «спит»"
    if ratio > 3.0:
        return False, f"волатильность уже «выстрелила» (ATR={ratio:.2f}x от средней) — вход поздний"
    return True, ""


def build_signal(symbol: str, exchange_data: dict[str, pd.DataFrame],
                  htf_data: dict[str, pd.DataFrame] | None = None,
                  funding_info: dict | None = None) -> Signal | None:
    if not exchange_data:
        return None

    per_exchange_scores = {}
    last_price = None
    last_atr = None
    reference_df = None

    for ex_id, df in exchange_data.items():
        if len(df) < 25:
            continue
        score, direction, _ = _score_single_exchange(df)
        per_exchange_scores[ex_id] = (score, direction)
        if last_price is None:
            reference_df = df
            last_price = float(df["close"].iloc[-1])
            d = add_all_indicators(df)
            last_atr = float(d["atr14"].iloc[-1])

    if not per_exchange_scores:
        return None

    long_votes = sum(1 for s, d in per_exchange_scores.values() if d == "LONG")
    short_votes = sum(1 for s, d in per_exchange_scores.values() if d == "SHORT")
    total = len(per_exchange_scores)

    avg_score = sum(s for s, _ in per_exchange_scores.values()) / total
    majority_direction = "LONG" if long_votes > short_votes else ("SHORT" if short_votes > long_votes else "NONE")
    agreeing = max(long_votes, short_votes)
    agreement_ratio = agreeing / total

    strength = min(abs(avg_score), 100)
    confidence = strength * agreement_ratio

    reasons = [
        f"Направление подтверждают {agreeing}/{total} бирж",
        f"Средний скор индикаторов: {avg_score:.1f}",
    ]

    if funding_info and funding_info.get("funding_sources", 0) > 0:
        from funding_oi import funding_bias_score
        adj, explanation = funding_bias_score(funding_info["avg_funding_rate_pct"])
        reasons.append(explanation)
        if majority_direction == "LONG":
            confidence += adj
        elif majority_direction == "SHORT":
            confidence -= adj

    zone = None
    if reference_df is not None:
        zone, zone_pct = premium_discount_zone(reference_df)
        zone_labels = {"premium": "premium-зона (дорого)", "discount": "discount-зона (дёшево)",
                       "equilibrium": "равновесная зона"}
        reasons.append(f"Цена в {zone_pct:.0f}% диапазона — {zone_labels.get(zone, zone)}")

        # SMC-логика: LONG выгоднее из discount, SHORT — из premium
        if majority_direction == "LONG":
            if zone == "discount":
                confidence += 8
            elif zone == "premium":
                confidence -= 8
        elif majority_direction == "SHORT":
            if zone == "premium":
                confidence += 8
            elif zone == "discount":
                confidence -= 8

        is_anomaly, z_score = volume_anomaly(reference_df)
        if is_anomaly:
            reasons.append(f"⚡ Аномальный объём (z={z_score:.1f}) — возможен резкий импульс")

    confidence = max(0.0, min(100.0, confidence))

    vp = compute_volume_profile(reference_df) if reference_df is not None else None
    if vp:
        reasons.append(f"POC={vp['poc']:.4f}, зона объёма {vp['val']:.4f}-{vp['vah']:.4f}")

    signal = Signal(
        symbol=symbol,
        direction=majority_direction if confidence > 0 else "NONE",
        score=round(confidence, 1),
        price=last_price or 0.0,
        atr=last_atr or 0.0,
        reasons=reasons,
        exchanges_confirming=agreeing,
        exchanges_total=total,
        volume_profile=vp,
        zone=zone,
    )

    if signal.direction == "NONE":
        return signal

    if reference_df is not None:
        vol_ok, vol_reason = _volatility_regime_ok(reference_df)
        if not vol_ok:
            signal.filtered_out_reason = f"Волатильность вне нормы: {vol_reason}"
            signal.direction = "NONE"
            return signal

    if htf_data:
        htf_votes = [_higher_timeframe_trend(df) for df in htf_data.values() if df is not None]
        htf_votes = [v for v in htf_votes if v != "NONE"]
        if htf_votes:
            htf_long = htf_votes.count("LONG")
            htf_short = htf_votes.count("SHORT")
            htf_trend = "LONG" if htf_long > htf_short else ("SHORT" if htf_short > htf_long else "NONE")
            if htf_trend != "NONE" and htf_trend != majority_direction:
                signal.filtered_out_reason = f"Против тренда старшего ТФ ({htf_trend}) — сигнал заглушен"
                signal.direction = "NONE"
                return signal
            reasons.append(f"Старший ТФ подтверждает направление ({htf_trend})")

    signal.levels = compute_levels(signal.direction, signal.price, signal.atr)

    return signal
