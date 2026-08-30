"""
Расчёт зоны входа, целей (TP1-3) и стопа на основе ATR — те же уровни,
что раньше считались только внутри bybit_demo.py для авто-сделок,
теперь доступны и для самого текстового алерта, чтобы ими можно было
пользоваться вручную.
"""


def compute_levels(direction: str, price: float, atr: float) -> dict:
    if atr <= 0:
        atr = price * 0.005  # запасной вариант, если ATR почему-то не посчитан

    if direction == "LONG":
        entry_low = price - 0.3 * atr
        entry_high = price + 0.1 * atr
        sl = price - 1.5 * atr
        tp1 = price + 1.0 * atr
        tp2 = price + 2.0 * atr
        tp3 = price + 3.5 * atr
    else:  # SHORT
        entry_low = price - 0.1 * atr
        entry_high = price + 0.3 * atr
        sl = price + 1.5 * atr
        tp1 = price - 1.0 * atr
        tp2 = price - 2.0 * atr
        tp3 = price - 3.5 * atr

    return {
        "entry_low": entry_low,
        "entry_high": entry_high,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
    }
