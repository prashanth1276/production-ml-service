# Production ML Service: Semantic Search with Evaluation and Observability

[![CI](https://github.com/prashanth1276/production-ml-service/actions/workflows/ci.yml/badge.svg)](https://github.com/prashanth1276/production-ml-service/actions)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A production-shaped ML service that serves semantic product recommendations via
FAISS vector search, with Redis caching, Prometheus metrics, structured logging,
and a rigorous evaluation harness.

---

## Overview

This project answers a question most teams shipping LLM-powered services can't:
**how do you know your retrieval is actually good, and how does it behave under load?**

It combines:

- **FastAPI** backend with three endpoints: recommendations, chat, description generation
- **FAISS + sentence-transformers** for semantic search over a product catalog
- **Redis** for embedding and query caching
- **MongoDB** for the product and user store
- **LLM backend** with a mock implementation for CI and Ollama support for real LLM-generated text
- **Prometheus** metrics exposed at `/metrics`
- **Structured JSON logging** for machine-parseable request traces
- **Docker Compose** stack for one-command startup
- **GitHub Actions CI** running tests, Docker image builds, and a Docker Compose smoke test on every push
- **An evaluation harness** measuring retrieval quality, latency, and cache effectiveness

---

## Evaluation Results

### Retrieval Quality (15 labeled queries)

| Config | NDCG@5 | Precision@5 | Recall@5 | MRR |
|---|---|---|---|---|
| **Baseline** (raw query) | **0.895** | 0.347 | **0.922** | **0.933** |
| User-context-augmented | 0.675 | 0.267 | 0.744 | 0.689 |

**Finding:** Naively appending user purchase history to the query *degrades* retrieval
(NDCG drops by 22 points). User context is not always relevant — a gated approach that
only injects context when the query semantically matches user interests is a natural
extension.

### Latency Profile (30 requests per endpoint)

| Endpoint | Mean | p50 | p95 | p99 |
|---|---|---|---|---|
| `/health` | 5.3 ms | 5.2 ms | 6.6 ms | 6.7 ms |
| `/api/recommendations` | 24.2 ms | 24.4 ms | 27.6 ms | 29.1 ms |
| `/api/conversation` | 30.2 ms | 28.4 ms | 34.9 ms | 35.6 ms |

**Note:** The `/conversation` endpoint uses a mock LLM for CI-ability.
Production with a real Ollama backend adds 200–500 ms per call.

### Cache Ablation

| Path | Mean latency | p95 latency |
|---|---|---|
| Cold (no cache) | 25.6 ms | 31.5 ms |
| Warm (Redis hit) | 6.0 ms | 7.9 ms |
| **Speedup** | **4.3×** | **4.0×** |

Cache hits are 4.3× faster than cold-path retrieval — the primary driver of
the service's response-time profile under sustained load.

---

## Architecture

```
                   ┌──────────────────┐
                   │     FastAPI      │
                   │   (app/main.py)  │
                   └────────┬─────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
   ┌────────────┐    ┌──────────────┐   ┌─────────────┐
   │ /api/      │    │ /api/        │   │ /api/       │
   │ recommend  │    │ conversation │   │ description │
   └─────┬──────┘    └──────┬───────┘   └──────┬──────┘
         │                  │                  │
         ▼                  ▼                  ▼
   ┌──────────────┐  ┌──────────────┐   ┌─────────────┐
   │ Recommendation│  │ Chatbot      │   │ LLM Client  │
   │ Engine        │  │ Engine       │   │ (mock/      │
   └──────┬────────┘  └──────┬───────┘   │  ollama)    │
          │                  │           └─────────────┘
          ▼                  ▼
   ┌──────────────┐    ┌──────────────┐
   │ FAISS +      │    │ LLM Client   │
   │ Sentence     │    │ (mock/ollama)│
   │ Transformers │    └──────────────┘
   └──────┬───────┘
          │
          ▼
   ┌────────────────────────────────────┐
    │ Redis (cache) │ MongoDB (store) │
    │               │ products + users│
   └────────────────────────────────────┘

              Prometheus
                  ▲
                  │
               /metrics
```

---

## Getting Started

### Prerequisites

- Docker Desktop (for the full stack), **or**
- Python 3.10 + MongoDB + Redis (for manual setup)

### Option A — Full stack via Docker Compose (recommended)

```bash
git clone https://github.com/prashanth1276/production-ml-service.git
cd production-ml-service

docker compose up --build
```

This starts five containers:

- **web** — FastAPI app at http://localhost:8000
- **mongo** — MongoDB at localhost:27017
- **redis** — Redis at localhost:6379
- **prometheus** — metrics scraper at http://localhost:9090
- **grafana** — dashboards at http://localhost:3000 (credentials configured via Docker secret)

Seed the MongoDB database with the product catalog and user data:

```bash
docker compose exec web python scripts/seed_db.py
```

Then check the app:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl "http://localhost:8000/api/recommendations?query=running+shoes&top_k=5"
```

### Option B — Run components manually

```bash
# Start backing services
docker run -d -p 27017:27017 --name retail-mongo mongo:7
docker run -d -p 6379:6379 --name retail-redis redis:7-alpine

# Set up Python environment
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Seed the database
python scripts/seed_db.py

# Run the server
uvicorn app.main:app --reload --port 8000
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Welcome message + version info |
| `GET` | `/health` | Liveness probe |
| `GET` | `/ready` | Readiness probe (checks MongoDB + Redis) |
| `GET` | `/metrics` | Prometheus metrics (text exposition format) |
| `GET` | `/api/recommendations?query=...&top_k=5` | Semantic product recommendations |
| `POST` | `/api/conversation` | Conversational shopping response (mock/real LLM) |
| `GET` | `/api/description?product_id=...` | AI-generated product description |

Interactive API docs available at `/docs` when the server is running.

---

## Evaluation Harness

Three standalone evaluation scripts live in `eval/`:

```bash
# Retrieval quality: NDCG@5, Precision@5, Recall@5, MRR
python -m eval.retrieval_eval

# Latency profiling: mean/p50/p95/p99 per endpoint
python -m eval.latency_eval

# Cache ablation: cold vs warm
python -m eval.cache_eval
```

Results are written to `results/` as CSV files.

---

## Test Results

```bash
docker compose exec web sh -c "PYTHONPATH=/app pytest -q"
```

12 tests covering:

- API routes (health, readiness, recommendations, chat, description)
- Recommendation engine (index building, top-k retrieval, empty catalog handling)
- Mock LLM backend (deterministic CI-friendly responses)

CI runs on every push via GitHub Actions.

---

## Design Decisions

**Why FAISS over a managed vector DB?**
FAISS runs in-process with no additional vector database service, simplifying local development and deployment. For production scale, this would be swapped
for Pinecone/Weaviate/Qdrant — the interface (`get_recommendations`) stays the same.

**Why a mock LLM backend?**
Deterministic tests and CI. The real Ollama backend is swapped in via the
`LLM_BACKEND` env var. This is a common pattern for keeping CI fast and
hermetic.

**Why CPU-only PyTorch?**
`sentence-transformers` uses PyTorch for embedding generation. Since this
project is designed to run on CPU, `requirements.txt` pins the CPU-only
PyTorch wheels to avoid unnecessary CUDA dependencies and reduce the
container footprint.

```text
torch==2.4.1+cpu
torchvision==0.19.1+cpu

**Why structured logging?**
`print()` statements don't scale. JSON logs are parseable by ELK/Datadog/etc.
and include a request ID for tracing across services.

**Why Prometheus over built-in metrics?**
Prometheus is the de-facto standard for cloud-native observability. The
`/metrics` endpoint exposes `http_requests_total`, `http_request_duration_seconds`,
`cache_hits_total`, `cache_misses_total`, and `index_size_products`.

---

## Repository Structure

```
production-ml-service/
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── README.md
├── requirements.txt
├── ruff.toml
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── app/
│   ├── main.py
│   ├── routes/
│   │   ├── chat.py
│   │   ├── describe.py
│   │   └── recommend.py
│   ├── services/
│   │   ├── chatbot_engine.py
│   │   ├── genai_writer.py
│   │   └── rec_engine.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_rec_engine.py
│   │   └── test_routes.py
│   └── utils/
│       ├── cache.py
│       ├── config.py
│       ├── db.py
│       ├── llm_client.py
│       ├── logging_config.py
│       ├── metrics.py
│       ├── products.json
│       └── users.json
│
├── eval/
│   ├── cache_eval.py
│   ├── latency_eval.py
│   ├── metrics.py
│   ├── retrieval_eval.py
│   └── test_queries.py
│
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       ├── dashboards/
│       │   └── main.json
│       └── provisioning/
│           ├── dashboards/
│           │   └── dashboard.yml
│           └── datasources/
│               └── prometheus.yml
│
├── results/
│
├── scripts/
│   └── seed_db.py
│
└── secrets/
    └── grafana_admin_password.txt  # local secret, not committed

```

---

## Limitations

- **Small catalog:** 55 products, 53 users. A larger production catalog would likely require a more scalable indexing and retrieval architecture.
- **Mock LLM in CI:** The evaluation harness uses a mock LLM. Real LLM latency
  is 200–500 ms per call, which would shift the `/conversation` latency profile.
- **No auth:** MongoDB runs without authentication in local dev. Production
  would require MongoDB auth + IP allowlisting.
- **No GPU acceleration:** All models run on CPU. GPU inference could reduce embedding/retrieval latency for larger workloads.
- **Single-node Redis:** No clustering or persistence configuration. Redis
  is used as a pure cache, so a restart clears it.

---

## Future Work

- **Gated user-context injection:** Only augment the query with user history
  when the query semantically matches user preferences. Based on the retrieval
  eval finding (context degrades NDCG by 22 points).
- **Real LLM integration:** Deploy Ollama in the Docker Compose stack for
  end-to-end LLM evaluation.
- **Auth + rate limiting per user:** Currently rate limiting is per-IP via
  `fastapi-limiter`. Production would use API keys or JWT.
- **Load testing:** Integrate Locust to measure throughput under sustained load.

---

## License

MIT