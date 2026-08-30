"""
Быстрый предварительный скрининг по всей вселенной монет (топ-N по капитализации).

Использует ОДНУ быструю биржу (с фолбэком на следующую в списке, если монеты
на ней нет) и укороченную историю свечей — полный мультибиржевый анализ
(как в strategy.build_signal) на 200+ монетах занял бы очень долго и создал
бы риск рейт-лимитов на биржах.

Кандидаты, прошедшие быстрый скрининг, дальше уходят на полный анализ —
ровно тот же процесс, что раньше применялся к фиксированному списку монет.
"""
import logging

from exchanges import fetch_ohlcv
from strategy import _score_single_exchange
import config

logger = logging.getLogger("screener")


def quick_scan(universe_symbols: list[str]) -> list[tuple[str, float, str]]:
    """
    Возвращает список (symbol, score, direction), отсортированный по |score|
    по убыванию — только для монет, прошедших порог config.QUICK_MIN_SCORE.
    """
    results = []
    checked = 0
    for symbol in universe_symbols:
        df = None
        for ex_id in config.QUICK_SCAN_EXCHANGES:
            df = fetch_ohlcv(ex_id, symbol, config.TIMEFRAME, limit=60)
            if df is not None and len(df) >= 25:
                break
        if df is None or len(df) < 25:
            continue
        checked += 1
        try:
            score, direction, _ = _score_single_exchange(df)
        except Exception as e:
            logger.info(f"{symbol}: ошибка быстрого скоринга ({e})")
            continue
        if abs(score) >= config.QUICK_MIN_SCORE:
            results.append((symbol, score, direction))

    logger.info(f"Быстрый скрининг: удалось получить данные по {checked}/{len(universe_symbols)} монет")
    results.sort(key=lambda x: abs(x[1]), reverse=True)
    return results
