# Deployment Guide

How to deploy this service to production environments. Covers Google Cloud Run,
AWS ECS Fargate, and Railway, plus production patterns for secrets and managed
services.

**Current status:** The project runs locally via Docker Compose for development
and portfolio demonstrations. No production deployment is active — this guide
documents the deployment path for when it is needed.

---

## Platform Comparison

| Platform | Free tier | Best for |
|---|---|---|
| **Google Cloud Run** | 2M requests/month, scales to zero | Recommended — no idle cost |
| **Railway** | $5 free credit | Fastest setup |
| **Fly.io** | Limited free tier | Global edge deployment |
| **AWS ECS Fargate** | Pay per vCPU-second | Enterprise environments |
| **Self-hosted VPS** | ~$5/month | Full control |

---

## Google Cloud Run — Recommended

Cloud Run builds directly from the Dockerfile, scales to zero when idle, and
includes a generous free tier.

### Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated

### Deploy in one command

```bash
gcloud run deploy production-ml-service \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8000 \
  --set-env-vars LLM_BACKEND=mock,REDIS_ENABLED=false,LOG_JSON=true
```

Cloud Run automatically builds the Dockerfile, pushes to Artifact Registry,
deploys a container, and exposes a public HTTPS URL.

### External services

Cloud Run is stateless — MongoDB and Redis must be external:

- **MongoDB:** [MongoDB Atlas](https://www.mongodb.com/atlas) free tier (512 MB)
- **Redis:** [Upstash Redis](https://upstash.com/) free tier (10,000 commands/day)

Set their connection strings via Secret Manager:

```bash
gcloud run deploy production-ml-service \
  --source . \
  --set-secrets MONGO_URI=mongo-uri:latest,REDIS_URL=redis-url:latest,LLM_API_KEY=groq-key:latest \
  --set-env-vars LLM_BACKEND=openai_compatible,LLM_API_URL=https://api.groq.com/openai/v1,LLM_MODEL=openai/gpt-oss-20b
```

---

## Railway — Fastest Deploy

```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

Railway auto-detects the Dockerfile. The $5 free credit covers several months
of light usage.

---

## AWS ECS Fargate

Standard for AWS production environments.

```bash
# 1. Push image to ECR
aws ecr create-repository --repository-name production-ml-service
docker build -t production-ml-service .
docker tag production-ml-service:latest \
  <account>.dkr.ecr.<region>.amazonaws.com/production-ml-service:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/production-ml-service:latest

# 2. Create an ECS cluster + Fargate task definition
# 3. Configure ALB + target group on port 8000
# 4. Set task env vars via Parameter Store / Secrets Manager
```

Full walkthrough: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/

---

## Secrets Management

Never commit `.env`. Use platform-managed secrets:

| Platform | Mechanism |
|---|---|
| Cloud Run | Secret Manager + `--set-secrets` |
| ECS Fargate | AWS Secrets Manager |
| Railway | Dashboard environment variables |
| Fly.io | `fly secrets set KEY=value` |

For local Docker Compose, secrets are mounted as files (see
`secrets/grafana_admin_password.txt` referenced in `docker-compose.yml`).

---

## Production Checklist

Before deploying to any environment:

- [ ] `LLM_BACKEND=openai_compatible` with a real API key
- [ ] `MONGO_URI` points at a managed MongoDB (Atlas free tier)
- [ ] `REDIS_URL` points at a managed Redis (Upstash free tier)
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] `API_KEY_ENABLED=true` with a strong `API_KEY`
- [ ] `LOG_JSON=true`
- [ ] `CORS_ORIGINS` restricted to your frontend domain
- [ ] HTTPS terminated at the load balancer
- [ ] `/health` and `/ready` probes configured on the platform
- [ ] `/metrics` reachable by your Prometheus scraper

---

## Cost Notes

Running the service continuously requires MongoDB, Redis, and possibly LLM API
usage. For portfolio purposes, Cloud Run with scale-to-zero and Groq's free
tier keep costs at effectively zero.

For local demonstration, `docker compose up` runs the full system including
observability (Prometheus + Grafana) on a single machine.

---

## Why There Is No Live Deployment

This project is a portfolio demonstration, not a live service. Deployment is
documented rather than active because:

1. Continuous hosting costs money for a project with no users
2. The local Docker Compose stack mirrors the production architecture
3. The evaluation harness, CI pipeline, and observability stack demonstrate
   production readiness without a paid hosting bill