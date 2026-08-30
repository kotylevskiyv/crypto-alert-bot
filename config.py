"""Загрузка конфигурации из .env"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key, str(default)).strip().lower()
    return val in ("1", "true", "yes", "on")


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

BYBIT_DEMO_API_KEY = os.getenv("BYBIT_DEMO_API_KEY", "")
BYBIT_DEMO_API_SECRET = os.getenv("BYBIT_DEMO_API_SECRET", "")

# Статический список монет — используется, только если USE_TOP_N_UNIVERSE=false
SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "BTC/USDT,ETH/USDT").split(",") if s.strip()]

TIMEFRAME = os.getenv("TIMEFRAME", "15m")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "900"))
MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", "70"))
AUTO_TRADE_DEMO = _get_bool("AUTO_TRADE_DEMO", False)
POSITION_SIZE_USDT = float(os.getenv("POSITION_SIZE_USDT", "100"))
LEVERAGE = int(os.getenv("LEVERAGE", "5"))

# --- Сканирование топ-N монет по капитализации ---
USE_TOP_N_UNIVERSE = _get_bool("USE_TOP_N_UNIVERSE", True)
UNIVERSE_SIZE = int(os.getenv("UNIVERSE_SIZE", "200"))
# Сколько лучших кандидатов после быстрого скрининга уходят на полный анализ
CANDIDATES_PER_RUN = int(os.getenv("CANDIDATES_PER_RUN", "8"))
# Минимальный |score| на быстром скрининге, чтобы монета попала в кандидаты
QUICK_MIN_SCORE = float(os.getenv("QUICK_MIN_SCORE", "15"))
# Биржи для быстрого скрининга (пробуются по порядку, пока не найдётся пара)
QUICK_SCAN_EXCHANGES = [e.strip() for e in os.getenv(
    "QUICK_SCAN_EXCHANGES", "bitget,okx,kucoin,htx,mexc"
).split(",") if e.strip()]

# Топ-10 бирж по объёму (публичные данные, ключи не нужны для чтения цен)
EXCHANGES = [
    "binance",
    "bybit",
    "okx",
    "coinbase",
    "kraken",
    "kucoin",
    "bitget",
    "gate",
    "mexc",
    "htx",
]

LOG_FILE = os.path.join(os.path.dirname(__file__), "signals_log.csv")
