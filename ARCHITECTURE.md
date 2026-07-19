# Bot Orçamento — Arquitetura

```text
app/
  main.py                 # Application factory FastAPI
  api/routes/             # HTTP (webhook fino, health)
  core/                   # Config e segurança
  domain/                 # Regras de negócio (conversa, materiais)
  infrastructure/         # Redis/store, messaging, retry
  jobs/                   # Processamento assíncrono
  services/               # Adaptadores de APIs externas (legado modularizado)
```

## Sprint 1

- Webhook responde `200` imediatamente e processa em `BackgroundTasks`
- Estado (dedupe + sessão) em Redis, com fallback em memória
- Validação opcional de `X-Hub-Signature-256` via `META_APP_SECRET`
- Retries com backoff no download/transcrição
- Health check em `GET /health`

## Subir Redis

```bash
docker compose up -d redis
```

## Rodar API

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
