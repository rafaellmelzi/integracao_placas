# Implantação: Koyeb + Supabase

Preparação validada em 08/10/2026. Nenhuma aplicação publicada ou recurso de nuvem criado nesta etapa. O AUTCOM e os containers locais existentes não foram modificados. O frontend na Vercel fica para uma etapa posterior.

## 1. Estado do repositório

A base desta entrega é `9973898`. As correções de compatibilidade, testes e preparação para nuvem compõem o commit revisado antes do primeiro deploy. `VALIDACAO_MATCHER.md` e `VALIDACAO_NUVEM.md` registram as validações; `REVISAO_PRE_DEPLOY.md` registra a revisão final e o inventário incluído. Consulte `git log -1` para o hash da entrega.

`docker-compose.yml`, `requirements.txt` (incluindo PyMySQL) e `.env` foram preservados durante esta etapa. O Compose continua usando seu fluxo local de migração, seed e Uvicorn. A imagem, quando executada sem o override do Compose, usa o novo entrypoint de produção.

Antes de enviar ao GitHub:

```powershell
git status --short
git diff --check
git diff
git diff --cached --stat
git check-ignore .env
```

Revise e commite explicitamente os arquivos necessários, incluindo as correções anteriores. Não use `git add -f` em arquivos ignorados. `server.log` e `vehicle_sync_checkpoint.json` foram removidos apenas do índice Git; os arquivos locais foram preservados. Logs, checkpoints, bancos locais, `.env`, arquivos de secrets e certificados privados ficam fora do Git e do contexto Docker. `.env.production.example` contém somente placeholders.

A auditoria comparou os segredos atuais de provedor/AUTCOM com arquivos rastreados e diffs dos 19 commits existentes, sem encontrar correspondências. A URL SQLite padrão é configuração pública, não uma credencial. Essa verificação não detecta chaves antigas desconhecidas: antes de tornar o repositório público, revise também o histórico com um scanner de segredos. Se encontrar uma chave antiga, revogue-a antes da publicação; não reescreva o histórico compartilhado sem coordenação.

## 2. Limites e desenho de produção

O serviço usa **um worker**, pool SQLAlchemy de **duas conexões**, sem overflow, sem seed e sem migração automática no startup. O catálogo FIPE não é expandido automaticamente e a sincronização em massa fica desativada. O filesystem do container não armazena dados persistentes; o banco é PostgreSQL.

A instância Free do Koyeb entra em suspensão após uma hora sem tráfego; a primeira requisição pode ter latência de inicialização. [Scale-to-zero](https://www.koyeb.com/docs/run-and-scale/scale-to-zero).

O Koyeb oferece uma instância web gratuita por organização, com 512 MB de RAM, 0,1 vCPU e 2 GB de SSD, nas regiões elegíveis. Confirme disponibilidade, suspensão por inatividade e cobrança no painel antes de criar o serviço. A configuração privilegia baixo consumo; importações grandes e tarefas longas devem ser executadas separadamente. [Koyeb: instâncias](https://www.koyeb.com/docs/reference/instances), [preços](https://www.koyeb.com/docs/faqs/pricing).

O Supabase Free possui limite de banco e pode pausar projetos inativos; não deve ser tratado como serviço com disponibilidade garantida. O plano gratuito não inclui backups automáticos: mantenha dumps manuais externos. Não habilite complementos pagos ou upgrades automáticos sem aprovação. [Planos](https://supabase.com/pricing), [pausa](https://supabase.com/docs/guides/platform/free-project-pausing), [backups](https://supabase.com/docs/guides/platform/backups).

## 3. Preparar o Supabase — ação manual

1. Crie ou selecione um projeto no plano Free. Não importe dados de produção do cliente nesta etapa.
2. Copie do painel **Connect** a conexão do **Session pooler**, porta **5432**. Ela funciona em redes IPv4 e é apropriada para um backend persistente. Não use o Transaction pooler, porta 6543, nesta configuração: ele tem restrições de sessão/prepared statements. A conexão direta exige IPv6 ou disponibilidade de IPv4 apropriada. Não adivinhe o host. [Conexões oficiais](https://supabase.com/docs/guides/database/connecting-to-postgres).
3. Use TLS: `DB_SSL_MODE=require` é obrigatório no exemplo. Para validação de certificado/hostname, utilize `verify-full` e o certificado CA indicado pelo Supabase, disponibilizado como secret fora do repositório (`PGSSLROOTCERT`).
4. Use o schema privado `integracao_placas`. Não o adicione aos schemas expostos pela Data API do Supabase. Esta aplicação acessa PostgreSQL diretamente com SQLAlchemy; não necessita de `anon` ou `service_role` keys. [Proteção do banco](https://supabase.com/docs/guides/database/secure-data).

As quatro migrações existentes são executadas por Alembic. A revisão atual é `004_fipe_cache_tracking`. Os enums PostgreSQL são criados uma vez e removidos no downgrade completo. A tabela `alembic_version`, tabelas e enums ficam no schema configurado. O search_path e o timeout são definidos na sessão efetiva, sem depender de startup options que um pooler possa ignorar.

### Credenciais distintas para migração e runtime

Execute primeiro a migração com a conexão administrativa do projeto, somente na sua máquina ou em um job controlado. Depois, crie um usuário de runtime no SQL Editor. **Substitua o placeholder por uma senha gerada, privada; não salve o SQL preenchido no Git nem em logs.**

```sql
CREATE ROLE integracao_runtime LOGIN PASSWORD '<SENHA_GERADA_FORA_DO_GIT>';
GRANT CONNECT ON DATABASE postgres TO integracao_runtime;
GRANT USAGE ON SCHEMA integracao_placas TO integracao_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA integracao_placas TO integracao_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA integracao_placas TO integracao_runtime;
-- Execute como o mesmo dono que aplica as migrações (postgres no exemplo).
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA integracao_placas
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO integracao_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA integracao_placas
  GRANT USAGE, SELECT ON SEQUENCES TO integracao_runtime;
```

Não conceda CREATE no schema ao runtime. Não use esse usuário para migrar. Para roles personalizadas no pooler, o username usa `integracao_runtime.<PROJECT_REF>`; confirme o formato e copie o host correto do projeto. [Supabase: usuário do pooler](https://supabase.com/docs/guides/troubleshooting/tenant-or-user-not-found).

Senhas com `@`, `#`, `%`, `:`, `/` etc. precisam ser codificadas para URL. Não imprima a URL completa. Exemplo estrutural:

```text
postgresql+psycopg://integracao_runtime.PROJECT_REF:URL_ENCODED_PASSWORD@SESSION_POOLER_HOST:5432/postgres
```

## 4. Variáveis de produção

Copie `.env.production.example` para um arquivo **fora do repositório**, com acesso restrito, e preencha-o. Não modifique o `.env` local. No Koyeb, associe valores confidenciais a **Secrets**, em vez de colocá-los no código ou em comandos de build.

| Variável | Valor/uso |
|---|---|
| `APP_ENV` / `DEPLOYMENT_MODE` | `production` / `cloud` |
| `PORT` | `8000`; o entrypoint também aceita a porta definida pela plataforma |
| `DATABASE_URL` | URL PostgreSQL do **runtime**, secret |
| `DATABASE_SCHEMA` | `integracao_placas` |
| `DB_SSL_MODE` | `require` ou `verify-full` com CA |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `2` / `0` |
| `DB_POOL_TIMEOUT` / `DB_CONNECT_TIMEOUT` | `5` / `5` segundos |
| `DB_STATEMENT_TIMEOUT_MS` | `10000`; para job de migração pode usar `60000` |
| `API_ACCESS_TOKEN` | Secret aleatório com pelo menos 32 caracteres |
| `VEHICLE_PROVIDER` | `FIPEPLACA` |
| `VEHICLE_API_URL` | URL já usada pela integração FipePlaca |
| `FIPEPLACA_API_KEY` | Secret existente do provedor; não altere a chave local |
| `PARTS_PROVIDER` | `LOCAL_DB` |
| `FIPE_SYNC_ENABLED` / `FIPE_AUTO_UPDATE` | `false` / `false` |
| `FIPE_CACHE_ENABLED` / `PLATE_CACHE_TTL_DAYS` | `true` / `90` |
| `ERP_ENABLED` | `false`; cloud bloqueia o connector mesmo se marcado true por engano |
| `CORS_ORIGINS` | `[]`; posteriormente lista JSON de origens exatas |
| `MIGRATION_DATABASE_URL` | Somente no job de migração, URL administrativa; **não cadastrar no serviço web** |

Não cadastre `ERP_DB_HOST`, `ERP_DB_USER`, `ERP_DB_PASSWORD` ou queries privadas no Koyeb. Não use MOCK em produção. A configuração falha explicitamente se faltar PostgreSQL/TLS/token, se houver MOCK ou se FIPE em massa estiver habilitado.

As rotas `/api/v1/*`, exceto `/api/v1/health`, exigem `X-API-Key` em cloud. O token é compartilhado, adequado para esta etapa de backend controlado; antes de abrir o produto a usuários finais, implemente autenticação individual e quotas. Não coloque o token em JavaScript do navegador ou em variáveis `NEXT_PUBLIC_*`. O futuro frontend Vercel deve usar um proxy no servidor com o segredo protegido. `/admin` permanece disponível apenas localmente.

## 5. Build, testes e migração — comandos manuais

Na raiz do projeto, com Docker Desktop:

```powershell
docker build -t integracao-placas:validated .
docker run --rm --network none --mount "type=bind,source=$($PWD.Path),target=/app,readonly" -w /app --entrypoint python integracao-placas:validated -m pytest -p no:cacheprovider -q --disable-warnings
docker run --rm --network none --mount "type=bind,source=$($PWD.Path),target=/app,readonly" -w /app --entrypoint python integracao-placas:validated -m pytest tests/test_application_matcher.py -p no:cacheprovider -q
```

O teste PostgreSQL é opcional na execução acima e só aceita o host de validação e banco descartável descritos no próprio teste. Não aponte `TEST_POSTGRES_URL` para Supabase ou AUTCOM. A validação desta etapa também executou a suíte completa contra um PostgreSQL 16 descartável: upgrade/downgrade/reupgrade, três enums, schema privado e usuário sem privilégio DDL. Não foi testada uma conexão real ao Supabase, pois nenhum recurso foi criado.

`requirements-cloud.lock` fixa as versões Python/Linux validadas na imagem. `requirements.txt` permanece como recebido. Atualize o lock somente junto com nova validação completa. Para rollback reproduzível, retenha a imagem validada e registre seu digest; a tag do Python base ainda pode mudar em builds futuros.

Prepare, por exemplo, `C:\secrets\integracao-placas-migrate.env` com as variáveis da tabela, `DATABASE_URL` administrativo nesta primeira migração e `MIGRATION_DATABASE_URL` administrativo, schema correto e timeout de migração. O arquivo nunca deve entrar no Git. Após revisar o projeto de destino e fazer backup de qualquer banco existente, execute:

```powershell
docker run --rm --env-file C:\secrets\integracao-placas-migrate.env --entrypoint python integracao-placas:validated -m app.scripts.migrate
```

Esse comando aplica `alembic upgrade head`; não executa seed, não sincroniza FIPE e não acessa AUTCOM. Para inspeção posterior:

```sql
SELECT version_num FROM integracao_placas.alembic_version;
SELECT tablename FROM pg_tables WHERE schemaname = 'integracao_placas';
```

Não execute `app.seeds.seed_data` na nuvem: os dados demonstrativos servem exclusivamente ao desenvolvimento/testes. Um catálogo real pode ser importado posteriormente por processo autorizado, separado do startup.

## 6. Criar serviço Koyeb — ação manual posterior à aprovação

1. Salve as alterações revisadas em um commit e envie ao repositório privado autorizado. Anote commit e imagem/digest.
2. Crie um serviço **Web Service**, selecionando a instância **Free**, em região elegível; confira que não há componente pago. Use Dockerfile da raiz, contexto da raiz. Nenhum override do Compose deve ser usado em produção.
3. Cadastre as variáveis e secrets da seção 4. Runtime usa o usuário restrito; não exponha credencial de migração. Não configure volume local nem segunda instância.
4. Exponha a porta HTTP `8000`, rota `/`; configure `PORT=8000`. Se alterar a porta, altere o serviço e PORT juntos. O comando default é `python -m app.start` com um worker.
5. Configure healthcheck **HTTP `/health/ready`**, com grace period de aproximadamente 60 segundos e timeout compatível com a conexão ao banco. O Docker HEALTHCHECK separado usa `/health/live`. Readiness verifica banco e revisão Alembic, sem consumir créditos FipePlaca e sem consultar AUTCOM. [Koyeb: healthchecks](https://www.koyeb.com/docs/run-and-scale/health-checks).
6. Aplique previamente as migrações. Só então publique após a aprovação da implantação. Verifique logs com valores mascarados; não imprima env, tokens ou URLs para depurar.

## 7. Validação funcional após publicar

Verifique `/health/live` e `/health/ready` (200). Banco inacessível ou revisão divergente produz 503 no readiness. Uma requisição de negócio sem token deve produzir 401.

Em PowerShell, obtenha o token por mecanismo seguro e mantenha-o somente no ambiente da sessão:

```powershell
$apiBase = 'https://SEU_SERVICO.koyeb.app'
Invoke-RestMethod "$apiBase/health/ready"
Invoke-RestMethod "$apiBase/api/v1/vehicles/plate/OHF1I18/parts" -Headers @{ 'X-API-Key' = $env:API_ACCESS_TOKEN }
```

A consulta real de placa pode consumir créditos FipePlaca; execute-a conscientemente. Sem credencial do provedor, a identificação deve indicar indisponibilidade, sem inventar veículo. Com identificação real, o endpoint de peças em cloud retorna:

```json
{
  "plate": "OHF1I18",
  "erp_enabled": false,
  "erp_status": "PRIVATE_NETWORK_UNAVAILABLE",
  "availability_status": "NOT_QUERIED",
  "parts_count": 0,
  "parts": [],
  "message": "AUTCOM indisponível: banco privado do cliente não acessível neste modo."
}
```

Esse é um recorte do contrato; identificação, veículo e candidatos FIPE continuam no JSON quando disponíveis. Lista vazia significa integração indisponível, **não ausência de estoque**. Não são simulados preços, estoque nem resultados do AUTCOM. O endpoint de catálogo local consulta exclusivamente dados realmente cadastrados; em uma implantação nova ele começa vazio.

A integração local AUTCOM continua habilitada pelas variáveis atuais do `.env`/Compose. Não reinicie os containers existentes para validar a nuvem. Uma futura ponte segura para AUTCOM requer projeto e autorização próprios.

## 8. Backup e rollback

Antes de migrações em um banco com dados, faça backup externo. No plano Free, use `pg_dump` instalado localmente com arquivo de serviço e `.pgpass` protegidos fora do projeto, sem senha na linha de comando. Exemplo com um serviço PostgreSQL previamente configurado:

```powershell
$env:PGSERVICEFILE = 'C:\secrets\pg_service.conf'
$env:PGPASSFILE = 'C:\secrets\pgpass.conf'
pg_dump --dbname='service=integracao_backup' --format=custom --file='C:\backups\integracao-pre-migracao.dump'
pg_restore --list 'C:\backups\integracao-pre-migracao.dump'
```

Verifique restauração em banco isolado antes de considerar o backup válido. Não copie dumps para GitHub, imagem ou volume efêmero do Koyeb.

Para regressão apenas de aplicação, volte manualmente à imagem/deployment anterior **já validado com esse schema**, mantendo as variáveis/secrets e o banco. Registre digest e revisão Alembic de cada entrega. O commit `9973898` isoladamente não contém esta preparação de nuvem e não deve ser usado como rollback de produção sem adaptação.

Não execute downgrade automático: remoção de colunas/tabelas descarta dados. Em falha de migração, pare a publicação, revise a transação e prefira correção para frente; restauração/downgrade só após autorização, backup validado e janela de manutenção. Na primeira implantação, se não houver versão anterior compatível, mantenha o serviço sem tráfego até corrigir. Nenhum procedimento de rollback deve atingir AUTCOM.

## 9. Pendências e ações manuais

- Confirmar o commit revisado com `git log -1` e autorizar separadamente seu push; conferir que alterações posteriores também sejam revisadas.
- Confirmar os limites e a elegibilidade Free no Koyeb/Supabase antes de criar recursos.
- Criar projeto, copiar a conexão correta e gerar secrets/usuário runtime. Migrar e conferir grants no Supabase real.
- Aprovar a publicação, configurar o serviço, executar smoke tests HTTPS e monitorar memória/latência com tráfego real. Os testes locais não garantem capacidade sob carga do plano gratuito.
- Configurar backups e testar restauração. AUTCOM continua indisponível em cloud por desenho; o erro MySQL 2013 previamente observado continua sendo investigação separada local.
- Futuro frontend: proxy com secrets no servidor, autenticação individual e políticas de CORS conforme a origem definitiva.
