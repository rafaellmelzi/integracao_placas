# Preparação de nuvem — diagnóstico e validação

Data: 08/10/2026. Base Git: `9973898`. Este relatório registra a preparação inicial, anterior ao commit revisado em `REVISAO_PRE_DEPLOY.md`. Nenhum push, publicação ou recurso de nuvem criado. Nenhuma consulta ou alteração no AUTCOM nesta etapa. Containers locais existentes não foram reiniciados.

## Problemas encontrados e correções

| Problema | Causa | Correção |
|---|---|---|
| Startup inadequado para plataforma | Comando fixo e fluxo local com seed | Entrypoint com PORT dinâmico, um worker, sem seed/migração automática; Compose preserva override local |
| Credenciais poderiam entrar na imagem | COPY de todo o contexto, sem dockerignore | Exclusão de env, Git, logs, bancos locais, chaves e fixtures |
| Log rastreado | `server.log` já estava no índice Git | Removido apenas do índice, preservado em disco; logs ignorados |
| Exceções poderiam revelar conexão/chaves | Alguns endpoints retornavam texto cru de erros | Respostas genéricas, parâmetros SQL ocultos, redaction central de mensagens/tracebacks e chaves configuradas |
| Configuração PostgreSQL fragmentada | Runtime e Alembic criavam engines separadamente | Factory única, psycopg 3, TLS em cloud, pool pequeno e schema privado |
| Enums repetidos na migração inicial | Mesmo enum declarado em múltiplas tabelas | Criação única explícita, sem CREATE TYPE automático repetido; downgrade remove tipos |
| Pooler pode ignorar startup options | Dependência de options para search_path | SET no evento de conexão, fora de transação; guia exige Session pooler |
| AUTCOM privado inacessível na nuvem | Connector tentaria usar configuração de rede local | Cloud não inicializa connector; status PRIVATE_NETWORK_UNAVAILABLE e lista vazia |
| API pública consumiria créditos do provedor | Rotas antes não exigiam token | X-API-Key em cloud; admin local, CORS restrito e health público sem consulta ao provedor |
| Catálogo poderia fazer carga externa mesmo desativado | Cache vazio caía no fetch apesar de FIPE_AUTO_UPDATE=false | Retorno local inclusive vazio; sync em massa bloqueado por configuração |
| Builds futuros resolveriam outras versões | requirements com limites inferiores apenas | requirements-cloud.lock de Python 3.12/Linux validado; requirements local preservado |

## Arquivos desta etapa

- Container/dependências: `Dockerfile`, `.dockerignore`, `requirements-cloud.lock`.
- Configuração/segurança: `.gitignore`, `.env.production.example`, `app/core/config.py`, `app/core/security.py`.
- Runtime/health: `app/start.py`, `app/main.py`, `app/health.py`, `app/api/endpoints.py`.
- Banco: `app/db/connection.py`, `app/db/database.py`, `alembic/env.py`, `alembic/versions/001_initial_schema.py`, `app/scripts/migrate.py`.
- Serviços/contrato: `app/services/fipe_service.py`, `app/services/parts_compatibility_service.py`, `app/schemas/schemas.py`, `app/seeds/seed_data.py` (erro genérico).
- Testes: `tests/test_cloud.py`, `tests/test_postgresql_cloud.py`.
- Documentação: `DEPLOY_KOYEB_SUPABASE.md`, este relatório.
- `server.log`: exclusão do índice preparada, arquivo local preservado.

As alterações anteriores do matcher, contrato normalizado, testes e configuração local foram preservadas e integram a entrega revisada. Consulte `REVISAO_PRE_DEPLOY.md` para o inventário incluído e `VALIDACAO_MATCHER.md` para a etapa anterior. Nenhuma dessas correções foi descartada.

## Resultados

| Validação | Resultado |
|---|---|
| ApplicationMatcher | **93 aprovados, 0 falhas** |
| Suíte completa + PostgreSQL descartável | **162 aprovados, 0 falhas**, 182 warnings |
| Suíte sem acesso à rede | **161 aprovados, 0 falhas, 1 ignorado**, 177 warnings |
| PostgreSQL 16 real e isolado | Upgrade/downgrade/reupgrade completos; três enums; schema privado; CRUD e readiness com role sem CREATE |
| Migração pelo comando de produção | `python -m app.scripts.migrate` aplicado em schema separado no banco descartável |
| Alembic offline PostgreSQL | SQL gerado até 004_fipe_cache_tracking, com três CREATE TYPE |
| Build Docker | Concluído com lock de dependências |
| Conteúdo da imagem | Sem .env, .git, server.log, autoparts.db ou testes |
| Imagem com porta 9123 | Liveness/readiness HTTP 200; PostgreSQL conectado e revisão correta |
| Imagem em cloud sem rede, porta 9124 | Liveness 200; readiness 503 sem banco; negócio sem token 401; admin 404; respostas sem credenciais |
| Recursos locais do smoke test | Limitados a 512 MB/0,1 CPU; aproximadamente 86 MB em repouso, sem ensaio de carga |
| Contrato cloud | Teste exige token; AUTCOM não inicializado mesmo com ERP_ENABLED=true; parts_count=0, parts=[], disponibilidade NOT_QUERIED |
| Segurança | Testes de redaction em argumentos, URLs, senha URL-decoded, Bearer e traceback; erros de readiness sem detalhes sensíveis |
| Preservação | SHA-256 de .env, docker-compose.yml e requirements.txt iguais antes/depois; containers locais saudáveis |

O teste ignorado na suíte sem rede é exclusivamente o teste opt-in de PostgreSQL; ele passou na execução completa com banco isolado. Os warnings restantes incluem deprecações preexistentes; não foram suprimidas falhas. A falha intermediária de um teste novo foi a expectativa de revisão incorreta no próprio teste (002 em vez do head 004); o teste agora consulta o head Alembic real.

Os testes não usam internet e os cenários do provedor são mockados. O PostgreSQL de teste foi criado somente na rede Docker de validação. Seu teste de downgrade recusa qualquer host diferente de `integracao-cloud-validation-pg` e qualquer banco diferente de `validation`.

## Limitações e próximos passos

Não houve conexão a Supabase/Koyeb reais, nem validação HTTPS em nuvem. É necessário criar os recursos gratuitos manualmente, configurar secrets e grants, migrar no Supabase e aprovar a publicação. Limites e instruções oficiais estão vinculados no guia. Supabase Free pode pausar e não oferece backup automático; Koyeb Free suspende após inatividade.

Sem uma ponte autorizada, AUTCOM permanece explicitamente indisponível em cloud. O erro MySQL 2013 observado anteriormente continua em investigação local separada; nenhuma credencial ou rede foi alterada nesta preparação.

Não se deve interpretar a lista vazia cloud como estoque zero. Não são retornados preços/estoque simulados. O frontend futuro precisa manter o token somente no servidor, e o acesso de usuários finais requer autenticação/quotas próprias.

Siga `DEPLOY_KOYEB_SUPABASE.md` para revisão Git, criação manual, variáveis, migração, smoke tests, backups e rollback.
