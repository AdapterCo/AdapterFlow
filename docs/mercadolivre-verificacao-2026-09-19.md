# Mercado Livre: contratos verificados

Consulta oficial em 19/09/2026. Alguns acessos diretos retornaram 403; também foram usados resultados indexados das páginas oficiais. Verificação documental não comprova habilitação de conta/aplicação.

| Operação | Fonte oficial |
|---|---|
| OAuth, state por tentativa, refresh de uso único | https://developers.mercadolivre.com.br/autenticacao-e-autorizacao |
| Predição autenticada e categorias | https://developers.mercadolivre.com.br/pt_br/categorizacao-de-produtos |
| Upload multipart e IDs das imagens | https://developers.mercadolivre.com.br/en_us/working-with-pictures |
| Validação de anúncio | https://developers.mercadolivre.com.br/pt_br/validador-de-publicacoes |
| Criação e consulta de anúncio | https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos |
| Descrição após criar anúncio | https://developers.mercadolivre.com.br/pt_br/produto-consulta-de-usuarios/descricao-de-produtos |

O cliente usa Bearer, formulário no token endpoint, JSON numérico diretamente de Decimal e bytes de imagens reais. State é armazenado como hash, expira, vincula operador/cookie e é consumido uma vez. Refresh usa lock de linha e tokens são cifrados com Fernet.

Quantidade, condição, categoria, atributos e perfil são explícitos. Estado vem da resposta externa; falha da descrição não apaga o anúncio criado. Timeout não autoriza repetir POST.

Limites: não houve OAuth/publicação real nesta sessão. PKCE não é enviado: aplicações que o exigem precisam dessa extensão antes de uso. Regras de categoria/conta/formato exigem homologação real. Taxas precisam de fonte informada pelo operador; não são presumidas nem buscadas automaticamente.
