"""
Еженедельный разбор полётов в Telegram — win-rate за неделю, лучшие и
худшие сделки, разбивка по типам исхода, и диагностика: реально ли
высокий score коррелирует с лучшим результатом (аналог "Learn"-шага
из референса — what worked / what failed / insights).

Запуск по расписанию: .github/workflows/weekly_report.yml
"""
import logging

from stats import (load_trade_history, filter_since, compute_stats,
                    breakdown_by_outcome, best_worst_trades, score_correlation)
from telegram_notify import send_message, format_weekly_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("weekly_report")


def main():
    history = load_trade_history()
    week_rows = filter_since(history, hours=24 * 7)

    if not week_rows:
        send_message("📊 Еженедельный разбор: за эту неделю ни один сигнал ещё "
                      "не закрылся — статистики пока нет.")
        logger.info("Нет данных за неделю — отправлено короткое уведомление")
        return

    week_stats = compute_stats(week_rows)
    alltime_stats = compute_stats(history)
    outcomes = breakdown_by_outcome(week_rows)
    best, worst = best_worst_trades(week_rows, n=3)
    correlation = score_correlation(week_rows)

    message = format_weekly_report(week_stats, alltime_stats, outcomes, best, worst, correlation)
    send_message(message)
    logger.info("Еженедельный отчёт отправлен")


if __name__ == "__main__":
    main()
