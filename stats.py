"""
Общие функции подсчёта статистики по закрытым сигналам (state/trade_history.csv).
Используется analyze_performance.py (ручной запуск), daily_report.py и
weekly_report.py (автоматические, по расписанию GitHub Actions).
"""
import csv
import os
from datetime import datetime, timedelta, timezone

import config


def _read_csv(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_trade_history() -> list[dict]:
    return _read_csv(config.TRADE_HISTORY_FILE)


def filter_since(rows: list[dict], hours: float, timestamp_field: str = "closed_at_utc") -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = []
    for r in rows:
        ts = r.get(timestamp_field)
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if dt >= cutoff:
            result.append(r)
    return result


def compute_stats(rows: list[dict]) -> dict:
    total = len(rows)
    if total == 0:
        return {"total": 0, "win_rate": 0.0, "avg_r": 0.0, "total_r": 0.0}
    r_values = [float(r["r_multiple"]) for r in rows]
    wins = sum(1 for r in rows if r["outcome"].startswith("win"))
    return {
        "total": total,
        "win_rate": (wins / total) * 100,
        "avg_r": sum(r_values) / total,
        "total_r": sum(r_values),
    }


def breakdown_by_outcome(rows: list[dict]) -> dict:
    counts = {}
    for r in rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    return counts


def best_worst_trades(rows: list[dict], n: int = 3) -> tuple[list[dict], list[dict]]:
    sorted_rows = sorted(rows, key=lambda r: float(r["r_multiple"]), reverse=True)
    best = sorted_rows[:n]
    worst = sorted_rows[-n:][::-1] if len(sorted_rows) >= n else list(reversed(sorted_rows))
    return best, worst


def score_correlation(rows: list[dict]) -> dict | None:
    """
    Сравнивает средний результат (R) у сигналов с высоким и низким score —
    диагностика того, реально ли высокий score коррелирует с лучшим исходом.
    Если нет — повод пересмотреть веса индикаторов в strategy.py.
    """
    scored = [r for r in rows if r.get("score")]
    if len(scored) < 4:
        return None
    scores = sorted(float(r["score"]) for r in scored)
    median = scores[len(scores) // 2]
    high = [r for r in scored if float(r["score"]) >= median]
    low = [r for r in scored if float(r["score"]) < median]
    if not high or not low:
        return None
    avg_high = sum(float(r["r_multiple"]) for r in high) / len(high)
    avg_low = sum(float(r["r_multiple"]) for r in low) / len(low)
    return {
        "median_score": median,
        "avg_r_high_score": avg_high,
        "avg_r_low_score": avg_low,
        "n_high": len(high),
        "n_low": len(low),
    }
