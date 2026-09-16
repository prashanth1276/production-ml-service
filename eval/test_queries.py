"""Labeled test queries for retrieval evaluation.

Each query has one or more relevant product IDs (ground truth).
Relevance was assigned by matching category + product semantics.
This is the same structure used in standard IR benchmarks
(BEIR, MS MARCO), just at smaller scale.
"""

TEST_QUERIES = [
    # --- Query, list of relevant product IDs ---
    {
        "query": "running shoes for sports",
        "relevant": ["prod004", "prod032", "prod052"],
        "category": "footwear",
    },
    {
        "query": "cheap casual t-shirt under 500",
        "relevant": ["prod001", "prod021"],
        "category": "clothing",
    },
    {
        "query": "formal office shirt",
        "relevant": ["prod008"],
        "category": "clothing",
    },
    {
        "query": "wireless headphones with noise cancellation",
        "relevant": ["prod006", "prod029"],
        "category": "electronics",
    },
    {
        "query": "water bottle for travel",
        "relevant": ["prod007", "prod033"],
        "category": "home",
    },
    {
        "query": "leather wallet or belt",
        "relevant": ["prod005", "prod023"],
        "category": "accessories",
    },
    {
        "query": "laptop backpack",
        "relevant": ["prod010", "prod033"],
        "category": "accessories",
    },
    {
        "query": "winter jacket warm",
        "relevant": ["prod003", "prod031", "prod046"],
        "category": "clothing",
    },
    {
        "query": "smart home device",
        "relevant": ["prod034", "prod044"],
        "category": "electronics",
    },
    {
        "query": "gaming gear",
        "relevant": ["prod029", "prod024", "prod049"],
        "category": "electronics",
    },
    {
        "query": "fitness tracker or smartwatch",
        "relevant": ["prod049"],
        "category": "electronics",
    },
    {
        "query": "cozy indoor footwear",
        "relevant": ["prod047", "prod027"],
        "category": "footwear",
    },
    {
        "query": "gift for coffee lover",
        "relevant": ["prod025", "prod035"],
        "category": "home",
    },
    {
        "query": "reading lamp for desk",
        "relevant": ["prod017"],
        "category": "home",
    },
    {
        "query": "running shorts",
        "relevant": ["prod019"],
        "category": "clothing",
    },
]
