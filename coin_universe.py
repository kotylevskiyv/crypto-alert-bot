"""
Получение списка топ-N монет по капитализации через публичный API CoinGecko
(бесплатный, без ключа для базового использования, есть лимиты по частоте
запросов — но для одного вызова раз в прогон бота этого достаточно).
Список конвертируется в тикеры вида 'BTC/USDT' для дальнейшего скрининга.
"""
import logging
import requests

logger = logging.getLogger("coin_universe")

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

# Стейблкоины и их обёрнутые версии — торговать их против USDT бессмысленно
# (либо это будет пара стейбл/стейбл, либо шум без реального сигнала)
EXCLUDE_SYMBOLS = {
    "USDT", "USDC", "DAI", "TUSD", "FDUSD", "USDE", "USDP", "PYUSD", "GUSD", "USDD",
}


def get_top_symbols(limit: int = 200, quote: str = "USDT") -> list[str]:
    """Возвращает список тикеров вида 'BTC/USDT' для топ-N монет по капитализации."""
    pairs = []
    try:
        resp = requests.get(
            COINGECKO_URL,
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": min(limit, 250),
                "page": 1,
                "sparkline": "false",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        seen = set()
        for coin in data[:limit]:
            sym = (coin.get("symbol") or "").upper()
            if not sym or sym in EXCLUDE_SYMBOLS or sym in seen:
                continue
            seen.add(sym)
            pairs.append(f"{sym}/{quote}")
    except Exception as e:
        logger.error(f"Не удалось получить топ-{limit} монет с CoinGecko: {e}")
    return pairs
