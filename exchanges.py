"""
Получение OHLCV-данных с бирж через ccxt.

Инстансы бирж и загруженные списки рынков кэшируются в памяти процесса —
это важно при сканировании большого числа монет: без кэша 200 монет x 10
бирж означали бы сотни повторных созданий объектов биржи и load_markets().
"""
import logging
import pandas as pd
import ccxt

import config

logger = logging.getLogger("exchanges")

_exchange_cache: dict = {}


def get_exchange_instance(exchange_id: str):
    """Возвращает закэшированный объект биржи ccxt (создаёт при первом обращении)."""
    if exchange_id in _exchange_cache:
        return _exchange_cache[exchange_id]
    try:
        klass = getattr(ccxt, exchange_id)
        ex = klass({
            "enableRateLimit": True,
            "timeout": 15000,
        })
        _exchange_cache[exchange_id] = ex
        return ex
    except Exception as e:
        logger.warning(f"Не удалось создать инстанс {exchange_id}: {e}")
        _exchange_cache[exchange_id] = None
        return None


def _ensure_markets(ex) -> bool:
    """Загружает список рынков биржи один раз за весь прогон, а не на каждый символ."""
    if ex.markets:
        return True
    try:
        ex.load_markets()
        return True
    except Exception as e:
        logger.info(f"{ex.id}: не удалось загрузить markets ({e})")
        return False


def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame | None:
    """
    Тянет свечи с одной биржи. Возвращает None, если биржа/пара недоступна
    (не все монеты листятся на всех биржах — это нормально).
    """
    ex = get_exchange_instance(exchange_id)
    if ex is None:
        return None
    if not _ensure_markets(ex):
        return None
    if symbol not in ex.symbols:
        return None
    try:
        raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not raw:
            return None
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["exchange"] = exchange_id
        return df
    except Exception as e:
        logger.info(f"{exchange_id}/{symbol}: пропуск ({e})")
        return None


def fetch_multi_exchange(symbol: str, timeframe: str, limit: int = 200) -> dict[str, pd.DataFrame]:
    """Тянет данные по одной паре со всех бирж из config.EXCHANGES."""
    results = {}
    for ex_id in config.EXCHANGES:
        df = fetch_ohlcv(ex_id, symbol, timeframe, limit)
        if df is not None and len(df) > 20:
            results[ex_id] = df
    return results
