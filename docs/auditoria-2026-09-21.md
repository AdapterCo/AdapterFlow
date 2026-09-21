# Auditoria técnica do AdapterFlow — 21/09/2026

Estado analisado: commit `1ca9c64`, branch observada pelo Git, árvore de trabalho inicialmente limpa. Raiz: `C:\Users\AdapterCO\Desktop\AdapterFlow`.

**Conclusão: o projeto tem uma base funcional, mas o estado atual não está pronto para ser considerado estável em produção. Há uma vulnerabilidade crítica de autenticação, falhas reproduzidas na extração do catálogo real e funcionalidades que anunciam resultados que não executam.**

Esta auditoria compara o código atual com `instrucao.md`. Não presume que commits, relatórios anteriores ou testes aprovados comprovem a operação completa. Nenhuma publicação, autorização externa, alteração de dados de produção ou correção funcional foi realizada nesta análise.

## Evidências executadas

| Verificação | Resultado |
|---|---|
| Backend: `python -m pytest -q` | 117 passaram; 3 testes de PostgreSQL foram ignorados por ausência de `TEST_DATABASE_URL` |
| Backend: `ruff check app --select F` | Falhou: 6 imports não utilizados, distribuídos entre Shopee e clonador |
| Frontend: `npx tsc --noEmit` | Passou |
| Frontend: `npm run lint -- --max-warnings=0` | Falhou: `frontend/types/index.ts:85`, `no-explicit-any` |
| Frontend: `node scripts/test-middleware.mjs` | Falhou: o teste não fornece `request.cookies`, exigido pelo middleware atual |
| OpenAPI calculado em memória versus arquivo versionado | Divergente: 49 caminhos atuais contra 34 documentados; 15 caminhos ausentes |
| Middleware real transpilado, executado localmente com credenciais sintéticas | Cookie inválido e Basic inválido foram aceitos e receberam credenciais administrativas injetadas |
| Cliente Shopee com transporte HTTP simulado | Token sintético apareceu no log INFO de HTTPX |
| URL de autorização Shopee com `state` sintético | O `state` fornecido não aparece na URL nem no redirect configurado |
| Parser de link de catálogo ML | `/p/MLB123456` foi classificado como anúncio comum (`is_catalog=False`) |
| Contrato de armazenamento do clonador | `StorageService.save` não existe |

O build completo do frontend não foi executado nesta auditoria: lint e testes de middleware já reprovam a sequência exigida no CI. Não houve teste de migração/persistência contra PostgreSQL nem execução na VPS nesta rodada. Isso limita conclusões sobre banco, rede, certificados e configuração efetivamente implantada.

### PDF real fornecido pelo usuário

Arquivo: `C:\Users\AdapterCO\Desktop\TrabalhoFelipe\LEHMOX  2026.09.16 2-26.pdf` — 35.305.748 bytes.

A leitura passou pelo subprocesso real usado pelo serviço, primeiro metadados e depois cada página, sem envio do arquivo a serviços externos:

- 25 páginas percorridas, todas retornadas como `EXTRACTED`.
- 224 candidatos a produto; esse número não comprova 224 produtos corretamente identificados.
- 145 candidatos sem preço normalizado: 144 por preços conflitantes e 1 sem preço detectado.
- 1 candidato sem nome e 1 sem imagem.
- 18 ocorrências adicionais de códigos repetidos. A repetição pode existir na origem; exige uma regra explícita de resolução, não deduplicação cega.
- Aproximadamente 27,34 segundos para a extração isolada completa neste computador, sem persistência no banco.

Uma segunda leitura confirmou os avisos de ambiguidade. Logo, afirmar apenas que “leu todas as páginas” não demonstra que o catálogo foi importado corretamente.

## Problemas confirmados e correções necessárias

Prioridades: **P0** bloqueia exposição segura; **P1** compromete função essencial, dados ou cumprimento das regras; **P2** causa inconsistências operacionais ou dificulta manutenção.

### A01 — P0 — Autenticação administrativa contornável

**Fonte:** `frontend/middleware.ts:22`, `:40`, `:65`.

O middleware considera autenticado qualquer cookie `adapterflow_session` com mais de dez caracteres. Também considera válido qualquer cabeçalho que comece com `Basic ` quando as variáveis administrativas estão configuradas. Nenhum desses caminhos verifica a credencial. Depois, substitui o Authorization recebido pelas credenciais administrativas verdadeiras do servidor.

**Reprodução local:** ambos os casos inválidos atravessaram o middleware com `adminCredentialsInjected=true`. Isso inutiliza a validação posterior do backend, que recebe uma credencial válida criada pelo próprio proxy. O Compose fornece exatamente as variáveis necessárias para esse comportamento.

**Correção:** remover a promoção de requisições não autenticadas a administrador; validar a sessão de fato e deixar o backend como autoridade. Cobrir cookie falso, expirado, assinatura incorreta, Basic errado e ausência de credencial. Esta é a primeira correção, antes de novo deploy público desse código.

### A02 — P1 — Cadastro de conta fictício

**Fonte:** `frontend/app/(auth)/register/page.tsx:63`.

O formulário apenas espera 900 ms, mostra “cadastrada com sucesso” e redireciona. Não chama API nem persiste usuário. O backend oferece login do operador configurado, não cadastro de contas.

**Impacto:** o usuário fornece dados e senha, acredita que criou uma conta e continua sem acesso. Viola diretamente “Frontend Não Deve Mentir”. **Correção:** retirar o fluxo fictício ou implementar o cadastro completo com o modelo de acesso definido; só mostrar sucesso após persistência real.

### A03 — P1 — Tokens Shopee aparecem em logs

**Fontes:** `backend/app/main.py:15`; `backend/app/integrations/shopee/client.py:104`, `:116`.

O token viaja na query da requisição e HTTPX registra a URL em INFO, habilitado globalmente. A reprodução usou somente token sintético e comprovou sua presença no log.

**Correção:** suprimir/redigir logs de URLs autenticadas, inclusive mensagens de exceção. Validar com testes de captura de logs. Se esse fluxo já tiver sido usado na VPS, verificar os logs de forma protegida e avaliar a rotação dos tokens que efetivamente apareceram. Não há evidência nesta auditoria de exposição de token real.

### A04 — P1 — Extração percorre o PDF, mas ainda mistura preços

**Fonte:** `backend/app/importers/pdf/lehmox.py:455`, `:463`, `:556`, `:602`.

A segmentação usa distâncias fixas para linhas, colunas e células. Ela não identifica de forma confiável todos os limites dos produtos do PDF real. Na amostra, 144 candidatos acumulam preços diferentes e acabam com preço nulo.

Manter o preço nulo em caso de dúvida está correto. O defeito está na qualidade da separação e associação do texto, e não deve ser “corrigido” selecionando arbitrariamente um dos preços.

**Correção:** distinguir conteúdo relevante de sobreposições/modelos gráficos, reconhecer limites de cada produto e associar preço/imagem pela região efetiva. Criar regressões a partir de trechos autorizados do catálogo, com resultados revisados visualmente e layouts variados. Preservar a evidência por página já existente.

### A05 — P1 — OCR e páginas não reconhecidas não possuem recuperação completa

**Fontes:** `backend/app/importers/pdf/lehmox.py:239`, `:244`; `backend/app/services/import_service.py:107`, `:163`, `retry_import`; rotas de importação.

O OCR só é tentado se a página inteira não tiver texto. Uma página com cabeçalho selecionável e produtos escaneados não entra nesse caminho. Com OCR desabilitado, a página sem texto fica em `NEEDS_REVIEW`; o job pode terminar em revisão, mas o retry só aceita jobs `FAILED` e pula páginas cujo status não seja `FAILED`.

Também não existe rota para criar manualmente um candidato a partir de uma página que teve zero produtos detectados. Exibir o texto e as imagens ajuda a diagnosticar, mas não conclui o trabalho.

**Correção:** permitir reprocessamento seletivo de páginas, OCR necessário por região/página e inclusão manual de candidatos vinculados à evidência, sem substituir silenciosamente revisões já feitas.

### A06 — P2 — Status de página esconde pendências dos candidatos

**Fonte:** `backend/app/importers/pdf/lehmox.py:270`.

O status da página usa apenas os avisos da própria página; não incorpora os avisos dos produtos. Assim, todas as 25 páginas do teste ficaram `EXTRACTED` apesar de 145 candidatos sem preço. **Correção:** separar “leitura realizada” de “dados completos/revisados” e exibir contagens de pendências por página.

### A07 — P1 — Itens ignorados impedem conclusão e voltam a ser aprovados

**Fonte:** `backend/app/services/import_service.py:263`, `:316`.

`confirm_import` trata `IGNORED` como pendência e mantém o job em `REVIEW_REQUIRED`. `approve_all_items` também reaprova itens `IGNORED` que não estejam esgotados. A decisão de ignorar um item não é respeitada como decisão final.

**Correção:** definir uma máquina de estados consistente; ignorado/rejeitado deve encerrar a revisão daquele item, e aprovação em lote não deve desfazer uma escolha explícita sem uma ação específica do operador.

### A08 — P1 — Esgotamento detectado não atualiza produto já cadastrado

**Fontes:** `backend/app/services/import_service.py:181`; `backend/app/services/product_service.py:104`, `:129`.

O extrator marca esgotamento, mas o serviço transforma o candidato em `IGNORED`, e a aprovação em lote o exclui. O código que desativa produto/vínculo está dentro da criação a partir de um item aprovado, caminho que esses candidatos normalmente não percorrem.

**Impacto:** um produto anteriormente ativo pode continuar ativo apesar do novo catálogo informar indisponibilidade. **Correção:** criar uma ação revisável de atualização de disponibilidade dos vínculos existentes, sem inventar estoque nem publicar automaticamente.

### A09 — P1 — Códigos repetidos podem sobrescrever dados sem decisão de conflito

**Fontes:** `backend/app/repositories/import_repository.py:70`; `backend/app/services/product_service.py:create_from_import`.

Os itens de confirmação são carregados sem ordenação explícita. Itens com o mesmo fornecedor/código atualizam o mesmo vínculo; não existe decisão sobre valores conflitantes no lote. A amostra real tem 18 ocorrências adicionais de códigos repetidos.

**Correção:** apresentar conflitos e manter uma decisão explícita e auditável; ordenar processamento e impedir que a ordem incidental da consulta escolha o custo/nome final.

### A10 — P1 — Clonador não salva as fotos

**Fonte:** `backend/app/services/clone_service.py:300`; `backend/app/storage/service.py`.

O clonador chama `self.storage.save(...)`, mas a abstração só implementa `put(...)`. A exceção é capturada pelo `except Exception: pass` do loop. O produto pode ser criado com aparência de sucesso, sem nenhuma foto persistida.

**Correção:** usar o contrato real de armazenamento e tornar falhas de foto visíveis; testar criação completa, incluindo arquivos e registros de imagens, não apenas preview.

### A11 — P1 — Links de catálogo Mercado Livre são classificados incorretamente

**Fonte:** `backend/app/services/clone_service.py:26`.

O código procura `"/p/MLB"` dentro de `cleaned.upper()`. A letra `p` da busca é minúscula e a URL foi convertida para maiúsculas: a classificação fica falsa. O fallback pode ocultar o defeito em certos retornos, mas uma recusa no primeiro endpoint encerra a consulta antes de tentar o produto de catálogo.

**Correção:** normalizar os dois lados e validar endpoint e tipo do identificador. O teste existente de catálogo devolve o mesmo mock para qualquer URL, por isso passa mesmo consultando o endpoint errado.

### A12 — P1 — Clonador cria informações sem fonte

**Fonte:** `backend/app/services/clone_service.py:270`, `:274`, `:318`, `:324`.

Cria SKU a partir do identificador ML, nome substituto `Produto Clonado ...`, código de fornecedor derivado do ML e `pcs_per_box=1`. O identificador do marketplace não comprova código do fornecedor nem quantidade na caixa.

**Correção:** armazenar a procedência/ID externo em campos próprios e solicitar dados reais quando forem obrigatórios. Ausências devem permanecer nulas conforme `instrucao.md`.

### A13 — P2 — Repetir clonagem provoca conflito de SKU

**Fontes:** `backend/app/services/clone_service.py:270`; `backend/app/models/product.py:sku`.

O SKU derivado é determinístico e único no banco; a clonagem sempre cria produto novo e não consulta uma importação anterior. Repetir o mesmo anúncio pode resultar em conflito em vez de atualizar/retornar a cópia existente.

**Correção:** definir identidade e idempotência pela origem externa, com comportamento explícito de atualizar, reutilizar ou criar uma nova versão.

### A14 — P1 — OAuth Shopee exige um `state` que não envia

**Fontes:** `backend/app/services/shopee_service.py:start_oauth`; `backend/app/integrations/shopee/client.py:65`; `frontend/app/(dashboard)/marketplaces/callback/shopee/page.tsx`; `ShopeeOAuthCallbackRequest`.

O serviço gera e salva `state`, mas `get_authorization_url(state)` ignora o argumento. A tela de retorno lê `state` da URL e o backend exige de 20 a 200 caracteres e correspondência com a tentativa salva.

**Correção:** fechar o contrato de ida/volta conforme a documentação oficial da Shopee, mantendo vínculo com navegador/operador. Simular a URL completa de ida e o callback, não apenas a assinatura de uma requisição.

### A15 — P1 — Shopee não recebe configuração no deploy padrão

**Fontes:** `.env.example:16`; `docker-compose.yml:environment`; `backend/app/core/config.py`.

As variáveis Shopee aparecem no exemplo de `.env` e são lidas pelo backend, mas não são repassadas no bloco `environment` do Compose, que também não declara um `env_file` para elas. O `.env` da raiz serve à interpolação; não injeta automaticamente todos os valores nos containers.

**Correção:** repassar explicitamente as variáveis necessárias, sem embuti-las na imagem ou versionar segredos. Validar os diagnósticos dentro do container.

### A16 — P1 — Publicação Shopee inventa peso, logística, marca e estoque

**Fontes:** `backend/app/services/shopee_service.py:220`, `:229`, `:233`; `frontend/components/marketplaces/publish-shopee-dialog.tsx:77`.

O backend usa peso `0.3` quando não informado, marca `NoBrand`/ID zero e logística ID zero. O frontend preenche quantidade `10`. Essas informações não foram obtidas da conta ou do produto e contradizem diretamente `instrucao.md`.

**Correção:** exigir peso/estoque reais e consultar opções válidas de logística e marca; selecionar “sem marca” somente quando confirmado, não por ausência de dados.

### A17 — P1 — Shopee perde precisão e descarta dados revisados

**Fonte:** `backend/app/services/shopee_service.py:222`, construção de `payload`; `PublishShopeeProductRequest`.

O preço Decimal é convertido para `float`, contra a regra explícita de dinheiro. A requisição aceita `description` e `attributes`, mas a publicação não os utiliza: envia descrição do produto/nome e omite os atributos do operador.

**Correção:** serializar dinheiro sem passagem por float e transportar/validar os campos revisados. Cobrir o payload exato enviado ao transporte simulado.

### A18 — P1 — Timeout Shopee pode liberar uma publicação duplicada

**Fonte:** `backend/app/services/shopee_service.py:245`, `:256`, consulta de `existing`.

Qualquer exceção leva o registro a `ERROR`, inclusive timeout após envio ao serviço externo. A verificação de publicação existente desconsidera `ERROR`; com outro request ID, uma nova tentativa pode duplicar um anúncio que foi criado remotamente. Além disso, presença de `item_id` vira `ACTIVE` sem confirmação do estado remoto.

**Correção:** distinguir erro comprovado de resultado desconhecido, bloquear repetição até reconciliação e refletir o estado realmente retornado/consultado. O fluxo ML já possui parte desse tratamento e serve como referência arquitetural interna.

### A19 — P1 — Central de publicações não reconcilia Shopee

**Fontes:** `frontend/app/(dashboard)/publications/page.tsx:18`; `backend/app/api/v1/marketplaces.py:reconcile_listing`; `backend/app/services/mercadolivre_service.py:reconcile`.

A lista contém publicações de ambos os canais, mas o formulário exige ID `MLB...`, usa a rota de reconciliação ML e apresenta link como Mercado Livre. Não existe encaminhamento para consulta Shopee.

**Correção:** implementar reconciliação por canal ou desabilitar explicitamente a ação não suportada, sem apresentá-la como funcional.

### A20 — P1 — Pipeline de qualidade e contratos estão quebrados

**Fontes:** `.github/workflows/quality.yml`; `docs/openapi.json`; `frontend/types/api.generated.ts`; `frontend/types/index.ts:85`; `frontend/scripts/test-middleware.mjs:20`.

Ruff e ESLint reprovam o código. O teste do middleware falha antes de validar a maior parte do comportamento. OpenAPI está atrasado em 15 caminhos (auth, páginas/retry/source, aprovação em lote, Shopee e clonador). Hooks usam tipos manuais provisórios.

**Correção:** reparar os testes, regenerar contratos a partir do backend e remover divergências manuais. Só declarar a versão pronta quando a sequência completa do CI passar.

### A21 — P2 — Notificações Mercado Livre somente são armazenadas

**Fontes:** `backend/app/services/marketplace_notification.py:23`; `backend/app/repositories/marketplace_notification.py`; `backend/app/worker.py`.

A inbox persiste a mensagem como não verificada. O worker processa PDFs; não há consumidor que consulte o recurso no ML e atualize produtos, pedidos ou anúncios. Isso é uma implementação parcial legítima de recebimento, mas não equivale a sincronização.

**Correção:** documentar o limite atual e implementar consumidor com consulta autenticada à origem, idempotência, retries e monitoramento antes de prometer atualização automática.

### A22 — P2 — Logout não revoga a sessão

**Fontes:** `backend/app/api/v1/auth.py:57`; `backend/app/core/security.py:32`.

Logout só remove o cookie no navegador. Um token já copiado continua validável por até 30 dias, pois não há sessão revogável. Separadamente, a falha A01 também permite que cookies inválidos/expirados atravessem o proxy.

**Correção:** primeiro resolver A01; depois adotar expiração coerente, revogação e limitação de tentativas de login. Não há proteção contra tentativas repetidas de senha implementada no login analisado; verificar também proteção externa da VPS antes de concluir sobre a implantação.

### A23 — P2 — Upload grande é integralmente carregado em memória

**Fontes:** `backend/app/api/v1/imports.py:48`, `:55`; `frontend/lib/api.ts:117`; `frontend/next.config.ts`.

A leitura em chunks acumula um `bytearray` completo e depois cria uma cópia `bytes`. O proxy permite corpos de cerca de 201 MB; uploads concorrentes ampliam o consumo. O timeout do navegador/proxy é fixo em 120 segundos, independente da velocidade de envio.

**Correção:** fazer streaming para arquivo temporário com hash/limite incremental, consolidar o arquivo após validação e alinhar limites de todas as camadas. Essa é uma fragilidade demonstrável do desenho, mas não foi reproduzido OOM nesta auditoria.

### A24 — P2 — Falhas operacionais deixam pouca evidência e o worker não tem healthcheck

**Fontes:** `backend/app/main.py:38`, `:80`; `backend/app/services/import_service.py:process_import_background`; `backend/app/worker.py`; `docker-compose.yml:worker`.

Os logs genéricos registram sobretudo tipo da exceção/ID, sem contexto técnico suficiente para distinguir falha de storage, banco e extração. A prontidão da API verifica `SELECT 1` e existência do diretório; não verifica escrita, migração aplicada ou progresso do worker. O container worker não tem healthcheck.

**Correção:** logs estruturados com contexto sanitizado e stack trace controlado, correlação entre upload/job/página, verificação de worker e alertas para fila sem progresso. Evitar reintroduzir segredos em logs ao melhorar observabilidade.

## Funções incompletas e melhorias adicionais

1. **Edição de importação incompleta:** o schema permite código, nome, preço e cor, mas não quantidade por caixa nem dimensões, embora ambos sejam extraídos. Ampliar a revisão dos campos efetivamente usados no cadastro.
2. **Fotos acumuladas em reimportações:** `ProductService` acrescenta uma nova imagem com posição padrão zero a cada item importado, sem decisão de substituição/deduplicação. Definir imagem principal e manter a procedência.
3. **Busca não encontra o código do fornecedor:** o repositório pesquisa somente nome e SKU; produtos importados corretamente podem ter SKU nulo. Incluir código do fornecedor como busca explícita.
4. **Clientes HTTP sem ciclo de vida uniforme:** overview cria clientes Shopee e o clonador instancia serviços ML; o shutdown fecha apenas o cliente ML principal. Compartilhar e fechar clientes para evitar recursos pendentes.
5. **Resultado zero sem caminho de conclusão útil:** página preservada com zero candidatos não pode virar produto manualmente; acrescentar ferramenta de revisão por região, sem exigir novo upload do arquivo inteiro.
6. **Cobertura de testes desalinhada:** há testes úteis de normalização, cálculo, revisão e segurança do backend, mas fixtures substituem `require_admin` por padrão. Faltam testes completos de login/proxy/backend, clonagem com fotos, OAuth Shopee ida/volta e publicação com resposta incerta. Asserções devem conferir a URL/payload, não devolver sucesso para qualquer chamada.
7. **Deploy e configuração:** limites de páginas/upload/idioma OCR não são todos repassados pelo Compose. Documentar valores efetivos e tornar a configuração consistente entre API, worker e frontend.
8. **Operação de dados:** validar restauração conjunta de PostgreSQL e volume de arquivos; a existência de volumes persistentes não comprova backup recuperável. Esta auditoria não verificou backups externos da VPS.
9. **Arquitetura:** há consultas e alterações SQL diretamente nas rotas e serviços, além dos repositories. Centralizar operações conforme a convenção do projeto e explicitar fronteiras de transação.
10. **Documentação de estado:** `instrucao.md` ainda declara fases 1–3 concluídas e Shopee `NOT_IMPLEMENTED`; o código agora expõe Shopee e cadastro. Registrar formalmente a divergência e atualizar o estado com evidências, sem alterar silenciosamente as regras fundamentais.

Estoque, pedidos, vendas, relatórios e configurações continuam como telas de recurso indisponível. Amazon e TikTok não possuem implementação operacional. São lacunas de escopo já declaradas, distintas dos erros de recursos que se apresentam como concluídos.

## O que está bem encaminhado

- Identidade interna por UUID e separação de código do fornecedor.
- Dinheiro com Decimal/NUMERIC no motor de precificação e no fluxo principal de importação; a regressão Shopee é localizada.
- Tokens de marketplace cifrados na persistência pelo serviço.
- PDF original e evidência por página preservados, com commits incrementais e limite de tempo por página.
- Campos ausentes preservados e validação de nome/código reais antes de cadastrar produtos importados.
- Fluxo ML com tentativa OAuth vinculada a navegador/operador, registro prévio da publicação e estado incerto em falhas externas.
- Processamento assíncrono de PDF separado da requisição de upload.

Esses pontos reduzem o trabalho de recuperação, mas não neutralizam as falhas apontadas.

## Ordem recomendada de execução e critérios de aceite

1. **Autenticação e logs:** corrigir A01/A03; testes negativos devem comprovar que credenciais inválidas nunca recebem privilégio e tokens não aparecem em logs.
2. **Importação real:** corrigir segmentação, revisão, ignorados, códigos repetidos e OCR. Usar o PDF de 35 MB como aceitação, comparando amostras reais de cada layout; completar upload → persistência PostgreSQL → revisão → cadastro → consulta. A contagem de candidatos, sozinha, não basta.
3. **Remover sucessos fictícios e completar clonador:** cadastro deve persistir ou ser declarado indisponível; fotos devem existir no storage e no banco; repetir uma operação deve ter resultado definido.
4. **Shopee:** completar configuração, OAuth, dados reais, atributos, Decimal e reconciliação; verificar a documentação oficial vigente antes de implementar os contratos externos. Não considerar a integração completa apenas por existir cliente HTTP e tela.
5. **Contratos e CI:** atualizar OpenAPI/tipos e passar testes, lint, build e migração em banco dedicado.
6. **Validação controlada na VPS:** confirmar o commit implantado, configuração efetiva e saúde de API/worker/storage; testar com evidências sanitizadas e só então considerar a versão validada.

Não foi atribuído percentual de conclusão: a quantidade de arquivos e testes não mede prontidão operacional. Este documento é um conjunto de achados comprovados por código e execuções locais, não uma garantia de ausência de outros defeitos ou uma auditoria de segurança exaustiva da infraestrutura.
