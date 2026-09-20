# Recebimento de notificações do Mercado Livre

No campo **URL de notificações**, cadastrar:

```text
https://flow.adapterco.com.br/api/v1/marketplaces/mercadolivre/notifications
```

Esta URL é diferente da URI de redirect OAuth. Não substitua `MERCADOLIVRE_REDIRECT_URI`.
O domínio deve encaminhar para o frontend desta aplicação na VPS. A rota funciona por POST JSON;
abri-la no navegador não testa o recebimento. Cloudflare Access, desafios interativos ou
autenticação adicional no proxy não podem bloquear esse POST.

## Comportamento implementado

- O backend valida os campos da notificação, limita o corpo a 16 KiB e confere
  `application_id` contra `MERCADOLIVRE_APP_ID` do servidor.
- Persiste na tabela `marketplace_notifications` antes de responder HTTP 200.
- Retentativas com `_id`, ou com os mesmos dados de evento e `received`, não geram duplicatas.
  Sem identificador e sem horário original, preserva cada entrega para não perder eventos distintos.
- Falha ao persistir retorna erro, permitindo nova tentativa do provedor.
- Apenas esse POST dispensa Basic Auth. As operações administrativas continuam protegidas.
- O estado salvo é `RECEIVED_UNVERIFIED`: o ID da aplicação não autentica a origem.
  Campos adicionais são descartados; tokens e cabeçalhos não são persistidos.

**Escopo:** esta entrega implementa recebimento durável. Não há consumidor automático desta
caixa nem sincronização por notificações. Não habilitar tópicos supondo que pedidos, estoque,
mensagens ou anúncios serão atualizados automaticamente. A reconciliação de anúncios existente
continua explícita. Um futuro consumidor deve consultar a API oficial autenticada e verificar
a conta antes de atualizar dados; nunca usar o payload recebido como verdade de negócio.

## Publicação e validação

1. Atualizar o código e reconstruir backend e frontend na VPS usando o procedimento de deploy
   existente. O backend executa `alembic upgrade head`; a revisão `005_notification_inbox`
   cria a tabela sem modificar produtos ou anúncios.
2. Confirmar `MERCADOLIVRE_APP_ID` no ambiente do backend e saúde dos serviços.
3. Cadastrar a URL acima no painel e testar com uma notificação real do Mercado Livre.
4. Conferir HTTP 200 e registro na tabela; observar latência em produção. O provedor exige
   resposta em até 500 ms; a rota não faz consultas externas, mas essa latência depende da VPS.

Os testes locais usam mensagens sintéticas isoladas e mocks, sem envio ao Mercado Livre.
O teste de persistência/deduplicação PostgreSQL requer `TEST_DATABASE_URL` e está incluído no CI.

Fontes oficiais consultadas em 20/09/2026:
- [Notificações](https://developers.mercadolivre.com.br/produto-receba-notificacoes)
- [Segurança da aplicação](https://developers.mercadolivre.com.br/en_us/category-prediction-resource/application-security)
