# Auditoria do AdapterFlow — 19/09/2026

## Conclusão

O projeto **não cumpre integralmente `instrucao.md`**. A estrutura arquitetural existe, mas os status `COMPLETED` das fases 1, 2 e 3 não são sustentados pelos fluxos atuais: há bloqueadores na importação e revisão, cálculos incorretos em faixas de precificação, contratos incompatíveis entre API e telas e problemas de segurança/publicação.

Este relatório contém **56 achados**, separados de melhorias adicionais. Não significa que todos os defeitos possíveis foram descobertos: é uma auditoria do checkout local, com inspeção de código e verificações executáveis. Não houve alteração de código funcional, migração de banco, publicação em marketplace, commit ou push.

**Prioridades:** P0 = bloqueador de exposição em produção; P1 = corrigir antes de uso operacional; P2 = corrigir no ciclo seguinte; P3 = manutenção/documentação. A prioridade de exposição considera o deploy público configurado no Compose; não foi verificado se a VPS possui proteção externa adicional.

## Verificações executadas e limites

| Verificação | Resultado |
|---|---|
| Leitura integral de `instrucao.md` | Concluída; usada como referência normativa |
| Inspeção de backend, frontend, schemas, repositories, migrations, Docker e testes | Concluída para os fluxos descritos neste relatório |
| `backend/venv/Scripts/python.exe -m pytest tests -q` | **23 passaram**, 1 aviso de depreciação |
| `npm run lint` | **Falhou: 20 erros e 20 avisos** |
| `npx tsc --noEmit --incremental false` | Passou |
| `npm run build` | Passou; compilou Next.js **16.3.5** |
| `python -m alembic heads` | Uma cabeça: `003_mercadolivre_integration` |
| Reprodução de edição de item via compilação SQLAlchemy | `CompileError: Unconsumed column names: normalized_code` |
| Reprodução matemática de taxas/frete | Três inconsistências demonstradas abaixo |
| Reprodução de normalização e identificação de esgotado | Sinal negativo perdido; imagem arbitrária marcada esgotada |
| Validação de confinamento do storage no Windows | Caminho absoluto em diretório irmão com mesmo prefixo aceito |

Não executei migrations contra um PostgreSQL real, não testei a VPS, não usei credenciais de marketplace e não publiquei anúncios. Docker não estava disponível como comando neste ambiente. A compilação do frontend não verifica a compatibilidade real de seus tipos com as respostas HTTP.

Tentei consultar os guias oficiais de [autenticação](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao) e [publicação](https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos), mas ambos retornaram HTTP 403 nesta sessão. Portanto, **não certifico a conformidade atual dos payloads/endpoints com a API externa**. As falhas de integração abaixo são demonstráveis pelo código local; requisitos externos específicos devem ser reconferidos na documentação oficial antes de implementação.

Os valores usados nas reproduções são entradas isoladas de teste, não dados comerciais inseridos no projeto.

## Comparação com `instrucao.md`

| Regra/decisão | Situação observada |
|---|---|
| Não inventar informações; ausências em NULL | **Violada:** taxas/custos predefinidos sem fonte, `UNKNOWN`, `Unnamed Product`, estoque inicial e condição presumidos |
| Não inferir dados desconhecidos | **Violada:** estado esgotado inferido apenas pela proporção/tamanho de imagem |
| Frontend refletir a realidade do backend/API | **Violada:** aprovação antecipada, conexão baseada em flag local, publicação sempre `ACTIVE`, erros apresentados como ausência |
| Dinheiro exclusivamente Decimal/NUMERIC | **Parcial:** banco usa NUMERIC e motor usa Decimal internamente; importação/publicação usam float e a DRE no frontend faz somas com Number |
| UTC com timezone | **Parcial:** colunas têm timezone; serviço de importação cria datetime ingênuo com `utcnow()` |
| Next.js 15 | **Violada:** manifesto, instalação e build usam 16.3.5 |
| Python 3.12, FastAPI, SQLAlchemy async, Alembic, PostgreSQL 16 | Estrutura compatível; Docker declara Python 3.12 e PostgreSQL 16 |
| UUID como PK; código do fornecedor separado | PKs UUID presentes; **identidade lógica incorreta**, pois código do fornecedor vira SKU global |
| BaseCatalogImporter → LehmoxCatalogImporter | Herança presente; seleção do adapter é fixa para qualquer fornecedor |
| Texto nativo e OCR quando necessário | Texto nativo presente; **fallback OCR ausente** |
| Preservação de raw_data JSONB | JSONB presente, mas campos são truncados e página/bbox não são persistidos |
| Fluxo UPLOADED → PROCESSING → REVIEW_REQUIRED → IMPORTED/FAILED | Strings presentes; **transições não são protegidas** |
| Nunca publicar automaticamente após importação | Atendido: publicação é fluxo separado |
| StorageService put/get/delete/exists/get_url | Métodos presentes; URL gerada não corresponde a rota e serviço depende de método privado de filesystem |
| Repositories, Services e Depends | Camadas presentes; commits dispersos impedem unidade transacional de negócio |
| TanStack Query | Presente |
| react-hook-form + zod nos formulários | Parcial: aplicado em fornecedores, ausente nos principais formulários novos |
| Shopee/Amazon/TikTok NOT_IMPLEMENTED | Corretamente não conectados; não classifiquei falta dessas integrações como bug |
| Fases futuras NOT_STARTED | Aceitável não implementá-las; suas URLs não deveriam renderizar precificação |
| Segredos fora do Git/frontend | Não encontrei `.env` real rastreado nem tokens nos schemas públicos; existem senha de desenvolvimento predefinida e risco de vazamento por exceções |
| Commit seguido imediatamente de push | Não aplicável: nenhum commit realizado; não é possível inferir cumprimento histórico só pelo código |

## Achados: importação, catálogo e dados

### 01 — P1 — Importação com produtos falha por símbolo ausente

**Evidência:** [import_service.py:118](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:118) instancia `ImportItem`, mas o módulo não importa nem define essa classe. A inspeção em execução confirmou `hasattr(module, 'ImportItem') == False`.

**Impacto:** ao chegar ao primeiro lote não vazio, a extração gera `NameError`, sofre rollback e tenta marcar o job como `FAILED`. Corrigir o import e testar o fluxo upload → extração → persistência; testes só do parser não detectam esse bloqueador.

### 02 — P1 — Salvar código/preço/cor na revisão gera erro de SQL

**Evidência:** [imports.py:100](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/imports.py:100) repassa `normalized_code`, `normalized_price` e `normalized_color` diretamente ao UPDATE; [import_repository.py:65](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/repositories/import_repository.py:65) os trata como colunas. Eles são chaves de JSONB, não colunas de `ImportItem`.

**Reprodução:** compilar `update(ImportItem).values(normalized_code=...)` retorna `CompileError`. O frontend fecha a edição sem aguardar sucesso. Mapear alterações para JSONB, validar Decimal e exibir sucesso somente após persistência.

### 03 — P1 — Um job consegue alterar/importar itens de outro job

**Evidência:** [imports.py:92](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/imports.py:92) recebe `id`, mas atualiza apenas por `item_id`; [import_service.py:163](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:163) aceita IDs explícitos sem verificar `item.import_id == job.id`.

**Impacto:** confirmação pode cadastrar item de outro catálogo no fornecedor do job atual; rejeições também atravessam jobs. Filtrar pela relação pai/filho, rejeitar IDs estrangeiros e impedir sobreposição entre listas aprovadas/rejeitadas.

### 04 — P1 — Confirmação não é atômica nem protegida contra concorrência

**Evidência:** [product_repository.py:12](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/repositories/product_repository.py:12) faz commit ao criar produto; [import_repository.py:66](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/repositories/import_repository.py:66) faz commit por item. O serviço percorre itens sem lock nem chave de operação.

**Impacto:** falha no meio deixa produtos/itens parcialmente persistidos, contador incompleto e risco de duplicação em confirmações simultâneas. A condição `status != IMPORTED` não elimina corrida entre duas transações. Centralizar a transação e definir idempotência/controle de concorrência.

### 05 — P1 — Confirmação pode encerrar importação incompleta

**Evidência:** [import_service.py:151](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:151): se existir algum `APPROVED`, importa só os aprovados; depois sempre grava `IMPORTED`. Não exige job em `REVIEW_REQUIRED`. Status enviados por PATCH são strings livres.

**Impacto:** uma aprovação entre vários detectados pode encerrar o job deixando os outros pendentes e a tela somente leitura. Também é possível confirmar job ainda processando, marcar estados arbitrários ou rejeitar item já importado. Implementar máquina de estados, validação dos itens e resultado explícito de confirmação parcial.

### 06 — P1 — Edição parcial substitui todos os dados extraídos

**Evidência:** [product_service.py:14](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/product_service.py:14) usa `user_edits or normalized_data`, sem mesclar os dicionários.

**Impacto:** editar só um campo via API faz desaparecer nome, código, preço e estado esgotado na criação do produto, acionando inclusive valores inventados. Aplicar merge por campo, diferenciando omissão de NULL explícito; os campos calculados da resposta também precisam refletir o valor efetivo revisado.

### 07 — P1 — Código do fornecedor é usado como identidade global do produto

**Evidência:** [product_service.py:23](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/product_service.py:23) busca produto por SKU usando `normalized_code` e grava o mesmo código no SKU interno.

**Impacto:** dois fornecedores com o mesmo código podem ser fundidos indevidamente, alterando nome/cor do mesmo produto. Alterar o SKU interno também rompe a associação nas reimportações. Resolver primeiro `(supplier_id, supplier_code)` e vincular ao UUID; SKU interno deve permanecer independente, como exige a instrução.

### 08 — P1 — Dados ausentes são inventados no cadastro

**Evidência:** [product_service.py:27](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/product_service.py:27) usa `Unnamed Product`; linha 42 usa `UNKNOWN` como código de fornecedor.

**Impacto:** além de violar NULL/ausência, vários itens sem código compartilham `UNKNOWN`; o vínculo de fornecedor pode apontar para um produto enquanto o item de importação aponta para outro. Preservar ausência e bloquear confirmação de campos obrigatórios até revisão; ajustar nullability quando apropriado.

### 09 — P1 — Caminho monetário deixa de ser Decimal

**Evidência:** [import_service.py:82](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:82) transforma preço em float; [mercadolivre_service.py:209](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/mercadolivre_service.py:209) faz `float(price)`; [dre-breakdown.tsx:18](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/components/pricing/dre-breakdown.tsx:18) soma valores monetários com Number. Models monetários são anotados `Mapped[float]`, embora as colunas sejam NUMERIC.

**Impacto:** viola diretamente a regra de dinheiro. Persistir decimais textuais no JSON, manter Decimal no backend e adotar serialização numérica exata compatível com a API. Diferenciar arredondamento visual de cálculos financeiros; corrigir também as anotações dos models. A anotação float, isoladamente, não prova que o driver deixou de retornar Decimal.

### 10 — P1 — Imagem comum pode ser marcada como “esgotado”

**Evidência:** [lehmox.py:428](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/importers/pdf/lehmox.py:428) considera esgotada qualquer imagem com proporção 2,3–2,7 e altura 80–280, mesmo sem texto ou hash conhecido.

**Reprodução:** bytes arbitrários com dimensão 250×100 retornaram `True`. O item é automaticamente ignorado e a imagem descartada. Trata-se de inferência proibida: heurística deve gerar sinal de revisão, nunca certeza de indisponibilidade.

### 11 — P1 — Adapter Lehmox aplicado a qualquer fornecedor; OCR ausente

**Evidência:** [import_service.py:24](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:24) fixa `importer_type='lehmox'`; linha 53 sempre instancia Lehmox. [lehmox.py:209](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/importers/pdf/lehmox.py:209) só extrai texto nativo.

**Impacto:** layouts não suportados e PDFs digitalizados podem terminar com zero itens, sem explicar a incompatibilidade. Selecionar adapter por configuração confiável; detectar necessidade de OCR e implementar o fallback previsto ou retornar explicitamente não suportado até existir implementação.

### 12 — P2 — Rastreabilidade do catálogo fica incompleta

**Evidência:** [import_service.py:90](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:90) trunca dados brutos; `page_number` e `bbox` do extrator não são persistidos. `file_hash`, `processing_log` e `total_errors` não são alimentados pelo fluxo.

**Impacto:** dificulta conferir origem, depurar associação espacial, detectar reenvios e interpretar contadores. `raw_price` aceita até 100 caracteres no item, mas é copiado para `raw_cost_value/raw_value` de 50, podendo falhar na confirmação. Preservar o bruto integral em JSONB e validar separadamente os campos normalizados limitados.

### 13 — P2 — Imagens reutilizadas no PDF só consideram a primeira ocorrência

**Evidência:** [lehmox.py:269](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/importers/pdf/lehmox.py:269) deduplica por xref e usa apenas `img_rects[0]`.

**Impacto:** uma imagem ou carimbo reutilizado em vários cards da página só é associado à primeira posição. Processar todas as ocorrências geométricas, ainda que os bytes sejam compartilhados.

### 14 — P2 — Limite esquerdo do card usa vizinho errado

**Evidência:** [lehmox.py:370](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/importers/pdf/lehmox.py:370) usa `left_neighbors[0]`; a lista é montada na ordem dos anchors, não pela menor distância.

**Impacto:** na terceira coluna pode usar a primeira como vizinha, causando sobreposição e associação indevida de textos/imagens. Escolher o vizinho mais próximo e testar limites entre cards, não apenas os centros do grid regular.

### 15 — P1 — Normalização transforma preço negativo em positivo

**Evidência:** [lehmox.py:115](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/importers/pdf/lehmox.py:115) captura somente o trecho numérico antes da validação de sinal.

**Reprodução:** `normalize_price('-13,00')` retornou `(Decimal('13.00'), [])`. Rejeitar entrada inválida ou preservar o sinal com alerta; validar finitude e formatos suportados sem interpretar silenciosamente trechos de texto ambíguos.

### 16 — P1 — Reenvios com o mesmo nome sobrescrevem o PDF original

**Evidência:** [import_service.py:16](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:16) grava em `imports/{supplier_id}/{file_name}`; `put()` usa `write_bytes`.

**Impacto:** dois jobs do mesmo fornecedor compartilham arquivo se o nome coincidir. Um processamento pendente pode ler o segundo catálogo, e a evidência original é perdida. Usar chave única por job, guardar o nome original como metadado e calcular hash.

### 17 — P1 — Validação e limite do PDF existem principalmente no navegador

**Evidência:** [imports.py:32](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/imports.py:32) verifica extensão; linha 41 carrega tudo em memória. `MAX_UPLOAD_SIZE_MB` não é aplicado no backend.

**Impacto:** cliente direto pode contornar 200 MB; arquivos renomeados, PDFs muito complexos e múltiplos uploads consomem recursos antes de validação adequada. Validar conteúdo/tipo com parser, tamanho durante leitura, limites de páginas/recursos e nome seguro. PDF deve ser tratado como não confiável, conforme a instrução.

### 18 — P2 — Processamento em BackgroundTasks não tem recuperação durável

**Evidência:** [imports.py:48](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/imports.py:48) agenda extração na própria aplicação; o serviço materializa todos os produtos/imagens em memória.

**Impacto:** reinício pode abandonar jobs `UPLOADED/PROCESSING`; não há retomada, cancelamento, timeout de extração ou limite de jobs concorrentes. Introduzir execução durável e recuperação de jobs, com processamento incremental e limpeza de arquivos órfãos.

### 19 — P1 — Timestamps de importação não têm timezone

**Evidência:** [import_service.py:51](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:51), 64, 127 e 138 usam `datetime.utcnow()`; as colunas são TIMESTAMPTZ.

**Impacto:** desrespeita a regra UTC aware e pode gerar incompatibilidade com driver ou interpretação local incorreta; `utcnow().timestamp()` interpreta um datetime ingênuo no timezone local. Usar `datetime.now(timezone.utc)`. A execução contra PostgreSQL não foi realizada para confirmar o comportamento do driver deste ambiente.

### 20 — P1 — Imagens não têm contrato funcional entre storage, API e frontend

**Evidência:** [product.py:30](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/schemas/product.py:30) retorna `storage_path`; os tipos/tela esperam `url`, `is_primary` e `order`. A revisão usa diretamente `src={item.image_path}`, que contém caminho relativo de storage. [service.py:40](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/storage/service.py:40) gera `/api/v1/storage/...`, rota inexistente.

**Impacto:** imagens importadas não são exibidas corretamente. Definir um contrato único de URL e metadados e gerar URLs das rotas efetivamente implementadas.

### 21 — P1 — Listagem de produtos nunca recebe custo, fornecedor ou imagem principal

**Evidência:** [product.py:40](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/schemas/product.py:40) define resposta básica sem `supplier_data` nem `primary_image`; a tabela de produtos usa esses campos.

**Impacto:** a UI apresenta traços/imagem vazia mesmo quando há dados no banco. Criar projeção de listagem compatível, com carregamento eficiente e custo do fornecedor explicitamente selecionado.

### 22 — P2 — Detalhe espera histórico e fornecedor em estruturas inexistentes

**Evidência:** [product.py:60](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/schemas/product.py:60) retorna histórico em `supplier_data[].prices` com `effective_at/import_id`; a tela espera `price_history` com `date/import_job_id`. Espera também `sd.supplier.name`, ausente no schema. `dimensions` esperado no tipo/tela não corresponde aos campos dimensionais da API.

**Impacto:** histórico aparece vazio e fornecedor “Desconhecido”. Alinhar o contrato; preservar dimensões/compatibilidade extraídas em campo apropriado, sem transformá-las por suposição em medidas físicas.

### 23 — P2 — Ciclo de atualização do produto está incompleto

**Evidência:** [product_service.py:36](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/product_service.py:36) e 61 só desativam quando esgotado; não há operação explícita equivalente para recuperação/revisão. [products.py](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/products.py) só oferece leitura e imagem.

**Impacto:** não há fluxo normal para corrigir SKU, marca, modelo, EAN/GTIN, descrição e outros dados antes de publicar; itens inativos não têm ciclo claro de reativação. Implementar edição validada e motivo/origem do status. Não reativar automaticamente por mera ausência do carimbo de esgotado.

## Achados: precificação

### 24 — P1 — Resolução de faixas produz preços e DRE inconsistentes

**Evidência:** [engine.py:287](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/pricing/engine.py:287) calcula só candidatos “com taxa/sem frete” e “sem taxa/com frete”, sem validar todas as combinações contra o preço final.

**Reproduções com `rounding_rule='EXACT'`:**

| Entradas de teste | Saída atual | Problema |
|---|---|---|
| Custo 75; taxa 10 abaixo de 80; margem alvo 0% | PV 75, taxa 0, margem 0% | Como PV < 80, taxa 10 se aplica. DRE correta desse mesmo preço: **−13,3333%** |
| Custo 100; taxa 6 sem limiar; frete 18 a partir de 79; margem 0% | PV 118, taxa 0 | Taxa incondicional foi removida. DRE do mesmo preço com taxa: **−5,0847%** |
| Custo 100; taxa 6 abaixo de 200; frete 18 a partir de 79; margem alvo 20% | PV 147,50; taxa 6; margem **15,9322%** | Preço foi calculado sem uma taxa que a própria DRE reconhece; nessa faixa PV 155 satisfaz o alvo |

Resolver combinações de faixas e suas fronteiras, validar custos aplicáveis ao preço final e conferir margem após arredondamento. Não basta recalcular uma vez após cruzar um limiar.

### 25 — P2 — Arredondamento comercial pode ficar abaixo do valor teórico

**Evidência:** [engine.py:78](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/pricing/engine.py:78) arredonda para centavos antes de verificar o terminal comercial.

**Reprodução:** `apply_rounding_rule(Decimal('45.904'), 'ENDS_90')` retorna `45.90`, abaixo do teórico, apesar da promessa de cobertura de margem. Comparar com o valor original nas regras ascendentes e verificar margem após arredondar cada dedução. `EXACT` deve ter sua tolerância documentada.

### 26 — P1 — Validação de perfis permite configurações inválidas

**Evidência:** [pricing.py:30](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/schemas/pricing.py:30) não repete limites do create; `PricingProfileUpdate(fixed_fee='-10')` foi aceito. Campos obrigatórios aceitam NULL no update; nomes não têm proteção equivalente. `rounding_rule` é string livre e o motor troca valor inválido silenciosamente por `ENDS_90`.

**Impacto:** custos negativos, regras diferentes das solicitadas e erros de integridade/serialização. Validar create/update consistentemente, limites/escala, soma percentual, combinações de frete e enums; não tratar custo de frete desconhecido como zero quando a regra exige frete.

### 27 — P1 — NUMERIC de percentual não comporta resultados permitidos

**Evidência:** [pricing.py:106](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/models/pricing.py:106) usa `NUMERIC(6,4)` para margem; os perfis também usam esse tipo. Ele comporta apenas dois dígitos inteiros. Schemas aceitam 100 e −100; margem real com override pode ser menor que −100%, ou 100% com custo zero.

**Impacto:** entradas/cálculos válidos pelo contrato podem estourar a coluna ao persistir. Ampliar precisão em migration e alinhar os limites. Isso foi identificado por inspeção de schema, sem INSERT no banco real.

### 28 — P1 — Preço calculado fica obsoleto e continua publicável

**Evidência:** [pricing_repository.py:42](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/repositories/pricing_repository.py:42) atualiza perfil sem invalidar preços persistidos; reimportação de custo também não os invalida. [mercadolivre_service.py:170](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/mercadolivre_service.py:170) publica o valor armazenado.

**Impacto:** alterar comissão/custo mantém preço e DRE antigos sem aviso. Registrar versão/origem do cálculo, marcar obsolescência e exigir recálculo quando insumos mudarem. Invalidar cache da UI não recalcula registros no banco.

### 29 — P2 — Custo base escolhido sem política explícita e sem verificar fornecedor pai

**Evidência:** [pricing_service.py:104](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/pricing_service.py:104) usa o primeiro vínculo `sup.is_active` com custo, sem seleção explícita/ordenação e sem testar `Supplier.is_active`. A UI de detalhe escolhe o primeiro custo não nulo mesmo de vínculo inativo.

**Impacto:** custo exibido pode diferir do usado no cálculo; fornecedor desativado pode continuar influenciando preço. Exigir fornecedor/custo escolhido ou política documentada e persistir sua origem.

### 30 — P1 — Tela cria taxas, impostos, custos e margem sem fonte

**Evidência:** [profile-dialog.tsx:38](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/components/pricing/profile-dialog.tsx:38) e [pricing/page.tsx:37](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/app/(dashboard)/pricing/page.tsx:37) iniciam com comissão 14%, taxa 6, impostos 6%, operacional 3%, custo fixo 3,50, frete 18 e limiar 79. O simulador calcula automaticamente com custo 35.

**Impacto:** esses números podem ser salvos como perfil real sem fonte ou preenchimento consciente. Não afirmo que são as tarifas atuais de qualquer marketplace. Pela instrução, os campos devem iniciar ausentes e exigir informação confiável; zero só deve significar custo efetivamente zero.

## Achados: segurança e Mercado Livre

### 31 — P0 — API de negócio sem autenticação/autorização da aplicação

**Evidência:** [deps.py](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/deps.py) define apenas banco/storage; [router.py](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/router.py) não aplica autenticação. Rotas de escrita, publicação e desconexão também não verificam usuário/permissão.

**Impacto:** se o deploy configurado estiver acessível sem proteção externa, qualquer cliente que o alcance pode consultar dados, alterar registros, desconectar contas e publicar usando tokens guardados no servidor. CORS não substitui autenticação. Implantar proteção de sessão/API e autorização antes da exposição operacional. Não foi executado ataque contra a VPS.

### 32 — P1 — OAuth usa `state` fixo e ignora a verificação no callback

**Evidência:** [client.py:32](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/integrations/mercadolivre/client.py:32) usa `adapterflow_oauth`; [marketplaces.py:57](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/marketplaces.py:57) passa apenas `request.code` ao serviço, embora o schema receba state.

**Impacto:** não há correlação segura entre quem iniciou a conexão e o callback. Gerar state aleatório, com validade e consumo único, vinculado à sessão iniciadora, e validar no backend. O próprio documento local da integração já exige state aleatório.

### 33 — P1 — Erros internos podem vazar dados e segredos

**Evidência:** [main.py:26](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/main.py:26) registra exceção completa e retorna `str(exc)` ao cliente. Upload faz o mesmo. Escrita de tokens usa SQLAlchemy sem ocultação dos parâmetros do engine.

**Impacto:** exceções SQL podem carregar parâmetros, incluindo tokens de um INSERT/UPDATE que falhou. É um caminho potencial de vazamento, não evidência de segredo já exposto. Usar mensagens públicas genéricas, identificador de incidente e logs com remoção de dados sensíveis; ocultar parâmetros SQL.

### 34 — P1 — Storage valida prefixo textual, não descendência real; rotas não verificam vínculo

**Evidência:** [service.py:13](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/storage/service.py:13) usa `str(full_path).startswith(str(base_path))`. No Windows, um caminho absoluto `.../storage_sibling/audit.txt` foi aceito com base `.../storage`. A reprodução só resolveu o caminho; não leu nem gravou fora do storage.

**Impacto:** confinamento incorreto na plataforma local; não se afirma que esse mesmo vetor absoluto funciona igual no Linux. Além disso, [products.py:27](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/api/v1/products.py:27) ignora o vínculo do `id` ao arquivo e a rota de imagens de importação aceita qualquer arquivo do storage. Usar descendência por componentes, rejeitar caminhos absolutos e servir por ID de imagem autorizado.

### 35 — P1 — Publicação sempre fica ACTIVE, independentemente do status retornado

**Evidência:** [mercadolivre_service.py:240](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/mercadolivre_service.py:240) grava `ACTIVE` fixo, não valida presença de ID externo e usa preço/quantidade da requisição. Linha 266 grava `last_synced_at` até em erro.

**Impacto:** um anúncio não ativo pode aparecer ativo; tentativa falha aparece com data de sincronização. Persistir identificador, status e valores efetivamente confirmados pela resposta, com validação; separar última tentativa de última sincronização bem-sucedida. Não há fluxo posterior de consulta/webhook para manter o status atual.

### 36 — P1 — “Conectado”, “Ativa” e “Credenciais validadas” não refletem validação real

**Evidência:** [mercadolivre_service.py:47](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/mercadolivre_service.py:47) calcula conexão apenas pela existência de conta ativa no banco; `is_configured()` só verifica preenchimento. A página de marketplaces escreve “Credenciais validadas” e exibe badge “Ativa” incondicional por conta.

**Impacto:** revogação e falha de refresh não atualizam o panorama. Exibir configuração presente, última conexão verificada e reautenticação necessária como estados distintos; registrar validade/erro verificáveis.

### 37 — P1 — Publicação pode usar preço de outro canal/perfil

**Evidência:** [mercadolivre_service.py:180](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/mercadolivre_service.py:180) escolhe o primeiro preço existente quando não encontra o solicitado. Não verifica canal do perfil, atividade do perfil nem correspondência entre comissão e tipo de anúncio.

**Impacto:** preço de outro marketplace ou perfil pode ser publicado no Mercado Livre; trocar Clássico por Premium não recalcula custos. Exigir perfil válido explícito, canal e condições compatíveis; falhar se não encontrar o perfil pedido, sem fallback silencioso.

### 38 — P1 — Estoque e condição são presumidos; inatividade não bloqueia publicação

**Evidência:** [marketplace.py:51](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/schemas/marketplace.py:51) define quantidade 1 e condição `new`; [publish-dialog.tsx:54](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/components/marketplaces/publish-dialog.tsx:54) repete defaults. `setCondition` não é usado por nenhum campo. O serviço não impede produto inativo/esgotado de ser publicado.

**Impacto:** pode anunciar estoque inexistente ou condição desconhecida como nova. Exigir quantidade e condição informadas/verificadas e política explícita para produto inativo; não confundir quantidade por caixa com estoque.

### 39 — P1 — Publicação não envia fotos nem oferece atributos necessários à revisão

**Evidência:** [mercadolivre_service.py:206](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/mercadolivre_service.py:206) monta payload sem `pictures`, embora produto tenha imagens. `get_category_attributes()` existe no client, mas não tem fluxo de UI/serviço. O frontend não envia `attributes`; o backend só acrescenta marca/modelo/EAN. `product.gtin` separado é ignorado.

**Impacto:** fluxo não permite completar anúncios de categorias que exigem informações adicionais; fotos importadas não chegam ao anúncio. Implementar resolução de imagens e atributos conforme documentação oficial verificada, validando conflitos/deduplicação e origem dos valores. Não completar marca/modelo/GTIN por suposição.

### 40 — P1 — Timeout, repetição e falha de persistência podem duplicar anúncios

**Evidência:** [api.ts:20](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/lib/api.ts:20) limita a chamada a 15 s; o backend encadeia refresh de até 15 s, validação de até 15 s e publicação de até 20 s. Não há chave de operação, trava de publicação ou reconciliação de resultado incerto.

**Impacto:** timeout no navegador não desfaz o POST externo. Repetir pode criar outro anúncio. Falha no commit após sucesso externo é tratada como falha de publicação; o catch tenta gravar outro registro na mesma sessão sem rollback. Persistir tentativa antes do efeito externo, distinguir resultado incerto e reconciliar antes de repetir.

### 41 — P2 — Renovação de token não tem coordenação nem recuperação de revogação

**Evidência:** [mercadolivre_service.py:131](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/mercadolivre_service.py:131) renova a partir de leitura comum, sem lock; requisições paralelas podem renovar e sobrescrever tokens. 401 com token ainda não vencido não dispara tratamento equivalente nem marca reautenticação.

**Impacto:** corrida na rotação e sessão local inconsistente. Serializar refresh por conta, persistir atomicamente e distinguir erro transitório de revogação. `expires_in` ausente deve ser erro de contrato, não validade presumida de seis horas.

### 42 — P2 — Falhas de categoria são mascaradas como lista vazia

**Evidência:** [client.py:151](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/integrations/mercadolivre/client.py:151) e 162 retornam `[]` para qualquer resposta não 200. O serviço de predição nunca fornece o token opcional.

**Impacto:** indisponibilidade, autorização e falta de sugestões ficam indistinguíveis. Propagar erro estruturado, usar autenticação conforme contrato oficial e aplicar debounce. Não afirmo, sem confirmação oficial acessível, que todo endpoint consultado exige token.

### 43 — P1 — Desconectar conta apaga histórico de anúncios

**Evidência:** [marketplace_repository.py:79](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/repositories/marketplace_repository.py:79) executa delete; [marketplace.py:54](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/models/marketplace.py:54) tem cascade delete-orphan e FKs com CASCADE.

**Impacto:** perde rastreabilidade local; anúncios externos não são encerrados por essa operação. Usar desconexão lógica, descarte seguro de tokens e manutenção do histórico, explicando separadamente eventual revogação externa. A regra de soft delete é aplicável aqui.

### 44 — P1 — Campo de título do anúncio é resetado após digitação

**Evidência:** [publish-dialog.tsx:47](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/components/marketplaces/publish-dialog.tsx:47) cria novo array via `filter` a cada render; esse array é dependência do efeito que executa `setTitle(product.name.slice(0, 60))` quando aberto.

**Impacto:** cada edição provoca render e o efeito repõe o título original. Memorizar dados e inicializar o formulário somente ao abrir/trocar produto. Limpar/revalidar também a categoria ao mudar o contexto; a primeira sugestão não deve virar classificação definitiva sem revisão.

## Achados: interface, infraestrutura e qualidade

### 45 — P1 — Revisão anuncia sucesso antes da resposta e informa quantidade diferente da confirmada

**Evidência:** [review/page.tsx:55](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/app/(dashboard)/imports/[id]/review/page.tsx:55) dispara várias mutations e em seguida `toast.success`. `eligibleCount` inclui ERROR e IMPORTED e não segue a regra de seleção dos aprovados do backend. Confirmação não aguarda todas as aprovações pendentes.

**Impacto:** o operador pode confirmar enquanto aprovações falham ou ainda estão em trânsito, e o botão promete mais produtos do que serão cadastrados. Aguardar resultado, apresentar falhas por item, obter contagem efetiva da API e bloquear ações concorrentes.

### 46 — P2 — Falha de carregamento é exibida como ausência, tela em branco ou estado permanente

**Evidência:** importação, revisão, precificação, marketplaces e publicações não tratam `isError` adequadamente. Publicações usa `!data` para “Nenhum anúncio”; revisão retorna `null`. `useImport` e `useImportItems` não fazem polling de job em processamento. Callback sem `code` e sem `error` permanece no spinner.

**Impacto:** viola a distinção entre ausência real e backend indisponível. Implementar estados erro/vazio/processando separadamente, recuperação e atualização da revisão; exibir `error_message` do job. Preservar zero legítimo usando verificação de NULL, inclusive preço/confiança.

### 47 — P2 — Paginação do backend não é navegável nas telas

**Evidência:** produtos/importações solicitam apenas 50 itens; fornecedores 100; publicações 50. Não há controles para páginas seguintes. APIs aceitam `skip/limit` sem limites apropriados; revisão carrega todos os itens e ignora o `limit=1000` enviado pelo hook.

**Impacto:** registros antigos ficam inacessíveis pelo fluxo normal e requisições grandes podem consumir recursos. Implementar paginação visível, limites no servidor e revisão em lotes. Corrigir `PaginatedResponse`, que exige page/size/pages que a API não retorna.

### 48 — P2 — Módulos futuros renderizam a tela de precificação

**Evidência:** [inventory/page.tsx:1](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/app/(dashboard)/inventory/page.tsx:1), orders, sales, reports e settings reexportam `../pricing/page`.

**Impacto:** clicar em “Pedidos” ou “Estoque” abre funcionalidade diferente sob título inconsistente. A ausência das fases futuras é prevista; o erro é representar outra tela no lugar delas. Mostrar estado explícito de não implementado/em breve.

### 49 — P2 — Limpar código de fornecedor não remove o valor salvo

**Evidência:** [suppliers/page.tsx:86](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/app/(dashboard)/suppliers/page.tsx:86) transforma código vazio em `undefined`; JSON omite esse campo, e PATCH usa `exclude_unset`. `SupplierUpdate` também não compartilha normalização/limites do cadastro.

**Impacto:** apagar e salvar mantém o código anterior. Usar NULL explícito para remoção e validação de comprimento/nome; converter conflito de código único em erro de negócio, não 500.

### 50 — P1 — Next.js instalado contradiz versão obrigatória

**Evidência:** [package.json:23](C:/Users/AdapterCO/Desktop/AdapterFlow/frontend/package.json:23) declara Next.js 16.3.5; build confirmou a mesma versão. `instrucao.md` exige Next.js 15.

**Correção:** alinhar código/dependências/lockfile à versão 15 compatível, com validação de build. Não alterar silenciosamente o documento normativo para legitimar a divergência; qualquer mudança arquitetural deve ser deliberada e registrada.

### 51 — P1 — Credenciais Mercado Livre do `.env` não chegam ao container backend

**Evidência:** [docker-compose.yml:27](C:/Users/AdapterCO/Desktop/AdapterFlow/docker-compose.yml:27) passa apenas banco, storage e CORS; não há `env_file` nem `MERCADOLIVRE_*` em environment. O `.env` da raiz não integra o contexto `./backend`, e o Dockerfile ignora `.env`.

**Impacto:** preencher `.env.example` como orientado não configura OAuth no Compose fornecido. Passar explicitamente as variáveis necessárias sem embutir segredos na imagem. Para execução local, documentar o caminho efetivo do env, pois `env_file='.env'` é relativo ao diretório de execução.

### 52 — P2 — Procedimento de instalação documentado não corresponde à infraestrutura

**Evidência:** Compose só usa `expose`, depende da rede externa `traefik9` e fixa domínio/labels. README promete localhost:3099 e localhost:8000 com `docker compose up --build`. `FRONTEND_PORT/BACKEND_PORT/DOMAIN` não parametrizam todo o roteamento. Em execução sem Docker, proxy Next usa `http://backend:8000` por padrão.

**Impacto:** setup novo não reproduz os endereços prometidos; rede/proxy externos não são provisionados. Separar configuração local e VPS, documentar pré-requisitos e usar `INTERNAL_BACKEND_URL=http://localhost:8000` no desenvolvimento apropriado. `.env.example` também não oferece DATABASE_URL/STORAGE_PATH descritos pelo README.

### 53 — P2 — Verificação de qualidade falha e testes não cobrem os defeitos principais

**Evidência:** lint apresentou 20 erros/20 avisos: `any`, interface vazia, efeitos e dependências, imports ociosos e imagens. Os 23 testes passaram, mas APIs usam mocks; não cobrem upload → revisão → confirmação em PostgreSQL, transações, contratos das imagens, publicação completa, falha/revogação ou faixas problemáticas do motor.

**Impacto:** build/TypeScript verdes dão cobertura insuficiente. O teste de grid usa blocos sintéticos; o teste de PDF real depende de caminho absoluto local e verifica essencialmente presença de esgotados. Criar CI com testes de contrato, banco real isolado e E2E dos fluxos críticos; mocks são legítimos para testes, mas não comprovam integração real.

### 54 — P2 — Documentação de conclusão contradiz a implementação e outros documentos

**Evidência:** `instrucao.md` marca fases 1–3 concluídas, enquanto [mercadolivre.md:3](C:/Users/AdapterCO/Desktop/AdapterFlow/docs/integrations/mercadolivre.md:3) diz `IN_DEVELOPMENT`. README anuncia gerenciamento/CSV como objetivo, mas CSV não existe; descreve `frontend/src`, pasta inexistente no layout atual.

**Impacto:** usuários e desenvolvedores podem assumir capacidades não entregues. Manter requisitos da instrução como meta obrigatória; registrar pendências reais e critérios verificáveis de conclusão. Distinguir objetivos futuros de funcionalidades disponíveis. O campo “última verificação” da documentação não substitui evidência executável do fluxo atual.

### 55 — P2 — Constraints/modelos permitem inconsistências e dificultam evolução

**Evidência:** não há CHECKs para estados/valores; `is_default` não é único por canal. A constraint de produto/perfil chama `uq_product_channel_pricing_profile` no ORM e `uq_product_channel_prices_product_id_pricing_profile_id` na migration; defaults server-side de várias colunas das migrations não constam no ORM.

**Impacto:** múltiplos perfis padrão, estados inválidos e drift em autogenerate. Alinhar metadados/migrations, definir invariantes no banco e usar upserts/locks contra corridas. Perfis são apagados fisicamente com cascade dos preços; preferir desativação quando for necessário preservar histórico financeiro.

### 56 — P2 — Formulários e abstração de storage não seguem integralmente as convenções

**Evidência:** apenas fornecedores usa react-hook-form + zod; publicação e perfis usam estado manual. [import_service.py:54](C:/Users/AdapterCO/Desktop/AdapterFlow/backend/app/services/import_service.py:54) acessa `_get_full_path` de StorageService, acoplando processamento ao filesystem local.

**Impacto:** validações são repetidas/incompletas e a migração futura para S3 não respeita o contrato declarado. Adotar validação de formulários compartilhada e consumir interface pública de storage, com materialização temporária controlada quando necessária ao parser.

## Melhorias adicionais, sem tratá-las como falhas funcionais comprovadas

1. **Tokens em repouso:** colunas são Text sem criptografia na aplicação. Não foi inspecionada criptografia do volume/banco. Adotar proteção em repouso, rotação e acesso restrito; o comentário “Tokens protegidos” não demonstra esses controles.
2. **Senha de desenvolvimento:** configuração e Compose têm fallback de senha conhecido. Exigir segredo explícito no deploy e falhar na inicialização se ausente; não há evidência de que esse fallback esteja sendo usado na VPS.
3. **Imagem backend:** roda como root, mantém ferramentas de compilação e não exclui `venv/` no `.dockerignore`; o venv existe neste checkout e pode inflar a imagem. Usar usuário sem privilégios, build separado e exclusões adequadas.
4. **Dependências reproduzíveis:** requirements usa apenas limites mínimos, sem lock; pinagem/hashes e atualização controlada reduzem divergência entre testes e deploy. Não foi realizada auditoria de CVEs; não se afirma vulnerabilidade específica de versão.
5. **Readiness:** `/health` responde sempre ok sem banco/storage. Separar liveness de readiness e healthchecks de backend/frontend.
6. **Backups e recuperação:** não há procedimento versionado de backup/restauração do PostgreSQL e arquivos. Definir retenção e testar restauração consistente dos dois.
7. **Índices e volume:** revisar índices de FKs, status/data e busca `ILIKE '%...%'` com dados representativos. As migrations não criam índices secundários além dos implícitos das constraints. Evitar anunciar ganho de desempenho sem medir.
8. **Clientes externos:** reutilizar cliente HTTP/pool, classificar timeout/429/5xx, aplicar backoff apenas onde seguro e preservar identificadores de correlação. Não repetir publicação cegamente.
9. **Observabilidade:** registrar métricas de extração, falhas, fila, memória e latência, sem conteúdo sensível; criar trilha de alterações de custo/perfil/publicação.
10. **Acessibilidade:** verificar nomes acessíveis de botões só com ícone, títulos de dialogs/sheet, navegação por teclado e feedback de erro. Não houve auditoria visual/interativa nesta sessão.
11. **Tipos de API:** gerar tipos a partir do OpenAPI e validar respostas quando necessário; interfaces manuais hoje escondem várias incompatibilidades.
12. **Retenção:** definir limpeza de uploads/imagens órfãos após falha e política de retenção de fontes, mantendo a rastreabilidade exigida.
13. **Dados pessoais:** guardar apenas os campos necessários de `settings.user_info`; atualmente toda a resposta de usuário é persistida.

## Ordem recomendada de correção e critérios de aceite

| Ordem | Trabalho | Critério de aceite |
|---|---|---|
| 1 | Proteção de acesso, OAuth state, logs e storage | Escritas exigem autorização; callbacks inválidos rejeitados; segredos ausentes de erros; caminhos externos rejeitados |
| 2 | Importação, PATCH JSONB, identidade, transações e estados | PDF conhecido passa pelo fluxo completo; itens não atravessam jobs; falha não deixa confirmação parcial silenciosa; reenvio não sobrescreve fonte |
| 3 | Remoção de dados presumidos | Campos sem fonte ficam NULL/vazios; estoque/condição/taxas exigem dado confiável; heurísticas apenas pedem revisão |
| 4 | Motor Decimal e persistência | Todos os exemplos de faixa deste relatório corrigidos; DRE e margem consistentes; schema suporta resultados válidos |
| 5 | Contratos frontend/API e edição do catálogo | Imagens, fornecedores, custos e histórico aparecem; revisão realmente salva; UI diferencia erro/ausência/processamento |
| 6 | Publicação real controlada | Payload verificado oficialmente; fotos/atributos completos; preço atualizado e canal correto; estado externo preservado; resultados incertos reconciliáveis |
| 7 | Stack/deploy/documentação e testes | Next.js conforme instrução; setup reproduzível; lint e build passam; testes de banco e E2E cobrem os fluxos |

Não considerar fases 1–3 operacionalmente concluídas apenas porque há páginas, classes e testes unitários. O aceite precisa demonstrar os fluxos completos e a conformidade com as regras de dados, dinheiro, segurança e estados reais de `instrucao.md`.
