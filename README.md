# AdapterFlow

Catálogo de fornecedores, revisão de PDF, precificação Decimal e integração Mercado Livre. As regras obrigatórias estão em [instrucao.md](instrucao.md).

Implementado no código: adapter LEHMOX com texto nativo/OCR opcional, fila durável, revisão manual, catálogo, perfis de preço, OAuth e publicação controlada. Shopee, Amazon, TikTok, estoque, pedidos e relatórios continuam **não implementados**. Não há importador CSV. Código existente não comprova homologação em produção; consulte [correções e limites de validação](docs/correcoes-2026-09-19.md).

## Produção

Requisitos: Docker Compose, domínio HTTPS e Traefik configurado na rede externa `traefik9`. PostgreSQL 16 está incluído. O Compose não publica portas diretamente no host.

1. Copie `.env.example` para `.env` e preencha domínio, senha do PostgreSQL, usuário/senha administrativos e chave Fernet. Não use credenciais de exemplo. A senha PostgreSQL interpolada na URL deve usar caracteres seguros para URL.
2. Gere a chave localmente com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Guarde-a separadamente: perdê-la impede recuperar tokens cifrados.
3. Configure os três campos `MERCADOLIVRE_*` com dados reais da aplicação. A URI deve corresponder exatamente à cadastrada e terminar em `/marketplaces/callback`.
4. Faça backup consistente antes de atualizar uma instalação existente, conforme [operação](docs/operacao.md).
5. Execute `docker compose config --quiet` e `docker compose up -d --build`. O backend aplica Alembic antes de atender; o worker espera readiness. Acesse o domínio HTTPS e autentique-se no diálogo do navegador.

HTTP Basic protege um único operador, com HTTPS obrigatório em produção; não é RBAC multiusuário. API/frontend exigem as mesmas credenciais no servidor. Nenhuma publicação ou conexão externa ocorre na instalação.

## Desenvolvimento sem Docker

Use Python 3.12, Node.js 22 e PostgreSQL 16 local. Em `backend`, crie/ative o venv e execute `pip install -r requirements-dev.txt`. Configure `backend/.env` com `DATABASE_URL`, `STORAGE_PATH`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `TOKEN_ENCRYPTION_KEY` e `BACKEND_CORS_ORIGINS=["http://localhost:3099"]`. Crie o diretório de storage.

Em terminais separados dentro de backend:

```sh
alembic upgrade head
uvicorn app.main:app --reload --port 8000
python -m app.worker
```

Em `frontend/.env.local`, configure as mesmas credenciais, `APP_ORIGIN=http://localhost:3099` e `INTERNAL_BACKEND_URL=http://localhost:8000`. Execute `npm ci` e `npm run dev`. O navegador usa `/api/v1` no mesmo domínio. Alterar URL interna em produção exige novo build: rewrites são compiladas.

OCR exige `OCR_ENABLED=true`, Tesseract e idiomas `por`/`eng`. A imagem Docker os inclui. Desabilitado, PDFs sem texto falham explicitamente, sem dados inventados.

## Verificações

```sh
# backend
python -m pytest -q
ruff check app --select F
alembic upgrade head --sql
# frontend
npm run lint -- --max-warnings=0
npx tsc --noEmit --incremental false
npm run build
node scripts/smoke-auth.mjs
```

O teste de banco requer `TEST_DATABASE_URL` para banco de testes já migrado. Sem essa variável ele é explicitamente ignorado. A CI fornece PostgreSQL 16 e executa migrations e o teste. Dados sintéticos existem apenas em testes; não há seed de produtos, taxas ou estoque.

Contratos: após alterar schemas, execute `python -m app.export_openapi` em backend e `npx openapi-typescript ../docs/openapi.json -o types/api.generated.ts` em frontend. A CI verifica divergência; `types/index.ts` exporta aliases desses tipos gerados.

Veja [auditoria original](docs/auditoria-2026-09-19.md), [operação](docs/operacao.md) e [fontes oficiais](docs/mercadolivre-verificacao-2026-09-19.md).
