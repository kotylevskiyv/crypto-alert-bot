"""
Логирование каждого сигнала в CSV — это единственный способ честно
проверить реальную эффективность стратегии, а не поверить цифре "скора".
"""
import csv
import os
from datetime import datetime, timezone

import config

FIELDNAMES = ["timestamp_utc", "symbol", "direction", "score", "price",
              "exchanges_confirming", "exchanges_total", "demo_result"]


def log_signal(signal, demo_result: str = ""):
    file_exists = os.path.isfile(config.LOG_FILE)
    with open(config.LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "symbol": signal.symbol,
            "direction": signal.direction,
            "score": signal.score,
            "price": signal.price,
            "exchanges_confirming": signal.exchanges_confirming,
            "exchanges_total": signal.exchanges_total,
            "demo_result": demo_result,
        })
