---
name: restart-servers
description: >-
  Reinicia de forma segura o uvicorn (FastAPI) e o ngrok no bot_orcamento:
  mata todos os processos Python/uvicorn na porta 8000 e o ngrok antes de
  subir uma única instância nova. Use quando o usuário pedir para reiniciar
  os servidores, restart server, restart uvicorn/ngrok, ou quando houver
  conflito de porta 8000 / webhook sem resposta por processo duplicado.
---

# Restart Servers (bot_orcamento)

## Quando aplicar

Sempre que o usuário pedir para **reiniciar os servidores** (ou equivalente).
Nunca apenas “subir de novo” sem matar o que já está rodando.

## Problema que esta skill evita

No Windows, vários `uvicorn` (especialmente com `--reload`) competem pela
porta **8000**. O webhook da Meta pode receber 200 sem processar/enviar
resposta. Sempre deve existir **no máximo um** processo ouvindo a 8000.

## Procedimento obrigatório

Execute na raiz do repo (`bot_orcamento`), com permissões totais no shell.

### 1. Matar processos antigos

Rode o script (preferencial):

```powershell
powershell -ExecutionPolicy Bypass -File .cursor/skills/restart-servers/scripts/stop-servers.ps1
```

Ou, se o script falhar, faça manualmente:

1. Mate todo `python.exe` cuja `CommandLine` contenha `uvicorn` **ou** `multiprocessing` ligado ao app.
2. Mate o que estiver em **Listen** na porta `8000` (`OwningProcess`).
3. Mate processos `ngrok`.
4. Aguarde 2–3s e confirme que a porta **8000 está livre**.

**Não prossiga** enquanto ainda houver listener na 8000.

### 2. Subir uvicorn (uma instância, sem reload)

```powershell
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Regras:

- **Sem** `--reload` (no Windows o reload deixa processos órfãos e quebra jobs em background).
- Rode em **background** (`block_until_ms: 0`).
- Espere o log `Application startup complete` **e** confirme que **não** apareceu `WinError 10048` / bind na 8000.
- Se der erro de porta em uso → volte ao passo 1.

### 3. Subir ngrok

```powershell
ngrok http 8000
```

Também em background. Confirme a URL pública via:

```powershell
(Invoke-RestMethod http://127.0.0.1:4040/api/tunnels).tunnels[0].public_url
```

### 4. Validar

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Garanta **um único** listener na 8000 e um único `uvicorn` ativo.

### 5. Responder ao usuário

Informe de forma curta:

- Health ok (ou falha)
- URL do ngrok
- Webhook da Meta para atualizar: `{ngrok_url}/webhook`

## Checklist rápido

```
- [ ] Porta 8000 livre
- [ ] Nenhum uvicorn/ngrok antigo
- [ ] Um uvicorn sem --reload
- [ ] Um ngrok
- [ ] /health ok
- [ ] URL do webhook passada ao usuário
```

## O que NÃO fazer

- Não iniciar outro uvicorn “por cima” do atual.
- Não usar `--reload` ao reiniciar servidores neste projeto.
- Não assumir que a URL do ngrok é a mesma — sempre ler a URL nova.
- Não deixar dois reloaders (`python -m uvicorn ... --reload`) ao mesmo tempo.
