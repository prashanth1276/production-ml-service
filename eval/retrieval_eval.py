"""Evaluate retrieval quality across configurations.

Configurations compared:
  1. baseline:      raw query, no user context
  2. user_context:  query + user purchase history + preferences

Run:  python -m eval.retrieval_eval
"""

import os

os.environ["REDIS_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import csv
from pathlib import Path

import numpy as np

from app.services.rec_engine import RecommendationEngine
from eval.metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from eval.test_queries import TEST_QUERIES

K = 5  # evaluate at top-5


def evaluate_config(engine, queries, use_user_context: bool = False) -> dict:
    """Run all test queries through a retrieval config and compute metrics."""
    ndcgs, precisions, recalls, rrs = [], [], [], []

    for item in queries:
        q = item["query"]
        relevant = set(item["relevant"])
        user_id = "user123" if use_user_context else None

        retrieved = engine.get_recommendations_sync(q, user_id=user_id, top_k=K)

        ndcgs.append(ndcg_at_k(retrieved, relevant, K))
        precisions.append(precision_at_k(retrieved, relevant, K))
        recalls.append(recall_at_k(retrieved, relevant, K))
        rrs.append(reciprocal_rank(retrieved, relevant))

    return {
        "ndcg@5": float(np.mean(ndcgs)),
        "precision@5": float(np.mean(precisions)),
        "recall@5": float(np.mean(recalls)),
        "mrr": float(np.mean(rrs)),
    }


def main():
    print("=" * 60)
    print("RETRIEVAL EVALUATION")
    print("=" * 60)

    engine = RecommendationEngine()
    engine.build_index_sync()

    results = []

    print("\n[1/2] Baseline (raw query, no user context)")
    baseline = evaluate_config(engine, TEST_QUERIES, use_user_context=False)
    baseline["config"] = "baseline"
    results.append(baseline)
    print(f"      NDCG@5:      {baseline['ndcg@5']:.3f}")
    print(f"      Precision@5: {baseline['precision@5']:.3f}")
    print(f"      Recall@5:    {baseline['recall@5']:.3f}")
    print(f"      MRR:         {baseline['mrr']:.3f}")

    print("\n[2/2] User-context-augmented (query + history + preferences)")
    with_ctx = evaluate_config(engine, TEST_QUERIES, use_user_context=True)
    with_ctx["config"] = "user_context"
    results.append(with_ctx)
    print(f"      NDCG@5:      {with_ctx['ndcg@5']:.3f}")
    print(f"      Precision@5: {with_ctx['precision@5']:.3f}")
    print(f"      Recall@5:    {with_ctx['recall@5']:.3f}")
    print(f"      MRR:         {with_ctx['mrr']:.3f}")

    # Save CSV
    Path("results").mkdir(exist_ok=True)
    out = "results/retrieval_metrics.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["config", "ndcg@5", "precision@5", "recall@5", "mrr"]
        )
        writer.writeheader()
        writer.writerows(results)
    print(f"\n✓ Saved {out}")

    # Print summary table
    print("\n" + "=" * 60)
    print(f"{'config':<20} {'NDCG@5':<10} {'P@5':<10} {'R@5':<10} {'MRR':<10}")
    print("-" * 60)
    for r in results:
        print(
            f"{r['config']:<20} {r['ndcg@5']:<10.3f} {r['precision@5']:<10.3f} "
            f"{r['recall@5']:<10.3f} {r['mrr']:<10.3f}"
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
