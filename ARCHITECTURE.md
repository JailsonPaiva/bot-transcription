# Bot Orçamento — Arquitetura

```text
app/
  main.py                 # Application factory FastAPI
  api/routes/             # HTTP (webhook fino, health)
  core/                   # Config e segurança
  domain/                 # Regras de negócio (conversa, materiais, catálogo)
  infrastructure/         # Redis/store, messaging, retry, budgets
  jobs/                   # Processamento assíncrono
  services/               # Adaptadores de APIs externas
supabase/migrations/      # SQL do catálogo e histórico
scripts/                  # utilitários (seed do catálogo)
tests/                    # testes unitários (edição de lista, LGPD)
```

## Sprint 1

- Webhook responde `200` imediatamente e processa em background
- Estado (dedupe + sessão) em Redis, com fallback em memória
- Validação opcional de `X-Hub-Signature-256` via `META_APP_SECRET`
- Retries com backoff no download/transcrição
- Health check em `GET /health`

## Sprint 2

- Tabelas `materials` e `budgets` (SQL em `supabase/migrations`)
- Catálogo carregado do Supabase (cache 5 min) com fallback para seed
- PDF com preço unitário, total por item e total geral
- Histórico de orçamentos + comando WhatsApp `último orçamento`

### Setup catálogo

1. Rode o SQL: `supabase/migrations/001_materials_budgets.sql`
2. Seed:

```bash
python scripts/seed_catalog.py --overwrite-prices
```

## Sprint 3

- ACK imediato ao usuário assim que a mensagem é reivindicada (após o webhook 200)
- Edição da lista antes do PDF:
  - `remove N` / `tira cimento`
  - `qtd N=X` / `muda N para X`
  - `adiciona …`
  - `lista`
- LGPD mínima: `privacidade` e `apagar meus dados` (limpa sessão Redis + histórico `budgets`)
- Rate limit de áudio por `wa_id` (já na Sprint 1; mantido)

## Subir Redis

```bash
docker compose up -d redis
```

## Rodar API

Use a skill `restart-servers` (mata processos e sobe **sem** `--reload`):

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
