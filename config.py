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

# Рабочие биржи для получения данных с GitHub Actions.
# Binance и Bybit НЕ включены — оба гарантированно блокируют IP серверов
# GitHub Actions (гео-ограничение на уровне домена, подтверждено логами:
# binance 451 "restricted location", bybit 403 "blocked from your country").
# Держать их в списке бессмысленно — 100% отказ на каждом запросе, только
# лишние секунды и шум в логах.
EXCHANGES = [
    "okx",
    "coinbase",
    "kraken",
    "kucoin",
    "bitget",
    "gate",
    "mexc",
    "htx",
]

# --- Risk Engine (по мотивам Risk-шага из референса: position sizing + R:R gate) ---
# Размер счёта, от которого считается position sizing в алертах.
# Поставьте равным вашему реальному капиталу/счёту (например, $50,000 на CFT).
ACCOUNT_EQUITY_USDT = float(os.getenv("ACCOUNT_EQUITY_USDT", "50000"))
# Сколько % от equity готовы потерять на ОДНОЙ сделке при срабатывании стопа
RISK_PERCENT_PER_TRADE = float(os.getenv("RISK_PERCENT_PER_TRADE", "1.0"))
# Минимальное соотношение прибыль/риск (до TP2) — сигналы хуже этого порога
# заглушаются фильтром, как и остальные gate-проверки в strategy.py
MIN_RR_RATIO = float(os.getenv("MIN_RR_RATIO", "1.5"))

# --- Monitor + Learn: отслеживание судьбы сигналов без Bybit API ---
# Файлы состояния коммитятся обратно в репозиторий шагом в bot.yml,
# поэтому переживают между запусками GitHub Actions (раннеры сами по себе
# одноразовые и ничего не хранят).
STATE_DIR = os.path.join(os.path.dirname(__file__), "state")
OPEN_POSITIONS_FILE = os.path.join(STATE_DIR, "open_positions.csv")
TRADE_HISTORY_FILE = os.path.join(STATE_DIR, "trade_history.csv")
# Через сколько часов открытая (не сработавшая ни в TP, ни в SL) позиция
# считается протухшей и закрывается принудительно по текущей цене
POSITION_MAX_AGE_HOURS = float(os.getenv("POSITION_MAX_AGE_HOURS", "72"))

LOG_FILE = os.path.join(os.path.dirname(__file__), "signals_log.csv")
