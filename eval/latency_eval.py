"""Profile latency of each endpoint.

Reports p50, p95, p99, and mean for:
  - /health           (baseline: no dependencies)
  - /api/recommendations  (retrieval only)
  - /api/conversation     (retrieval + LLM)

Run:  python -m eval.latency_eval
"""
import os
os.environ["REDIS_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import csv
import statistics
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


N_RUNS = 30


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(p * (len(s) - 1))
    return s[idx]


def measure(name: str, callable_fn, n: int = N_RUNS) -> dict:
    """Run callable_fn n times and return latency percentiles."""
    # Warm-up
    callable_fn()

    latencies = []
    for _ in range(n):
        start = time.perf_counter()
        callable_fn()
        latencies.append((time.perf_counter() - start) * 1000)  # ms

    return {
        "endpoint": name,
        "n": n,
        "mean_ms": statistics.mean(latencies),
        "p50_ms": _percentile(latencies, 0.50),
        "p95_ms": _percentile(latencies, 0.95),
        "p99_ms": _percentile(latencies, 0.99),
    }


def main():
    print("=" * 60)
    print("LATENCY PROFILING")
    print("=" * 60)

    with TestClient(app) as client:
        results = []

        print(f"\n[1/3] /health")
        r = measure("health", lambda: client.get("/health"))
        results.append(r)

        print(f"[2/3] /api/recommendations (retrieval only)")
        r = measure(
            "recommendations",
            lambda: client.get("/api/recommendations?query=running+shoes&top_k=5"),
        )
        results.append(r)

        print(f"[3/3] /api/conversation (retrieval + LLM)")
        r = measure(
            "conversation",
            lambda: client.post("/api/conversation",
                                json={"message": "shoes under 500"}),
        )
        results.append(r)

    # Save CSV
    Path("results").mkdir(exist_ok=True)
    out = "results/latency_profile.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "endpoint", "n", "mean_ms", "p50_ms", "p95_ms", "p99_ms",
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n✓ Saved {out}")

    print("\n" + "=" * 60)
    print(f"{'endpoint':<20} {'mean':<10} {'p50':<10} {'p95':<10} {'p99':<10}")
    print("-" * 60)
    for r in results:
        print(f"{r['endpoint']:<20} {r['mean_ms']:<10.2f} "
              f"{r['p50_ms']:<10.2f} {r['p95_ms']:<10.2f} {r['p99_ms']:<10.2f}")
    print("=" * 60)
    print("(all values in ms)")


if __name__ == "__main__":
    main()