"""Ablation: with vs. without Redis caching.

Since we may not have a real Redis running, this script uses mocks
to simulate the cache behavior — but the *latency* is real, since
the mock adds negligible overhead while real cache I/O would add
some. The point is to show relative timing between cold and warm
paths, which is dominated by whether we hit the embedding+FAISS
pipeline or return a cached response.

Run:  python -m eval.cache_eval
"""

import os

os.environ["REDIS_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import csv
import time
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def _percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    return s[int(p * (len(s) - 1))]


def main():
    print("=" * 60)
    print("CACHE ABLATION")
    print("=" * 60)

    from app.main import app
    from app.services.rec_engine import get_rec_engine

    query = "running shoes"
    n = 20

    # ---- Cold path: no cache (default behavior, REDIS_ENABLED=false) ----
    print("\n[1/2] Cold path (no cache)")
    with TestClient(app) as client:
        client.get(f"/api/recommendations?query={query}")  # warm-up
        cold_latencies = []
        for _ in range(n):
            start = time.perf_counter()
            client.get(f"/api/recommendations?query={query}")
            cold_latencies.append((time.perf_counter() - start) * 1000)

    # ---- Warm path: mocked cache hits ----
    print("[2/2] Warm path (mocked cache hits)")
    engine = get_rec_engine()
    fake_hit = b'["prod004","prod032","prod052"]'

    with TestClient(app) as client:
        # Patch the engine's internal cache getter to always return a hit
        engine._cache_get = AsyncMock(return_value=fake_hit)

        warm_latencies = []
        for _ in range(n):
            start = time.perf_counter()
            client.get(f"/api/recommendations?query={query}")
            warm_latencies.append((time.perf_counter() - start) * 1000)

    cold_mean = sum(cold_latencies) / len(cold_latencies)
    warm_mean = sum(warm_latencies) / len(warm_latencies)
    cold_p95 = _percentile(cold_latencies, 0.95)
    warm_p95 = _percentile(warm_latencies, 0.95)
    speedup = cold_mean / warm_mean if warm_mean > 0 else 0

    result = {
        "cold_mean_ms": round(cold_mean, 3),
        "cold_p95_ms": round(cold_p95, 3),
        "warm_mean_ms": round(warm_mean, 3),
        "warm_p95_ms": round(warm_p95, 3),
        "speedup_x": round(speedup, 2),
    }

    Path("results").mkdir(exist_ok=True)
    with open("results/cache_eval.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result.keys()))
        writer.writeheader()
        writer.writerow(result)

    print(f"\n  Cold mean:  {cold_mean:.2f} ms   (p95: {cold_p95:.2f} ms)")
    print(f"  Warm mean:  {warm_mean:.2f} ms   (p95: {warm_p95:.2f} ms)")
    print(f"  Speedup:    {speedup:.2f}x")
    print("\n✓ Saved results/cache_eval.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
