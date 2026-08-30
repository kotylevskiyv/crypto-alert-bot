"""
Точка входа.

Если USE_TOP_N_UNIVERSE=true (по умолчанию):
  1. получает топ-UNIVERSE_SIZE монет по капитализации (CoinGecko)
  2. быстрый скрининг по всей вселенной (1 биржа, короткая история) —
     отсеивает большинство монет, оставляя только заметные сетапы
  3. полный анализ (мультибиржевое согласие, funding, старший ТФ,
     volume profile, TP/SL) — только для CANDIDATES_PER_RUN лучших кандидатов
Если USE_TOP_N_UNIVERSE=false — работает по статическому списку config.SYMBOLS,
как раньше.

Запуск: python main.py [--once]
"""
import logging
import time
import sys

import config
from exchanges import fetch_multi_exchange
from strategy import build_signal, HIGHER_TIMEFRAME_MAP
from telegram_notify import send_message, format_signal_message
from logger_csv import log_signal
from funding_oi import get_funding_and_oi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

_btc_context: str | None = None


def _compute_btc_context() -> str | None:
    """Считает короткую строку контекста по BTC — берётся один раз за прогон,
    независимо от того, попал ли сам BTC в список кандидатов."""
    data = fetch_multi_exchange("BTC/USDT", config.TIMEFRAME, limit=30)
    if not data:
        return None
    df = next(iter(data.values()))
    if len(df) < 25:
        return None
    change_pct = (df["close"].iloc[-1] - df["close"].iloc[-25]) / df["close"].iloc[-25] * 100
    direction = "рост" if change_pct >= 0 else "падение"
    return f"BTC {change_pct:+.1f}% ({direction} за период) — общий фон рынка"


def build_symbol_list() -> list[str]:
    """Возвращает список монет для полного анализа в этом прогоне."""
    if not config.USE_TOP_N_UNIVERSE:
        return config.SYMBOLS

    from coin_universe import get_top_symbols
    from screener import quick_scan

    universe = get_top_symbols(config.UNIVERSE_SIZE)
    if not universe:
        logger.warning("Не удалось получить список монет с CoinGecko — используем запасной список SYMBOLS")
        return config.SYMBOLS

    logger.info(f"Вселенная монет: {len(universe)} тикеров (топ-{config.UNIVERSE_SIZE} по капитализации)")

    candidates = quick_scan(universe)
    logger.info(f"Быстрый скрининг: {len(candidates)} монет прошли порог |score|>={config.QUICK_MIN_SCORE}")

    top = candidates[:config.CANDIDATES_PER_RUN]
    if top:
        logger.info("Кандидаты на полный анализ: " +
                    ", ".join(f"{s}({d},{sc:.0f})" for s, sc, d in top))
    return [s for s, _, _ in top]


def process_symbol(symbol: str):
    logger.info(f"Анализ {symbol}...")
    data = fetch_multi_exchange(symbol, config.TIMEFRAME)
    if not data:
        logger.warning(f"{symbol}: нет данных ни с одной биржи, пропуск")
        return

    htf = HIGHER_TIMEFRAME_MAP.get(config.TIMEFRAME)
    htf_data = fetch_multi_exchange(symbol, htf) if htf else None

    funding_info = get_funding_and_oi(symbol)

    signal = build_signal(symbol, data, htf_data=htf_data, funding_info=funding_info)
    if signal is None or signal.direction == "NONE":
        reason = getattr(signal, "filtered_out_reason", None) if signal else None
        if reason:
            logger.info(f"{symbol}: сигнал заглушен фильтром — {reason}")
        else:
            logger.info(f"{symbol}: явного сигнала нет")
        return

    logger.info(f"{symbol}: {signal.direction}, score={signal.score}")

    demo_result = None
    if signal.score >= config.MIN_CONFIDENCE_SCORE:
        if config.AUTO_TRADE_DEMO:
            from bybit_demo import place_market_order
            demo_result = place_market_order(
                symbol=symbol,
                direction=signal.direction,
                qty_usdt=config.POSITION_SIZE_USDT,
                price=signal.price,
                atr=signal.atr,
                leverage=config.LEVERAGE,
            )
            logger.info(f"{symbol}: демо-сделка -> {demo_result}")

        btc_ctx = _btc_context if symbol != "BTC/USDT" else None
        message = format_signal_message(signal, demo_result, btc_context=btc_ctx)
        send_message(message)
        log_signal(signal, demo_result or "")
    else:
        logger.info(f"{symbol}: скор {signal.score} ниже порога {config.MIN_CONFIDENCE_SCORE}, алерт не шлём")


def run_cycle():
    global _btc_context
    _btc_context = _compute_btc_context()

    symbols = build_symbol_list()
    if not symbols:
        logger.info("Нет монет для анализа в этом цикле")
        return

    for symbol in symbols:
        try:
            process_symbol(symbol)
        except Exception as e:
            logger.exception(f"Ошибка обработки {symbol}: {e}")


def main_loop():
    logger.info("Бот запущен. USE_TOP_N_UNIVERSE=%s, UNIVERSE_SIZE=%s, CANDIDATES_PER_RUN=%s, "
                "таймфрейм=%s, интервал=%sс, авто-торговля demo=%s",
                config.USE_TOP_N_UNIVERSE, config.UNIVERSE_SIZE, config.CANDIDATES_PER_RUN,
                config.TIMEFRAME, config.CHECK_INTERVAL_SECONDS, config.AUTO_TRADE_DEMO)

    while True:
        run_cycle()
        logger.info(f"Цикл завершён, спим {config.CHECK_INTERVAL_SECONDS}с")
        time.sleep(config.CHECK_INTERVAL_SECONDS)


def run_once():
    """Для запуска через cron / GitHub Actions без постоянного процесса."""
    run_cycle()


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        try:
            main_loop()
        except KeyboardInterrupt:
            logger.info("Остановлено пользователем")
