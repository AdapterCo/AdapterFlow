> Registro anterior: consulte [a verificação de 19/09/2026](../mercadolivre-verificacao-2026-09-19.md) e [as correções](../correcoes-2026-09-19.md) para contratos e limitações atuais. Não representa homologação em produção.

# Mercado Livre — Integração Oficial

## Status: IN_DEVELOPMENT (Fase 3)

## Documentação Oficial
- Portal de Desenvolvedores: [https://developers.mercadolivre.com.br/](https://developers.mercadolivre.com.br/)
- Guia de Autenticação OAuth 2.0: [https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)
- Publicação de Produtos: [https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos](https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos)
- Data da última verificação: 2026-09-18

---

## 1. Autenticação (OAuth 2.0 Authorization Code Flow)

### 1.1 Requisição de Autorização (Brasil - MLB)
O usuário clica no botão "Conectar Conta" e é redirecionado para:
`https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={APP_ID}&redirect_uri={REDIRECT_URI}&state={STATE}`

- `client_id`: ID da aplicação obtido no portal de desenvolvedores.
- `redirect_uri`: URL de callback registrada (ex: `http://localhost:3099/marketplaces/callback`).
- `state`: Identificador único aleatório para prevenção de ataques CSRF.

### 1.2 Troca do Código por Tokens
Após a autorização, o Mercado Livre redireciona para a `redirect_uri` com o parâmetro `?code=TG-xxxxx`. O backend realiza a troca:
- **Endpoint:** `POST https://api.mercadolibre.com/oauth/token`
- **Headers:** `Content-Type: application/x-www-form-urlencoded`
- **Body:**
  - `grant_type=authorization_code`
  - `client_id={APP_ID}`
  - `client_secret={CLIENT_SECRET}`
  - `code={CODE}`
  - `redirect_uri={REDIRECT_URI}`
- **Resposta Sucesso (JSON):**
  - `access_token`: Token JWT temporário (duração de 6 horas / 21600 segundos).
  - `token_type`: "Bearer"
  - `expires_in`: 21600
  - `scope`: "offline_access read write"
  - `user_id`: ID do vendedor no Mercado Livre.
  - `refresh_token`: Token utilizado para renovação sem intervenção do usuário.

### 1.3 Renovação Automática de Tokens (Refresh Token)
- **Endpoint:** `POST https://api.mercadolibre.com/oauth/token`
- **Body:**
  - `grant_type=refresh_token`
  - `client_id={APP_ID}`
  - `client_secret={CLIENT_SECRET}`
  - `refresh_token={REFRESH_TOKEN}`

---

## 2. Endpoints Utilizados no AdapterFlow

| Finalidade | Método | Endpoint |
|---|---|---|
| Dados do Vendedor Conectado | GET | `https://api.mercadolibre.com/users/me` |
| Predição de Categorias | GET | `https://api.mercadolibre.com/sites/MLB/domain_discovery/search?limit=1&q={TITLE}` |
| Atributos da Categoria | GET | `https://api.mercadolibre.com/categories/{CATEGORY_ID}/attributes` |
| Validação Prévia de Anúncio | POST | `https://api.mercadolibre.com/items/validate` |
| Publicação de Novo Anúncio | POST | `https://api.mercadolibre.com/items` |
| Atualização de Preço/Estoque | PUT | `https://api.mercadolibre.com/items/{ITEM_ID}` |

---

## 3. Estrutura do Payload de Publicação (`POST /items`)

```json
{
  "title": "Produto Teste Lehmox",
  "category_id": "MLB123456",
  "price": 89.90,
  "currency_id": "BRL",
  "available_quantity": 10,
  "buying_mode": "buy_it_now",
  "condition": "new",
  "listing_type_id": "gold_special",
  "description": {
    "plain_text": "Descrição completa do produto..."
  },
  "pictures": [
    { "source": "https://..." }
  ],
  "attributes": [
    { "id": "BRAND", "value_name": "LEHMOX" },
    { "id": "MODEL", "value_name": "LE-520" },
    { "id": "ITEM_CONDITION", "value_name": "Novo" }
  ]
}
```

---

## 4. Segurança e Regras de Negócio
1. **Credenciais:** `MERCADOLIVRE_APP_ID` e `MERCADOLIVRE_CLIENT_SECRET` NUNCA são expostos ao frontend.
2. **Tokens:** Armazenados exclusivamente no banco de dados. Nunca retornados em endpoints públicos.
3. **Validação Obrigatória:** Antes de chamar `POST /items`, o sistema executa `POST /items/validate` para evitar falhas ou penalidades de conta.
