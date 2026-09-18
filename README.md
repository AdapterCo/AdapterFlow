# AdapterFlow

Central de comércio multicanal para gerenciamento centralizado de produtos, precificação, estoque e publicação em marketplaces.

## Objetivo

Plataforma web que permite:
- Importar catálogos de fornecedores (PDF, CSV)
- Gerenciar produtos de forma centralizada
- Precificar com base em regras configuráveis
- Publicar em múltiplos marketplaces (Mercado Livre, Shopee, Amazon, TikTok Shop)
- Controlar estoque multicanal
- Gerenciar pedidos unificados

## Arquitetura

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│  Next.js 15  │     │   FastAPI    │     │     16       │
│  TypeScript  │     │   Python     │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, shadcn/ui, Tailwind CSS v4 |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic |
| Banco de Dados | PostgreSQL 16 |
| PDF Processing | PyMuPDF (fitz) |
| Infraestrutura | Docker, Docker Compose |

## Requisitos

- Docker e Docker Compose
- Node.js 22+ (para desenvolvimento frontend sem Docker)
- Python 3.12+ (para desenvolvimento backend sem Docker)
- PostgreSQL 16+ (incluído no Docker Compose)

## Instalação e Desenvolvimento

### Com Docker (recomendado)

```bash
# Clonar repositório
git clone <url> AdapterFlow
cd AdapterFlow

# Criar arquivo de ambiente
cp .env.example .env

# Subir todos os serviços
docker compose up --build

# Aplicar migrations
docker compose exec backend alembic upgrade head
```

Acesse:
- Frontend: http://localhost:3099
- Backend API: http://localhost:8000
- Swagger: http://localhost:8000/docs

### Sem Docker

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

pip install -r requirements.txt

# Configurar DATABASE_URL no .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha os valores:

```
DATABASE_URL=             # PostgreSQL connection string
STORAGE_PATH=             # Caminho para armazenamento de arquivos
BACKEND_CORS_ORIGINS=     # Origens permitidas para CORS
```

Consulte `.env.example` para a lista completa.

## Migrations

```bash
# Criar nova migration
cd backend
alembic revision --autogenerate -m "descricao"

# Aplicar migrations
alembic upgrade head

# Reverter última migration
alembic downgrade -1
```

## Testes

```bash
cd backend
python -m pytest tests/ -v
```

## Estrutura do Projeto

```
AdapterFlow/
├── backend/
│   ├── app/
│   │   ├── api/          # Rotas HTTP
│   │   ├── core/         # Configuração, banco de dados
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Schemas Pydantic
│   │   ├── services/     # Lógica de negócio
│   │   ├── repositories/ # Acesso a dados
│   │   ├── importers/    # Importadores de catálogo
│   │   └── storage/      # Abstração de armazenamento
│   ├── alembic/          # Migrations
│   └── tests/            # Testes automatizados
├── frontend/
│   └── src/
│       ├── app/          # Páginas (App Router)
│       ├── components/   # Componentes React
│       ├── lib/          # Utilitários
│       ├── hooks/        # Custom hooks
│       └── types/        # TypeScript types
├── docs/
│   └── integrations/     # Documentação de integrações
├── docker-compose.yml
├── instrucao.md          # Regras do projeto
└── README.md
```

## Status do Projeto

Consulte `instrucao.md` para o status atual de cada fase e integração.

## Regras

Consulte `instrucao.md` para as regras completas do projeto, incluindo:
- Proibição de dados fictícios
- Regras de segurança
- Convenções de código
- Decisões arquiteturais
