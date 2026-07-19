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
Dockerfile                # imagem de produção (Render)
render.yaml               # Blueprint Render (web + Redis)
.env.example              # variáveis necessárias (sem segredos)
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

## Deploy na Render (preparado)

Arquivos: `Dockerfile`, `render.yaml`, `.env.example`.

### Passo a passo

1. Suba o código no GitHub (branch `main`).
2. No [Render Dashboard](https://dashboard.render.com): **New → Blueprint** e selecione o repositório (lê `render.yaml`).
3. Preencha os secrets marcados `sync: false` (iguais ao `.env` local):
   - `VERIFY_TOKEN`, `META_WA_TOKEN`, `WA_PHONE_NUMBER_ID`, `META_APP_SECRET`
   - `SUPABASE_URL`, `SUPABASE_KEY`
   - `GEMINI_API_KEY`, `GLADIA_API_KEY`
4. Aguarde o deploy. Health: `GET https://<servico>.onrender.com/health`
5. Na Meta (WhatsApp Cloud API), webhook:
   - Callback URL: `https://<servico>.onrender.com/webhook`
   - Verify token: o mesmo de `VERIFY_TOKEN`
6. Em produção, mantenha `REQUIRE_WEBHOOK_SIGNATURE=true` (já no blueprint).

### Observações

- O blueprint usa plano **starter** (evita cold start do free, importante para webhook Meta).
- Redis vem do Key Value (`REDIS_URL` injetado automaticamente).
- Não faça commit de `.env`.
- Seed do catálogo: rode uma vez apontando para o mesmo Supabase (`scripts/seed_catalog.py`).

### Teste local da imagem

```bash
docker build -t bot-orcamento .
docker run --rm -p 8000:8000 --env-file .env -e REDIS_URL=redis://host.docker.internal:6379/0 bot-orcamento
```

## Subir Redis (local)

```bash
docker compose up -d redis
```

## Rodar API (local)

Use a skill `restart-servers` (mata processos e sobe **sem** `--reload`):

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
