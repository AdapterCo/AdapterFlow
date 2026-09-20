# Correções aplicadas — 19/09/2026, atualizadas em 20/09/2026

`instrucao.md` foi lido integralmente e preservado. Este registro complementa a auditoria original: não redefine suas regras nem converte código existente em alegação de homologação.

## Rastreamento dos 56 achados

| Achados | Alterações no código | Limite do aceite |
|---|---|---|
| 01–06 | Persistência correta de ImportItem; PATCH tipado em JSONB; preservação de extração/NULL; vínculo ao job; locks; confirmação transacional, idempotente e bloqueada por pendências | Testes locais de contratos; transação real incluída no teste PostgreSQL da CI, não executada nesta estação |
| 07–10 | Identidade por fornecedor/código; SKU interno opcional; ausência preservada; Decimal; removida inferência de esgotado por proporção da imagem | Registros legados não são desmembrados por suposição |
| 11–15 | Adapter explícito com confirmação de layout; OCR opcional; raw/page/bbox preservados; ocorrências de imagem; vizinho espacial correto; preço negativo não vira positivo | OCR depende de Tesseract; testes locais não comprovam todos os layouts do catálogo |
| 16–19 | Fonte UUID imutável; hash; validação de tamanho/assinatura/páginas/criptografia; subprocesso com timeout; fila durável e recuperação de jobs abandonados; UTC | Worker/limites Docker adicionados; infraestrutura não executada localmente |
| 20–23 | Imagens autenticadas e vinculadas; fornecedor/custo/histórico nos contratos; edição do produto; revisão explícita do vínculo do fornecedor com motivo; preços invalidados | Não há reativação presumida por ausência de carimbo |
| 24–30 | Enumeração de faixas; DRE conferida após arredondamento; rejeição de float/nonfinite; schemas validados; NUMERIC ampliado; origem explícita do custo; obsolescência; formulários sem taxas inventadas | Perfis legados exigem revisão; taxas de mercado não são buscadas automaticamente |
| 31–34 | Autenticação servidor/frontend, checagem de origem; OAuth state aleatório, expirável e de uso único; erros sanitizados; paths por descendência real | Autenticação de operador único; não implementa RBAC |
| 35–39 | Estado externo preservado; conexão verificada; perfil/canal/fonte coerentes; quantidade/condição explícitas; produto ativo; imagens reais e atributos de categoria | OAuth, categorias e publicação reais precisam de homologação com credenciais válidas |
| 40–44 | Tentativa persistida antes do POST; chave de requisição; bloqueio de duplicação; UNKNOWN reconciliável por ID real; refresh serializado; erro de categoria visível; desconexão preserva histórico; título não reseta | Ausência de anúncio após resultado incerto exige investigação; não há retry cego |
| 45–49 | Mutations aguardadas; quantidade real confirmada; erro distinto de vazio; paginação de listas; módulos futuros honestos; limpar código salva NULL | Teste visual completo/teclado ainda não realizado |
| 50–54 | Next.js 15.5.25; variáveis ML no Compose; worker/healthcheck; setup corrigido; CI; regressões; documentação com limites explícitos | CI configurada, não executada remotamente; nenhum deploy foi realizado |
| 55 | CHECKs de estado/custo, índices, precisão, nome de constraint alinhado, locks de defaults/upsert e soft delete de perfis | Parcial: CHECKs legadas NOT VALID; padrões antigos duplicados exigem escolha humana; comparação autogenerate com banco real ainda pendente |
| 56 | RHF/zod em perfis, publicação, revisão, catálogo, cálculo, seleção de importação e reconciliação; storage materializado por interface pública | Estado local permanece apenas nos controles de interface, como paginação, abertura de diálogo e seleção de arquivo |

## Melhorias adicionais da auditoria

Aplicadas: tokens Fernet e utilitário de proteção dos legados; remoção de senha padrão; backend sem root; exclusões de venv/cache/segredos do build; versões diretas Python fixadas e lock npm; readiness e worker limitado; documentação de backup/restauração; índices de FKs/status; remoção de user_info persistido na reconexão; pool HTTP compartilhado com retry/backoff somente para GET; tipos TypeScript derivados do OpenAPI com verificação na CI; limpeza das imagens de extração que falhou.

Parciais ou dependentes do ambiente: dependências transitivas Python ainda não têm lock com hashes; logs classificados não substituem métricas/alertas/trilha completa de auditoria; não houve medição de performance ou ensaio de restauração; acessibilidade não passou por auditoria interativa; retenção/expurgo não foi presumida sem política definida. Esses pontos não são apresentados como concluídos.

## Evidências locais

- Backend: 56 testes aprovados; teste PostgreSQL ignorado explicitamente por ausência de TEST_DATABASE_URL. Suíte inclui casos reais de preço da auditoria, estado OAuth inválido, token cifrado, paths, extração inválida, confirmação e estados PAUSED/UNKNOWN do cliente mockado. Nesta estação, uma página do PDF real também passou pelo subprocesso isolado, preservando página/bbox e identificação de esgotados.
- Ruff: verificação F sem erros.
- TypeScript: compilação sem erros.
- ESLint: zero erros/avisos na última verificação completa.
- Build Next.js 15: passou; fontes não dependem mais de download no build.
- Smoke HTTP do frontend: quatro verificações aprovadas (sem credenciais, credenciais inválidas, acesso autenticado e origem de escrita proibida).
- Alembic: geração de SQL 001→004 aprovada; execução em PostgreSQL não foi feita.
- YAML de Compose/CI interpretado com sucesso (não equivale a executar Docker Compose).
- Docker/PostgreSQL locais não encontrados. Nenhuma credencial real foi utilizada para OAuth/publicação. Nenhum dado de produção foi migrado, publicado ou corrigido automaticamente.

Veja [operação](operacao.md) para aplicar migrations/worker, proteger tokens legados e revisar registros ambíguos. O documento original de instruções continua inalterado. A validação na VPS será realizada pelo responsável pelo ambiente após receber estas alterações pelo repositório; os testes desta sessão não incluem deploy.
