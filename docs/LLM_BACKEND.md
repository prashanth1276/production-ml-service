# LLM Backend Options

The service is backend-agnostic. Any server implementing the OpenAI
`/v1/chat/completions` API works without code changes.

---

## Supported Configurations

| Mode | Config | Resources | Use case |
|---|---|---|---|
| **Mock** | `LLM_BACKEND=mock` | None | CI, tests, offline development |
| **Groq cloud** | `openai_compatible` + Groq URL | None local | Real responses, free tier |
| **Self-hosted CPU** | `openai_compatible` + llama.cpp | ~1 GB RAM | Local inference |
| **Self-hosted GPU** | `openai_compatible` + llama.cpp CUDA | ~1.5 GB VRAM | Best local latency |
| **Self-hosted GPU (large)** | `openai_compatible` + vLLM | 12+ GB VRAM | Production GPU serving |

---

## 1. Mock (default)

Zero setup. Deterministic responses for tests and CI.

```env
LLM_BACKEND=mock
```

Used automatically by GitHub Actions.

---

## 2. Groq Cloud (free, verified)

Real LLM responses with zero local resources. Free tier, no credit card.
Verified end-to-end with `openai/gpt-oss-20b`.

```bash
# 1. Get a key from https://console.groq.com/keys
# 2. Set in .env:
LLM_BACKEND=openai_compatible
LLM_API_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
LLM_API_KEY=gsk_your_key_here
```

Test:

```bash
curl -X POST http://localhost:8000/api/conversation \
  -H "Content-Type: application/json" \
  -d '{"message":"recommend running shoes under 1000"}'
```

Expected latency: 200–500 ms.

To check currently available models at any time:

```bash
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY"
```

---

## 3. Self-hosted: llama.cpp (CPU or small GPU)

Best-in-class CPU throughput. Runs on laptops without a dedicated GPU.
Optionally offloads layers to an NVIDIA GPU via `--n-gpu-layers`.

**Model:** `Qwen2.5-1.5B-Instruct-Q4_K_M` (~1 GB GGUF, no HuggingFace token required).

Set in `.env`:

```env
LLM_BACKEND=openai_compatible
LLM_API_URL=http://llamacpp:8080/v1
LLM_MODEL=qwen2.5-1.5b-instruct
```

**Hardware notes:**

- CPU only: ~1 GB RAM, 5–15 tokens/s
- 4 GB GPU (e.g. GTX 1650): full layer offload, 20–40 tokens/s
- If VRAM is tight, set `LLAMA_ARG_N_GPU_LAYERS=10` for partial offload

---

## 4. Self-hosted: vLLM (production GPU)

Industry standard for high-throughput GPU serving. Requires 12+ GB VRAM for
models up to 7B; 24+ GB for 13B+.

**Not viable on consumer laptops**, but documented for architectural
completeness.

Reference config:

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "8001:8000"
    volumes:
      - vllm_cache:/root/.cache/huggingface
    command:
      - "--model"
      - "meta-llama/Llama-3.1-8B-Instruct"
      - "--dtype"
      - "auto"
      - "--max-model-len"
      - "8192"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

Set in `.env`:

```env
LLM_BACKEND=openai_compatible
LLM_API_URL=http://vllm:8000/v1
LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

---

## Choosing a Backend

```
                                 ┌─────────────────────┐
                                 │ Do you have a GPU?  │
                                 └──────────┬──────────┘
                                            │
              ┌─────────────────────────────┼───────────────────────────┐
              │                             │                           │
              ▼                             ▼                           ▼
    ┌──────────────────┐         ┌──────────────────┐        ┌──────────────────┐
    │ 12+ GB VRAM GPU  │         │ 4–8 GB VRAM GPU  │        │ No GPU / CPU     │
    └────────┬─────────┘         └────────┬─────────┘        └────────┬─────────┘
             │                            │                           │
             ▼                            ▼                           ▼
    ┌──────────────────┐         ┌──────────────────┐        ┌──────────────────┐
    │ Self-hosted vLLM │         │ llama.cpp + GPU  │        │ Groq cloud or    │
    │  (highest QPS)   │         │  (best for edge) │        │ llama.cpp CPU    │
    └──────────────────┘         └──────────────────┘        └──────────────────┘
```

---

## Interface Contract

Every backend implements the OpenAI `/v1/chat/completions` API:

- **Request:** `POST` with `{model, messages, max_tokens, temperature}`
- **Response:** `{choices: [{message: {content: "..."}}]}`

The application's `OpenAICompatibleClient` (`app/utils/llm_client.py`) sends
this payload. Any server implementing the spec works — vLLM, llama.cpp,
Ollama's OpenAI shim, OpenAI, Together, Groq, Anyscale, etc.

**No code changes are required when switching backends.**

---

## A Note on Model Churn

Cloud LLM providers regularly deprecate models. When this project was first
built, Groq's `llama-3.1-8b-instant` was the recommended free-tier model. It
has since been retired; `openai/gpt-oss-20b` is the current replacement.

The client code did not change — only a `.env` value. This is why `LLM_MODEL`
exists as a separate config: model swaps are a configuration concern, not a
deployment one.

---

## Testing a Backend

```bash
# 1. Set env vars in .env
# 2. Recreate the web container
docker compose up -d web

# 3. Check the app picked up the backend
curl http://localhost:8000/
# Expected: {"llm_backend":"openai_compatible", ...}

# 4. Exercise the LLM
curl -X POST http://localhost:8000/api/conversation \
  -H "Content-Type: application/json" \
  -d '{"message":"recommend a warm jacket"}'
```