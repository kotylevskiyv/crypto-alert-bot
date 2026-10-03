"""
Считает реальную статистику по закрытым сигналам из state/trade_history.csv.

v2: раньше этот скрипт спрашивал статистику у Bybit Demo API — но Bybit
полностью заблокирован для серверов GitHub Actions, поэтому та версия
никогда реально не работала в автоматическом режиме. Теперь бот сам
отслеживает судьбу каждого своего сигнала (см. position_tracker.py) и
считает win-rate/expectancy по собственным данным, без внешних API.

Запуск: python analyze_performance.py
"""
import csv
import os

import config


def load_trade_history() -> list[dict]:
    if not os.path.isfile(config.TRADE_HISTORY_FILE):
        return []
    with open(config.TRADE_HISTORY_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_stats(rows: list[dict]) -> dict:
    total = len(rows)
    if total == 0:
        return {"total": 0, "win_rate": 0.0, "avg_r": 0.0, "total_r": 0.0}

    r_values = [float(r["r_multiple"]) for r in rows]
    wins = sum(1 for r in rows if r["outcome"].startswith("win"))
    win_rate = (wins / total) * 100
    total_r = sum(r_values)
    avg_r = total_r / total

    return {"total": total, "win_rate": win_rate, "avg_r": avg_r, "total_r": total_r}


def main():
    rows = load_trade_history()
    if not rows:
        print("Закрытых сигналов пока нет — статистику собрать не из чего.")
        print("Она появится сама по себе после того, как какие-то из отправленных")
        print("алертов дойдут до TP или SL (это отслеживает position_tracker.py на")
        print("каждом прогоне бота).")
        return

    stats = compute_stats(rows)

    print(f"\n=== Статистика по {stats['total']} закрытым сигналам ===")
    print(f"Win-rate: {stats['win_rate']:.1f}%")
    print(f"Средний результат: {stats['avg_r']:+.2f}R на сделку")
    print(f"Суммарно: {stats['total_r']:+.2f}R")

    print("\nПо типам исхода:")
    outcome_counts = {}
    for r in rows:
        outcome_counts[r["outcome"]] = outcome_counts.get(r["outcome"], 0) + 1
    for outcome, count in sorted(outcome_counts.items()):
        print(f"  {outcome}: {count}")

    print("\nЭто фактические цифры по собственным сигналам бота — именно на них")
    print("стоит ориентироваться, а не на внутренний 'скор уверенности'.")


if __name__ == "__main__":
    main()
