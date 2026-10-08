# Validação da compatibilidade de peças — 08/10/2026

Base do trabalho: commit `9973898`. Este relatório registra a validação inicial,
realizada antes do commit das correções. Não houve deploy ou reinício dos containers
existentes. A revisão final para commit está em `REVISAO_PRE_DEPLOY.md`.

## Causas e correções

| Problema | Causa | Correção |
| --- | --- | --- |
| Motor e ano ignorados | Placas entregavam `engine`/`year_model`; matcher esperava `engine_displacement`/`model_year` | `MatchingVehicle` normaliza ambos os contratos na fronteira do serviço e também aceita entradas diretas dos testes |
| Incompatíveis apresentados | Filtro excluía somente o status antigo `REJECTED` | Lista explícita de estados permitidos: `COMPATIBLE` e `CONDITIONAL`; disponibilidade consultada apenas para os códigos retornados |
| Atributos de veículos diferentes misturados | Delimitadores por vírgula e `--` sem espaços não eram tratados | Avaliação independente de segmentos; preservação de listas de motores, intervalos e sufixos de atributos |
| CVT aceita sem confirmação | Novo parser tinha removido suporte à restrição CVT | CVT/DCT avaliados explicitamente; transmissão desconhecida gera `CONDITIONAL` |
| Falta de informação apresentada como confirmação | Modelo, tração ou especificações desconhecidas podiam ser aprovados | Modelo sozinho gera `CONDITIONAL`; restrições desconhecidas de motor, ano, combustível, transmissão, tração, versão, válvulas ou turbo exigem confirmação |
| Estados inconsistentes | Retornos misturavam `EXACT`, `REJECTED` e os novos estados | Matcher usa três classificações; motivos distinguem conflito, entrada vazia, inválida, modelo ausente e confirmação pendente |
| SQLite sem tabelas | Alembic migrava outro engine em memória; overrides de dependências eram globais e o seed alterava factories sem restauração | Migração aceita conexão fornecida; cada teste recebe seu banco migrado e estado restaurado por fixtures |
| Sincronização dependente de internet | Testes chamavam APIs FIPE reais | Catálogo determinístico com marcas, modelos, anos e detalhes; mocks nas fronteiras HTTP e falha explícita para chamadas não simuladas |

Anos sem rótulo representam ano modelo. Ano fabricação só é comparado quando a
aplicação o exige explicitamente; não é usado para inventar ano modelo ausente.
Combustíveis distintos não são considerados intercambiáveis apenas por um veículo
Flex poder consumir gasolina. Associações ambíguas entre modelos/motores/anos
recebem confirmação pendente. Sintaxe de exclusão requer revisão do catálogo e
é excluída dos resultados aplicáveis.

Os 13 cenários originais foram mantidos. No caso 4, a tração passou a ser explicitamente
conhecida como `4X2`, para isolar o teste da lista de motores. Um teste adicional
garante `CONDITIONAL` quando essa tração é exigida e desconhecida. O teste original
do endpoint com aplicação FWD/4X2 também passou a exigir confirmação de tração.

## Contrato JSON do endpoint

`GET /api/v1/vehicles/plate/{plate}/parts` tem schema de resposta explícito:

- `parts` contém somente `COMPATIBLE` ou `CONDITIONAL`.
- `parts_count` deve ser igual ao tamanho de `parts`, inclusive nos retornos vazios/erros.
- `requires_confirmation` é verdadeiro somente para `CONDITIONAL`.
- `match_details` informa `reason`, `matched`, `unknown` e `conflicts`.
- Peças retornadas não podem conter conflitos; condicionais devem conter pendências.
- Os campos públicos do veículo (`year_model`, `year_manufacture`, `engine` etc.)
  continuam disponíveis; o contrato interno é normalizado sem alterar o provedor FipePlaca.

Há testes HTTP cobrindo normalização, cache, filtro de incompatíveis, disponibilidade,
contagem e respostas vazias por ERP desativado, ausência de produtos, incompatibilidade,
veículo ausente ou erro de consulta.

## Resultados dos testes

- Matcher: **93 aprovados, 0 reprovados**.
- Suíte completa: **145 aprovados, 0 reprovados**, incluindo os 10 testes da API.
- Execução em Python 3.12 no Docker, rede desabilitada e montagem do repositório somente para leitura.
- Permanecem avisos de depreciação de dependências; não há erros de testes.

## Validação real somente de leitura

Cache de `OHF1I18`: Jeep Renegade 1.8 Flex, fabricação 2015, modelo 2016,
transmissão desconhecida. Sem consulta ao provedor de placas.

O código atualizado foi carregado em memória em um processo Python separado,
usando PostgreSQL em transação somente de leitura e consultas SELECT existentes
do AUTCOM. A API em execução não foi modificada.

| Resultado na consulta atual | Quantidade |
| --- | ---: |
| Candidatos consultados | 400 |
| COMPATIBLE | 110 |
| CONDITIONAL | 182 |
| INCOMPATIBLE excluídos | 108 |
| Peças retornadas pelo serviço corrigido | 292 |
| Peças retornadas com disponibilidade | 292 |

Exemplos conhecidos excluídos: produto `06958` por GNV e `07477` por motor 2.4.
O número histórico de 346 peças era uma resposta anterior da API; a consulta atual
trouxe 400 candidatos e não estabelece que o catálogo tenha mudado.

## Investigação separada do MySQL 2013

A primeira falha ocorreu na inicialização do dialeto, ao executar `SET NAMES`,
antes da consulta de produtos. Posteriormente funcionaram conexão TCP, handshake
MySQL (protocolo 10, servidor 8.0.46-commercial), `SELECT 1`, consulta de produtos
e consulta de disponibilidade. Drivers observados: PyMySQL 1.2.3 e SQLAlchemy 2.1.4.

A falha é intermitente nas observações realizadas; a causa raiz permanece pendente.
Uma nova ocorrência deve ser correlacionada com logs do servidor e da infraestrutura
no mesmo horário. Nenhuma credencial, parâmetro de rede ou configuração de conexão
foi alterada como tentativa de correção.

## Arquivos deste trabalho

- `app/services/vehicle_contract.py` (novo).
- `app/services/application_matcher.py`.
- `app/services/parts_compatibility_service.py`.
- `app/schemas/schemas.py`.
- `app/api/endpoints.py`.
- `alembic/env.py`.
- `tests/conftest.py` (novo).
- `tests/test_application_matcher.py`.
- `tests/test_api.py`.
- `tests/test_fipe_ondemand.py`.
- `tests/test_fipe_provider.py`.
- `tests/test_fipeplaca_integration.py`.
- `tests/test_fipeplaca_provider.py`.
- `tests/test_sync.py`.
- `VALIDACAO_MATCHER.md` (novo).

As alterações locais anteriores de `docker-compose.yml` e `requirements.txt`
permanecem preservadas. `.env`, credenciais, estrutura e dados de produção do AUTCOM
não foram alterados.

## Reproduzir localmente sem reiniciar os containers

No PowerShell, usar a imagem já disponível, com o código atual montado em leitura:

```powershell
cd C:\Projetos\integracao_placas
docker run --rm --network none --mount "type=bind,source=C:\Projetos\integracao_placas,target=/app,readonly" -w /app -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python integracao_placas-api -m pytest -p no:cacheprovider tests/test_application_matcher.py -q
docker run --rm --network none --mount "type=bind,source=C:\Projetos\integracao_placas,target=/app,readonly" -w /app -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python integracao_placas-api -m pytest -p no:cacheprovider -q
docker compose config --quiet
```

A imagem da API em execução continua com o código anterior. Sua reconstrução e
recriação devem ocorrer somente depois da confirmação do responsável pelo projeto.
Após a atualização autorizada, validar `/docs` e consultar o endpoint de peças para
`OHF1I18`: todos os resultados devem ser compatíveis/condicionais, a contagem deve
coincidir com o tamanho da lista e as condicionais devem explicitar suas pendências.
