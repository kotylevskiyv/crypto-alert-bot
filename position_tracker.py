"""
Monitor + Learn — отслеживание того, что реально произошло с каждым
отправленным сигналом, БЕЗ обращения к Bybit API (который заблокирован
для GitHub Actions). Логика простая: после алерта запоминаем цену входа,
SL и TP1-3; на каждом следующем прогоне проверяем текущую цену по той же
паре — если она пересекла SL или один из TP, считаем сигнал закрытым и
записываем исход (win/loss, R-мультипликатор) в историю.

Файлы состояния (state/open_positions.csv, state/trade_history.csv)
коммитятся обратно в репозиторий отдельным шагом в bot.yml — сами по себе
раннеры GitHub Actions ничего не хранят между запусками.
"""
import csv
import logging
import os
from datetime import datetime, timezone

import config
from exchanges import fetch_ohlcv

logger = logging.getLogger("position_tracker")

OPEN_FIELDNAMES = ["symbol", "direction", "entry_price", "sl", "tp1", "tp2", "tp3",
                    "risk_amount_usdt", "score", "opened_at_utc"]
HISTORY_FIELDNAMES = OPEN_FIELDNAMES + ["closed_at_utc", "close_price", "outcome", "r_multiple"]


def _ensure_state_dir():
    os.makedirs(config.STATE_DIR, exist_ok=True)


def _read_csv(path: str, fieldnames: list) -> list[dict]:
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: str, fieldnames: list, rows: list[dict]):
    _ensure_state_dir()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_open_positions() -> list[dict]:
    return _read_csv(config.OPEN_POSITIONS_FILE, OPEN_FIELDNAMES)


def save_open_positions(positions: list[dict]):
    _write_csv(config.OPEN_POSITIONS_FILE, OPEN_FIELDNAMES, positions)


def append_trade_history(record: dict):
    _ensure_state_dir()
    file_exists = os.path.isfile(config.TRADE_HISTORY_FILE)
    with open(config.TRADE_HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)


def open_new_position(signal) -> None:
    """Начинает отслеживать сигнал, который только что был отправлен в Telegram."""
    if not signal.levels:
        return
    positions = load_open_positions()
    positions.append({
        "symbol": signal.symbol,
        "direction": signal.direction,
        "entry_price": signal.price,
        "sl": signal.levels["sl"],
        "tp1": signal.levels["tp1"],
        "tp2": signal.levels["tp2"],
        "tp3": signal.levels["tp3"],
        "risk_amount_usdt": signal.levels.get("risk_amount_usdt", 0.0),
        "score": signal.score,
        "opened_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    save_open_positions(positions)


def _get_current_price(symbol: str) -> float | None:
    """Лёгкий запрос текущей цены с первой доступной рабочей биржи."""
    for ex_id in config.EXCHANGES:
        df = fetch_ohlcv(ex_id, symbol, "5m", limit=3)
        if df is not None and len(df) > 0:
            return float(df["close"].iloc[-1])
    return None


def _hours_since(iso_timestamp: str) -> float:
    opened = datetime.fromisoformat(iso_timestamp)
    now = datetime.now(timezone.utc)
    return (now - opened).total_seconds() / 3600


def _check_single_position(pos: dict) -> dict | None:
    """
    Проверяет одну открытую позицию. Возвращает запись для истории, если
    позиция закрылась (SL/TP/протухла), иначе None (остаётся открытой).
    """
    symbol = pos["symbol"]
    direction = pos["direction"]
    entry = float(pos["entry_price"])
    sl = float(pos["sl"])
    tp1, tp2, tp3 = float(pos["tp1"]), float(pos["tp2"]), float(pos["tp3"])
    risk_amount = float(pos.get("risk_amount_usdt", 0) or 0)

    price = _get_current_price(symbol)
    if price is None:
        logger.info(f"{symbol}: не удалось получить текущую цену для проверки позиции")
        return None

    risk_distance = abs(entry - sl)
    outcome = None
    close_price = None

    if direction == "LONG":
        if price <= sl:
            outcome, close_price = "loss", sl
        elif price >= tp3:
            outcome, close_price = "win_tp3", tp3
        elif price >= tp2:
            outcome, close_price = "win_tp2", tp2
        elif price >= tp1:
            outcome, close_price = "win_tp1", tp1
    else:  # SHORT
        if price >= sl:
            outcome, close_price = "loss", sl
        elif price <= tp3:
            outcome, close_price = "win_tp3", tp3
        elif price <= tp2:
            outcome, close_price = "win_tp2", tp2
        elif price <= tp1:
            outcome, close_price = "win_tp1", tp1

    if outcome is None and _hours_since(pos["opened_at_utc"]) > config.POSITION_MAX_AGE_HOURS:
        outcome, close_price = "expired", price

    if outcome is None:
        return None  # всё ещё открыта, ничего не делаем

    if risk_distance > 0:
        realized_move = (close_price - entry) if direction == "LONG" else (entry - close_price)
        r_multiple = realized_move / risk_distance
    else:
        r_multiple = 0.0

    return {
        **pos,
        "closed_at_utc": datetime.now(timezone.utc).isoformat(),
        "close_price": close_price,
        "outcome": outcome,
        "r_multiple": round(r_multiple, 2),
    }


def check_and_close_positions() -> list[dict]:
    """
    Проверяет все открытые позиции, закрывает те, что достигли SL/TP/протухли,
    перезаписывает open_positions.csv без них и дописывает закрытые в
    trade_history.csv. Возвращает список закрытых записей (для Telegram-алертов).
    """
    open_positions = load_open_positions()
    if not open_positions:
        return []

    still_open = []
    closed = []

    for pos in open_positions:
        result = _check_single_position(pos)
        if result is None:
            still_open.append(pos)
        else:
            closed.append(result)
            append_trade_history(result)

    save_open_positions(still_open)

    if closed:
        logger.info(f"Закрыто позиций: {len(closed)}, осталось открытых: {len(still_open)}")

    return closed
