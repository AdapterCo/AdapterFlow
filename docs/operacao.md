# Operação e recuperação

## Dados legados e atualização

A migration `004_audit_hardening` adiciona proveniência/obsolescência de preços, tentativas OAuth/publicação, constraints e índices. Preços anteriores exigem recálculo. CHECKs `NOT VALID` protegem novas escritas sem reescrever dados antigos por suposição.

Execute `python -m app.maintenance` para diagnóstico somente leitura: IDs de contas com tokens legados, produtos com múltiplos fornecedores/placeholders e canais com padrões duplicados. Vários fornecedores no mesmo produto podem ser legítimos; o programa não presume erro de identidade.

Com backup e chave configurada, `python -m app.maintenance --encrypt-legacy` cifra tokens existentes sem exibi-los e remove `settings` antigos dessas contas. Alternativamente, reconecte cada conta. Plaintext é rejeitado pela integração atualizada. Não troque a chave sem recifragem.

Revise identidades historicamente unidas por SKU, placeholders e taxas sem fonte usando o catálogo original. Não há separação automática nem substituição por valores presumidos. Resolva padrões duplicados escolhendo o correto na interface. Valide CHECKs no PostgreSQL após tratar os dados legados.

## Backup consistente

Retenção e destino dependem da política real da operação. Preserve banco, storage, configuração sensível e chave Fernet, com criptografia e acesso restrito.

Procedimento em manutenção, no shell Linux do host Docker:

1. Interrompa operações e execute `docker compose stop adapterflow-web worker backend`; mantenha PostgreSQL ativo.
2. Execute `docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > database.dump`.
3. Execute `docker compose run --rm --no-deps -T --entrypoint tar backend -C /app/storage -cf - . > storage.tar`.
4. Registre versão do código, revisão Alembic e checksums SHA-256; transfira as cópias para o destino aprovado e religue os serviços.

Restaure em ambiente isolado: banco vazio com `pg_restore`, volume separado e chave correspondente. Confira revisão, contagens, imagens/PDFs e revisão de importação. Nunca ensaie restauração sobre produção. A migration não oferece downgrade destrutivo: rollback exige backup consistente e código compatível. O procedimento não foi executado nesta estação.

Volumes existentes devem permitir leitura/escrita pelo UID 1001 do novo container sem root. Verifique as permissões do volume em manutenção; não altere permissões recursivamente em diretórios fora do storage.

## Falhas

Se o backend parar no Alembic com `socket.gaierror: Name or service not known`,
o endereço do banco não foi resolvido. Uma causa possível era a interpolação direta
da senha na `DATABASE_URL` do Compose: `@` podia alterar o host interpretado.
O Compose agora envia host, porta e credenciais separadamente; backend, worker e
Alembic usam `URL.create` do SQLAlchemy, preservando a senha original.
Não altere a senha do banco existente para contornar esse erro.
Em desenvolvimento/CI, `DATABASE_URL` continua disponível quando `DATABASE_HOST`
não está definido; nessa URL textual, credenciais devem estar codificadas para URL.
No `.env` do Compose, coloque valores que contenham `$` entre aspas simples para
preservá-los literalmente.

Após atualizar o código, execute `docker compose up -d --build backend worker adapterflow-web`.
Se a falha de resolução persistir, teste o DNS da rede interna sem mostrar credenciais:

```bash
docker compose run --rm --no-deps backend python -c "import socket; socket.getaddrinfo('db', 5432); print('DNS db OK')"
```

Fonte: [SQLAlchemy — criação de URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#creating-urls-programmatically).

Extração tem timeout de 300 segundos; o worker Docker limita memória/CPU. Jobs abandonados em PROCESSING por dez minutos tornam-se FAILED; reenviar cria nova fonte imutável. O subprocesso não recebe credenciais e usa diretório temporário, mas não é um sandbox completo de sistema operacional.

UNKNOWN/IN_PROGRESS bloqueiam nova publicação do mesmo produto/conta. Confira a conta e informe o ID externo verdadeiro em Publicações para reconciliar; o backend verifica vendedor. Se nenhum anúncio existir, liberar tentativa exige investigação operacional: não há botão que presume ausência externa.

`/health` é liveness; `/api/v1/ready` verifica banco e existência do storage. Logs usam identificador de incidente/job e classe de erro, sem headers/tokens. Monitor externo, política de alertas e ensaio de carga ainda dependem do ambiente real.

Fontes originais são preservadas. Imagens produzidas por extração que falhou são removidas pelo serviço. Não há purga automática de PDFs antigos sem política de retenção definida.
