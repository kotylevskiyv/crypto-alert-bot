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


def format_signal_message(signal, demo_result: str | None = None) -> str:
    arrow = "🟢 LONG" if signal.direction == "LONG" else ("🔴 SHORT" if signal.direction == "SHORT" else "⚪ NONE")
    lines = [
        f"<b>{arrow} {signal.symbol}</b>  |  {signal.price:.4f}  |  {signal.score:.0f}/100  |  {signal.exchanges_confirming}/{signal.exchanges_total} бирж",
    ]
    for r in signal.reasons:
        lines.append(f"• {r}")
    if demo_result:
        lines.append(f"Демо: {demo_result}")
    return "\n".join(lines)
