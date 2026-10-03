"""Отправка сообщений в Telegram через Bot API (без лишних библиотек)."""
import logging
import requests

import config

logger = logging.getLogger("telegram")


def send_message(text: str) -> bool:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram не настроен (пустой токен/chat_id) — сообщение не отправлено")
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(f"Telegram API вернул {resp.status_code}: {resp.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")
        return False


def format_signal_message(signal, demo_result: str | None = None, btc_context: str | None = None) -> str:
    arrow = "🟢 LONG" if signal.direction == "LONG" else ("🔴 SHORT" if signal.direction == "SHORT" else "⚪ NONE")
    lines = [
        f"<b>{arrow} {signal.symbol}</b>  |  {signal.price:.4f}  |  {signal.score:.0f}/100  |  {signal.exchanges_confirming}/{signal.exchanges_total} бирж",
    ]

    if signal.levels:
        lv = signal.levels
        lines.append(f"Вход: {lv['entry_low']:.4f}–{lv['entry_high']:.4f}")
        lines.append(f"TP1: {lv['tp1']:.4f}  TP2: {lv['tp2']:.4f}  TP3: {lv['tp3']:.4f}")
        lines.append(f"SL: {lv['sl']:.4f}")
        lines.append(f"Размер позиции (риск ${lv['risk_amount_usdt']:.0f}): "
                      f"${lv['position_size_usdt']:.0f} (~{lv['position_qty']:.4f} монет)")

    for r in signal.reasons:
        lines.append(f"• {r}")

    if btc_context:
        lines.append(btc_context)

    if demo_result:
        lines.append(f"Демо: {demo_result}")

    return "\n".join(lines)


def format_close_message(record: dict) -> str:
    """Алерт о том, что открытая ранее позиция закрылась (SL/TP/протухла)."""
    outcome = record["outcome"]
    outcome_labels = {
        "loss": "❌ SL",
        "win_tp1": "✅ TP1",
        "win_tp2": "✅ TP2",
        "win_tp3": "✅ TP3",
        "expired": "⏱ Протухла (72ч без исхода)",
    }
    label = outcome_labels.get(outcome, outcome)
    r_mult = record.get("r_multiple", 0)
    sign = "+" if r_mult >= 0 else ""
    return (
        f"<b>{label} — {record['symbol']} {record['direction']}</b>\n"
        f"Вход: {float(record['entry_price']):.4f} → Закрытие: {float(record['close_price']):.4f}\n"
        f"Результат: {sign}{r_mult:.2f}R"
    )


def format_performance_summary(stats: dict) -> str:
    """Сводка по накопленной статистике (аналог 'Learning Engine Snapshot')."""
    lines = [
        "<b>📊 Статистика сигналов</b>",
        f"Всего закрыто: {stats['total']}",
        f"Win-rate: {stats['win_rate']:.1f}%",
        f"Средний результат: {stats['avg_r']:+.2f}R на сделку",
        f"Суммарно: {stats['total_r']:+.2f}R",
    ]
    return "\n".join(lines)


def format_daily_report(today_stats: dict, alltime_stats: dict, open_count: int) -> str:
    lines = ["<b>📅 Дневной отчёт</b>"]
    if today_stats["total"] == 0:
        lines.append("За последние 24 часа ни один сигнал не закрылся.")
    else:
        lines.append(f"Закрыто за 24ч: {today_stats['total']}")
        lines.append(f"Win-rate за 24ч: {today_stats['win_rate']:.0f}%")
        lines.append(f"Результат за 24ч: {today_stats['total_r']:+.2f}R")
    lines.append(f"Сейчас открыто позиций: {open_count}")
    lines.append("")
    lines.append(f"Всего за всё время: {alltime_stats['total']} закрытых, "
                  f"win-rate {alltime_stats['win_rate']:.0f}%, "
                  f"{alltime_stats['total_r']:+.2f}R суммарно")
    return "\n".join(lines)


def format_weekly_report(week_stats: dict, alltime_stats: dict, outcomes: dict,
                          best: list, worst: list, correlation: dict | None) -> str:
    lines = ["<b>📊 Еженедельный разбор</b>"]
    lines.append(f"Закрыто за неделю: {week_stats['total']}")
    lines.append(f"Win-rate за неделю: {week_stats['win_rate']:.0f}%")
    lines.append(f"Результат за неделю: {week_stats['total_r']:+.2f}R "
                  f"(в среднем {week_stats['avg_r']:+.2f}R/сделку)")

    outcome_labels = {"loss": "SL", "win_tp1": "TP1", "win_tp2": "TP2",
                       "win_tp3": "TP3", "expired": "протухло (72ч)"}
    if outcomes:
        lines.append("")
        lines.append("<b>По исходам:</b>")
        for outcome, count in sorted(outcomes.items()):
            lines.append(f"• {outcome_labels.get(outcome, outcome)}: {count}")

    if best:
        lines.append("")
        lines.append("<b>Лучшие сделки:</b>")
        for r in best:
            lines.append(f"• {r['symbol']} {r['direction']}: {float(r['r_multiple']):+.2f}R")

    if worst:
        lines.append("")
        lines.append("<b>Худшие сделки:</b>")
        for r in worst:
            lines.append(f"• {r['symbol']} {r['direction']}: {float(r['r_multiple']):+.2f}R")

    if correlation:
        lines.append("")
        lines.append("<b>Диагностика скора:</b>")
        lines.append(f"Score ≥{correlation['median_score']:.0f} (n={correlation['n_high']}): "
                      f"{correlation['avg_r_high_score']:+.2f}R в среднем")
        lines.append(f"Score <{correlation['median_score']:.0f} (n={correlation['n_low']}): "
                      f"{correlation['avg_r_low_score']:+.2f}R в среднем")
        if correlation['avg_r_high_score'] <= correlation['avg_r_low_score']:
            lines.append("⚠️ Высокий score пока не показывает явного преимущества над низким — "
                          "возможно, стоит пересмотреть веса в strategy.py")

    lines.append("")
    lines.append(f"Всего за всё время: {alltime_stats['total']} закрытых, "
                  f"win-rate {alltime_stats['win_rate']:.0f}%, {alltime_stats['total_r']:+.2f}R")

    return "\n".join(lines)
