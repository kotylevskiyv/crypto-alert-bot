"""
Расчёт зоны входа, целей (TP1-3), стопа и рекомендуемого размера позиции.

v2: стоп сужен с 1.5×ATR до 1.0×ATR — раньше риск на сделку был БОЛЬШЕ, чем
дистанция до TP1 (R:R к TP1 был хуже 1:1), что противоречит любому здравому
риск-менеджменту. Теперь R:R к TP1 ≈ 1:1, к TP2 ≈ 2:1, к TP3 ≈ 3.5:1.
Также считаем R:R до TP2 (используется как "основная" цель для gate-проверки
в strategy.py) и предлагаемый размер позиции от вашего equity и риска на сделку.
"""
import config


def compute_levels(direction: str, price: float, atr: float) -> dict:
    if atr <= 0:
        atr = price * 0.005  # запасной вариант, если ATR почему-то не посчитан

    if direction == "LONG":
        entry_low = price - 0.3 * atr
        entry_high = price + 0.1 * atr
        sl = price - 1.0 * atr
        tp1 = price + 1.0 * atr
        tp2 = price + 2.0 * atr
        tp3 = price + 3.5 * atr
    else:  # SHORT
        entry_low = price - 0.1 * atr
        entry_high = price + 0.3 * atr
        sl = price + 1.0 * atr
        tp1 = price - 1.0 * atr
        tp2 = price - 2.0 * atr
        tp3 = price - 3.5 * atr

    risk_distance = abs(price - sl)
    reward_to_tp2 = abs(tp2 - price)
    rr_to_tp2 = reward_to_tp2 / risk_distance if risk_distance > 0 else 0.0

    # Position sizing: сколько $ рисковать на сделку и какой объём это даёт
    risk_amount_usdt = config.ACCOUNT_EQUITY_USDT * (config.RISK_PERCENT_PER_TRADE / 100)
    risk_distance_pct = risk_distance / price if price > 0 else 0
    position_size_usdt = risk_amount_usdt / risk_distance_pct if risk_distance_pct > 0 else 0.0
    position_qty = position_size_usdt / price if price > 0 else 0.0

    return {
        "entry_low": entry_low,
        "entry_high": entry_high,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "rr_to_tp2": rr_to_tp2,
        "risk_amount_usdt": risk_amount_usdt,
        "position_size_usdt": position_size_usdt,
        "position_qty": position_qty,
    }
