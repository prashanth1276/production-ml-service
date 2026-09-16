"""Standard information retrieval metrics.

Implements:
  - Precision@K:  fraction of top-K results that are relevant
  - Recall@K:     fraction of all relevant items found in top-K
  - MRR:          mean reciprocal rank of first relevant result
  - NDCG@K:       normalized discounted cumulative gain
"""

import math


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for r in top_k if r in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for i, r in enumerate(retrieved, start=1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def dcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    score = 0.0
    for i, r in enumerate(retrieved[:k], start=1):
        if r in relevant:
            score += 1.0 / math.log2(i + 1)
    return score


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    dcg = dcg_at_k(retrieved, relevant, k)
    # Ideal DCG: all relevant items at the top
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0
