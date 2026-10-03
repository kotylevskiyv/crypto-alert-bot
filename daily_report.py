"""
Ежедневный дайджест в Telegram — сколько сигналов закрылось за последние
24 часа, с каким результатом, и общая статистика на данный момент.

Работает полностью на собственных данных бота (state/trade_history.csv),
без обращения к внешним API.

Запуск по расписанию: .github/workflows/daily_report.yml
"""
import logging

from stats import load_trade_history, filter_since, compute_stats
from position_tracker import load_open_positions
from telegram_notify import send_message, format_daily_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("daily_report")


def main():
    history = load_trade_history()
    today_rows = filter_since(history, hours=24)
    today_stats = compute_stats(today_rows)
    alltime_stats = compute_stats(history)
    open_count = len(load_open_positions())

    message = format_daily_report(today_stats, alltime_stats, open_count)
    send_message(message)
    logger.info("Дневной отчёт отправлен")


if __name__ == "__main__":
    main()
