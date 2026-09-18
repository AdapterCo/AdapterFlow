# AdapterFlow — Instruções Permanentes

> **REGRA**: Este arquivo é a fonte permanente de regras e decisões arquiteturais do projeto.
> Antes de qualquer alteração no projeto, leia integralmente este arquivo.
> Nunca ignore, substitua ou contradiga este documento silenciosamente.

---

## Regras Fundamentais

### 1. Não Inventar Informações
- É PROIBIDO inserir dados falsos, fictícios, presumidos ou inventados.
- Produtos, preços, custos, estoque, SKUs, códigos, EAN, GTIN, marcas, categorias, dimensões, pesos, imagens, taxas, comissões, endpoints, tokens, credenciais — NADA pode ser inventado.
- Quando não houver dados: mostrar estado vazio.
- Informação ausente deve continuar ausente (NULL) até existir fonte confiável.

### 2. Dados Desconhecidos
- Nunca completar automaticamente informação desconhecida por suposição.
- Utilizar NULL no banco quando apropriado.
- Não inferir cor, peso, categoria ou qualquer dado a partir de suposição.

### 3. Frontend Não Deve Mentir
- Não mostrar "Conectado" sem conexão real.
- Não mostrar "Sincronizado" sem sincronização real.
- Não mostrar "Publicado" sem resposta real da API.
- Estados devem refletir o backend.

### 4. Não Inventar Implementação
- Se faltar informação: PARE. Não invente.
- Não criar endpoints, payloads, scopes, OAuth flows por suposição.
- Pesquisar documentação oficial antes de implementar.
- É melhor NOT_IMPLEMENTED do que integração falsa.

### 5. Credenciais e Segurança
- NUNCA salvar segredo no Git.
- NUNCA colocar token no frontend.
- NUNCA registrar access_token ou refresh_token em log.
- Utilizar .env para configuração sensível.
- PDF enviado é arquivo não confiável — validar adequadamente.

### 6. Dinheiro e Datas
- NUNCA utilizar float para valores monetários. Usar NUMERIC/Decimal.
- Timestamps com timezone (TIMESTAMPTZ, UTC).
- Arredondamento monetário explícito e testado.

### 7. Versionamento Git e Deploy
- Sempre que realizar um commit, executar obrigatoriamente `git push` imediatamente para o repositório remoto, garantindo sincronização instantânea com o ambiente de deploy/VPS.

---

## Decisões Arquiteturais

### Stack Tecnológico
| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript |
| UI | shadcn/ui + Tailwind CSS v4 |
| Backend | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| DB | PostgreSQL 16 |
| PDF | PyMuPDF (fitz) |
| Infra | Docker + Docker Compose |

### Estrutura do Projeto
```
AdapterFlow/
├── backend/          # FastAPI + Python
├── frontend/         # Next.js + TypeScript
├── docs/             # Documentação de integrações
├── docker-compose.yml
├── .env.example
├── instrucao.md      # Este arquivo
└── README.md
```

### Banco de Dados
- UUID como PK em todas as tabelas.
- Código do fornecedor NÃO é primary key.
- NUMERIC para valores monetários.
- TIMESTAMPTZ para datas.
- Soft delete com campo status quando aplicável.
- Constraint naming convention explícita.

### Modelos Fase 1
- suppliers
- products
- product_supplier_data
- supplier_product_prices
- product_images
- import_jobs
- import_items

### Identidade do Produto
- id = UUID interno
- sku = SKU interno (opcional)
- supplier_code = código do fornecedor (na tabela product_supplier_data)
- EAN/GTIN = campo separado
- ID do marketplace = futuro (marketplace_listings)

### Importação
- Arquitetura baseada em adapters: BaseCatalogImporter → LehmoxCatalogImporter
- PDF: texto nativo primeiro, OCR somente se necessário
- Preservar dados brutos (raw_data JSONB)
- Status: UPLOADED → PROCESSING → REVIEW_REQUIRED → IMPORTED / FAILED
- Nunca publicar automaticamente após importação

### Precificação (Fase 2 - Implementada)
- Motor matemático puro (`app.pricing.engine`) estritamente desacoplado de APIs externas.
- Utilização exclusiva de `Decimal` (Python) e `NUMERIC` (PostgreSQL) para cálculos centavo por centavo.
- Formação pelo Preço de Venda (Markup Divisor / Margem Líquida Real):
  `PV = (Custo Base + Custos Fixos + Taxas Fixas) / (1 - (Comissões + Impostos + Operacional + Margem Líquida))`
- Suporte a limiares dinâmicos de frete grátis e taxa fixa para produtos de baixo valor.
- Estratégias de arredondamento comercial: `ENDS_90`, `ENDS_99`, `ROUND_INTEGER`, `EXACT`.
- DRE Unitária detalhada persistida em JSONB e calculada em tempo real.
- Modelos: `PricingProfile` e `ProductChannelPrice`.

### Storage
- Abstração StorageService (put, get, delete, exists, get_url)
- Fase 1: filesystem local
- Futuro: S3-compatible

---

## Integrações

### Mercado Livre
STATUS: IMPLEMENTED (Fase 3)
Documentação oficial: https://developers.mercadolivre.com.br/
Última verificação: 2026-09-18
- OAuth 2.0 Authorization Code Flow com refresh automático de tokens (MLB).
- Predição inteligente de categorias via `/sites/MLB/domain_discovery/search`.
- Validação prévia de anúncios via `POST /items/validate`.
- Publicação de anúncios via `POST /items`.
- Modelos: `MarketplaceAccount` e `MarketplaceListing`.

### Shopee
STATUS: NOT_IMPLEMENTED
Documentação oficial: TODO: consultar documentação oficial
Última verificação: N/A

### Amazon
STATUS: NOT_IMPLEMENTED
Documentação oficial: TODO: consultar documentação oficial
Última verificação: N/A

### TikTok Shop
STATUS: NOT_IMPLEMENTED
Documentação oficial: TODO: consultar documentação oficial
Última verificação: N/A

---

## Fases do Projeto

| Fase | Descrição | Status |
|---|---|---|
| 1 | Infraestrutura, importação PDF, produtos, fornecedores | COMPLETED |
| 2 | Motor de precificação | COMPLETED |
| 3 | Mercado Livre | COMPLETED |
| 4 | Shopee | NOT_STARTED |
| 5 | Amazon | NOT_STARTED |
| 6 | TikTok Shop | NOT_STARTED |
| 7 | Estoque multicanal | NOT_STARTED |
| 8 | Pedidos | NOT_STARTED |
| 9 | Relatórios e análise financeira | NOT_STARTED |
| 10 | Automações e publicação em massa | NOT_STARTED |

---

## Convenções

### Backend
- Rotas sob `/api/v1/`
- Pydantic v2 para schemas (ConfigDict com from_attributes=True)
- Repositories para acesso a dados
- Services para lógica de negócio
- Dependency injection via FastAPI Depends

### Frontend
- App Router (Next.js 15)
- TanStack Query para data fetching client-side
- react-hook-form + zod para formulários
- Componentes shadcn/ui
- Páginas sem dados mostram estado vazio

### Commits
- Pequenos e coerentes
- Não misturar funcionalidades não relacionadas

---

## Histórico de Decisões

| Data | Decisão |
|---|---|
| 2026-09-17 | Projeto criado — Fase 1 iniciada |
| 2026-09-17 | Stack definida: FastAPI + Next.js 15 + PostgreSQL 16 + PyMuPDF |
| 2026-09-17 | PyMuPDF escolhido para extração de texto + imagens de PDF |
| 2026-09-17 | SQLAlchemy async com asyncpg como driver |
| 2026-09-17 | Migration inicial 001_initial_phase1 criada com 7 tabelas e DDL PostgreSQL validado |
| 2026-09-17 | Pytest suite com testes de normalização de preço, quantidade e sanitização de nomes passando |
| 2026-09-17 | Next.js 15 compilado com sucesso com todas as 15 rotas e componentes UI shadcn |
| 2026-09-17 | Fase 1 concluída com sucesso |
| 2026-09-18 | Validação com página real do catálogo LEHMOX: grid 3x3 calibrado, extração dos 9 produtos confirmada por testes automatizados (códigos, preços Unid.CX, quantidades PCS/CX, dimensões e cores) |
