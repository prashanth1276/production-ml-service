"""Ablation: dense vs hybrid vs hybrid + reranker.

Run:  python -m eval.retrieval_ablation
"""

import os

os.environ["REDIS_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import csv
from pathlib import Path

import numpy as np

from app.services.hybrid_engine import HybridEngine
from app.services.rec_engine import RecommendationEngine
from eval.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from eval.test_queries import TEST_QUERIES

K = 5


def _evaluate(engine, queries):
    ndcgs, ps, rs, rrs = [], [], [], []
    for item in queries:
        q = item["query"]
        relevant = set(item["relevant"])
        retrieved = engine.get_recommendations_sync(q, top_k=K)
        ndcgs.append(ndcg_at_k(retrieved, relevant, K))
        ps.append(precision_at_k(retrieved, relevant, K))
        rs.append(recall_at_k(retrieved, relevant, K))
        rrs.append(reciprocal_rank(retrieved, relevant))
    return {
        "ndcg@5": float(np.mean(ndcgs)),
        "precision@5": float(np.mean(ps)),
        "recall@5": float(np.mean(rs)),
        "mrr": float(np.mean(rrs)),
    }


def main():
    print("=" * 72)
    print("RETRIEVAL ABLATION: dense vs hybrid vs hybrid+rerank")
    print("=" * 72)

    dense = RecommendationEngine()
    dense.build_index_sync()

    rows = []
    for mode in ["dense", "hybrid", "hybrid_rerank"]:
        engine = HybridEngine(dense, mode=mode)
        # Sync wrapper for evaluation
        if mode == "dense":
            metrics = _evaluate(dense, TEST_QUERIES)
        else:
            # Wrap async calls
            import asyncio

            class _Sync:
                def __init__(self, h):
                    self.h = h

                def get_recommendations_sync(self, q, top_k=K):
                    return asyncio.run(self.h.get_recommendations(q, top_k=top_k))

            metrics = _evaluate(_Sync(engine), TEST_QUERIES)
        metrics["config"] = mode
        rows.append(metrics)
        print(f"  {mode:<16} NDCG@5 = {metrics['ndcg@5']:.3f}  MRR = {metrics['mrr']:.3f}")

    Path("results").mkdir(exist_ok=True)
    out = "results/retrieval_ablation.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["config", "ndcg@5", "precision@5", "recall@5", "mrr"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n✓ Saved {out}")


if __name__ == "__main__":
    main()
