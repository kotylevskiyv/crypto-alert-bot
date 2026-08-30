"""
Funding rate и Open Interest — метрики закредитованности рынка на перпетуал-
фьючерсах. В отличие от спотовых свечей, это отражает, насколько рынок
перекошен в одну сторону плечом — источник многих резких разворотов.

Не все топ-10 "спотовых" бирж вообще предлагают перпетуалы ритейлу (например,
Coinbase/Kraken — ограниченно или недоступно в части юрисдикций), поэтому
здесь используется отдельный, более узкий список бирж с надёжной поддержкой
фьючерсных unified-методов в ccxt.
"""
import logging
import ccxt

import config

logger = logging.getLogger("funding_oi")

# Биржи с надёжной поддержкой fetchFundingRate/fetchOpenInterest в ccxt
# для USDT-перпетуалов
PERP_EXCHANGES = ["binance", "bybit", "okx", "bitget", "gate"]


def _perp_symbol_for(exchange_id: str, base_symbol: str) -> str:
    """BTC/USDT -> унифицированный тикер перпетуала для конкретной биржи ccxt."""
    # ccxt unified perpetual symbol format: 'BTC/USDT:USDT'
    return f"{base_symbol}:USDT"


def get_funding_and_oi(base_symbol: str) -> dict:
    """
    Возвращает усреднённые по доступным биржам funding_rate (в %) и
    направление изменения OI. Если данных нет — возвращает нейтральные значения.
    """
    funding_rates = []
    oi_values = {}

    for ex_id in PERP_EXCHANGES:
        try:
            klass = getattr(ccxt, ex_id)
            ex = klass({"enableRateLimit": True, "timeout": 15000,
                         "options": {"defaultType": "swap"}})
            ex.load_markets()
            perp_symbol = _perp_symbol_for(ex_id, base_symbol)
            if perp_symbol not in ex.symbols:
                continue

            if ex.has.get("fetchFundingRate"):
                fr = ex.fetch_funding_rate(perp_symbol)
                rate = fr.get("fundingRate")
                if rate is not None:
                    funding_rates.append(float(rate) * 100)  # в %

            if ex.has.get("fetchOpenInterest"):
                oi = ex.fetch_open_interest(perp_symbol)
                oi_val = oi.get("openInterestAmount") or oi.get("openInterestValue")
                if oi_val is not None:
                    oi_values[ex_id] = float(oi_val)

        except Exception as e:
            logger.info(f"{ex_id}: funding/OI недоступны для {base_symbol} ({e})")
            continue

    avg_funding = sum(funding_rates) / len(funding_rates) if funding_rates else 0.0

    return {
        "avg_funding_rate_pct": avg_funding,
        "funding_sources": len(funding_rates),
        "oi_by_exchange": oi_values,
    }


def funding_bias_score(avg_funding_rate_pct: float) -> tuple[float, str]:
    """
    Переводит funding rate в поправку к score (-25..+25) и текстовое пояснение.
    Логика контрарианская: экстремально высокий положительный funding
    (толпа переплечена в лонг) — предупреждающий сигнал против LONG.
    Пороги консервативные и настроены на "экстремальные" значения,
    а не на обычный дневной шум funding rate.
    """
    if avg_funding_rate_pct > 0.08:
        return -25, f"Funding {avg_funding_rate_pct:.3f}% — рынок сильно перегрет лонгами (риск для LONG)"
    elif avg_funding_rate_pct > 0.03:
        return -10, f"Funding {avg_funding_rate_pct:.3f}% — умеренный перекос в лонги"
    elif avg_funding_rate_pct < -0.08:
        return 25, f"Funding {avg_funding_rate_pct:.3f}% — рынок сильно перегрет шортами (риск для SHORT)"
    elif avg_funding_rate_pct < -0.03:
        return 10, f"Funding {avg_funding_rate_pct:.3f}% — умеренный перекос в шорты"
    else:
        return 0, f"Funding {avg_funding_rate_pct:.3f}% — нейтральный"
    for ex_id in PERP_EXCHANGES:
        try:
            klass = getattr(ccxt, ex_id)
            ex = klass({"enableRateLimit": True, "timeout": 15000,
                         "options": {"defaultType": "swap"}})
            ex.load_markets()
            perp_symbol = _perp_symbol_for(ex_id, base_symbol)
            if perp_symbol not in ex.symbols:
                continue

            if ex.has.get("fetchFundingRate"):
                fr = ex.fetch_funding_rate(perp_symbol)
                rate = fr.get("fundingRate")
                if rate is not None:
                    funding_rates.append(float(rate) * 100)  # в %

            if ex.has.get("fetchOpenInterest"):
                oi = ex.fetch_open_interest(perp_symbol)
                oi_val = oi.get("openInterestAmount") or oi.get("openInterestValue")
                if oi_val is not None:
                    oi_values[ex_id] = float(oi_val)

        except Exception as e:
            logger.info(f"{ex_id}: funding/OI недоступны для {base_symbol} ({e})")
            continue

    avg_funding = sum(funding_rates) / len(funding_rates) if funding_rates else 0.0

    return {
        "avg_funding_rate_pct": avg_funding,
        "funding_sources": len(funding_rates),
        "oi_by_exchange": oi_values,
    }


def funding_bias_score(avg_funding_rate_pct: float) -> tuple[float, str]:
    """
    Переводит funding rate в поправку к score (-25..+25) и текстовое пояснение.
    Логика контрарианская: экстремально высокий положительный funding
    (толпа переплечена в лонг) — предупреждающий сигнал против LONG.
    Пороги консервативные и настроены на "экстремальные" значения,
    а не на обычный дневной шум funding rate.
    """
    if avg_funding_rate_pct > 0.08:
        return -25, f"Funding {avg_funding_rate_pct:.3f}% — рынок сильно перегрет лонгами (риск для LONG)"
    elif avg_funding_rate_pct > 0.03:
        return -10, f"Funding {avg_funding_rate_pct:.3f}% — умеренный перекос в лонги"
    elif avg_funding_rate_pct < -0.08:
        return 25, f"Funding {avg_funding_rate_pct:.3f}% — рынок сильно перегрет шортами (риск для SHORT)"
    elif avg_funding_rate_pct < -0.03:
        return 10, f"Funding {avg_funding_rate_pct:.3f}% — умеренный перекос в шорты"
    else:
        return 0, f"Funding {avg_funding_rate_pct:.3f}% — нейтральный"
