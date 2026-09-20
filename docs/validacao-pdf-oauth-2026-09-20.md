# Investigação de upload PDF e conexão Mercado Livre — 20/09/2026

## Falhas reproduzíveis no código

- O Next.js 15.5.25 instalado usa `middlewareClientMaxBodySize=10485760` por padrão.
  O middleware cobre `/api/v1/imports/upload`; corpos maiores eram truncados no proxy,
  apesar de o backend permitir 200 MiB. O limite agora é 201 MiB, incluindo margem para
  multipart, com timeout do proxy de 120 segundos (antes, 30). O backend mantém o limite
  de arquivo de 200 MiB. O frontend informava 50 MB e exigia um checkbox de layout:
  ambos foram corrigidos; PDFs com extensão válida não dependem do MIME fornecido pelo navegador.
- A extração duplicava a leitura de imagens na obtenção de texto. Essa cópia foi removida.
  Blocos que contêm cabeçalhos de vários produtos agora preservam cada linha e coordenada;
  antes, apenas o primeiro código do bloco se tornava candidato. Na página 100 do catálogo
  completo LEHMOX, o código ST-330 é preservado após a correção.
- A cópia temporária para o subprocesso agora usa blocos de 1 MiB, sem carregar outra cópia
  integral do PDF na memória do worker. Timeout da extração recebe mensagem específica.
- O retorno OAuth sem `state` era rotulado incorretamente como recusa do Mercado Livre.
  A mensagem agora explica a falta da tentativa iniciada no AdapterFlow; a validação de
  segurança permanece obrigatória. A interface mostra o App ID e o redirect configurados
  no servidor para detectar divergências entre aplicações, sem exibir o Client Secret.
  O botão Autorizar conta não depende mais de terminar a verificação de contas existentes.
- Falhas de transporte da API e indisponibilidade do provedor têm mensagens distintas.
  O frontend ganhou healthcheck que atravessa seu próprio middleware/proxy até a readiness
  da API, em vez de considerar apenas que o processo Next está rodando.

## Evidência local

- Backend: 77 testes passaram, 2 testes PostgreSQL ficaram sem execução local por falta
  de `TEST_DATABASE_URL`. Estes continuam configurados no CI.
- Fluxo OAuth HTTP com serviço real e provedor/persistência simulados: geração de URL,
  state, cookie HttpOnly/Secure, consumo da tentativa, credenciais criptografadas e rejeição
  de reutilização. Isso não é uma autorização real da conta do proprietário.
- Frontend Next real + API de teste local: Basic Auth, state e cookie atravessam o proxy.
  Upload multipart do PDF completo LEHMOX: 154.095.339 bytes, incluindo envelope, com
  hash SHA-256 idêntico entre origem e destino. O teste padrão do CI usa 24 MiB sintéticos.
- Subprocesso real de extração, sem inserir produtos no banco:

| Arquivo local | Páginas | Candidatos extraídos | Tempo local aproximado |
| --- | ---: | ---: | ---: |
| LEHMOX 2026.09.16 (02) | 107 | 938 | 27 s |
| STARMEGA 2026.09.16 (02) | 45 | 286 | 12 s |

As contagens são candidatos para revisão, não uma certificação de que todos representam
produtos distintos ou de que os campos estão corretos. No LEHMOX, 19 candidatos não têm
nome e 104 não têm preço; no STARMEGA, 33 e 93, respectivamente. Valores ausentes continuam
ausentes. A extração por códigos/coordenadas não é um leitor universal de qualquer layout;
o checkbox não tornava essa limitação mais segura e não é mais exigido. PDFs digitalizados
continuam exigindo OCR habilitado; os dois catálogos testados contêm texto nativo.

## Publicação e confirmação na VPS

```bash
git pull --ff-only origin master
docker compose config --quiet
docker compose up -d --build --remove-orphans
docker compose ps
docker compose exec adapterflow-web node scripts/healthcheck.mjs
```

O último comando sai com código zero quando o caminho frontend → API → readiness funciona.
Confira em Marketplaces o App ID atual e o redirect, depois use **Autorizar conta** no mesmo
navegador e origem HTTPS. Não monte o link OAuth manualmente. Confira que o secret do `.env`
pertence ao App ID mostrado; a tela não tem como confirmar essa correspondência antes de
trocar o código com o provedor.

Reenvie o PDF original após atualizar: arquivos anteriormente truncados não podem ser
recuperados a partir do upload incompleto. O trabalho segue para revisão antes de criar
produtos. Se houver nova falha, o estado do job e os logs do worker são a evidência necessária:

```bash
docker compose logs --since=10m --tail=100 adapterflow-backend adapterflow-web worker
```

Limites da validação: não houve acesso à VPS, teste Docker local ou autorização de conta
real nesta estação. Não há garantia de que proxies externos (Cloudflare/Traefik) aceitem
o mesmo tamanho de upload; se retornarem 413, o limite externo também precisa ser ajustado.

Fontes: [PyMuPDF — flags de extração](https://pymupdf.readthedocs.io/en/latest/app1.html),
[Mercado Livre — OAuth](https://developers.mercadolivre.com.br/autenticacao-e-autorizacao).
O limite e a opção específicos do Next.js 15 foram conferidos no código da versão instalada
(`next/dist/server/body-streams.js`, `config-shared.js` e `config-shared.d.ts`).
