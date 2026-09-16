"""Prometheus metric definitions.

These are module-level (created once) and shared across the app.
"""

from prometheus_client import Counter, Gauge, Histogram

# ---- Counters ----
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

RECOMMENDATION_COUNT = Counter(
    "recommendations_served_total",
    "Total recommendations returned",
)

CACHE_HIT = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISS = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)


# ---- Histograms ----
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

RETRIEVAL_LATENCY = Histogram(
    "retrieval_duration_seconds",
    "Retrieval pipeline latency in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


# ---- Gauges ----
INDEX_SIZE = Gauge(
    "index_size_products",
    "Number of products in the FAISS index",
)

ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Number of in-flight HTTP requests",
)
