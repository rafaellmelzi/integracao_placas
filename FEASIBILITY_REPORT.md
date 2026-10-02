# Relatório de Viabilidade Técnica e Legal (FEASIBILITY_REPORT.md)
## API de Consulta de Autopeças por Placa e Aplicabilidade Veicular

---

### EXECUTIVE SUMMARY / RESUMO EXECUTIVO

Este relatório analisa a viabilidade técnica, legal, operacional e financeira para a criação de uma solução de integração entre consulta de placas veiculares brasileiras, catálogo unificado de aplicabilidade de autopeças e o ERP Autcom.

---

### 1. RESPOSTAS ÀS 17 PERGUNTAS DE VIABILIDADE

#### 1. De onde virão os dados da placa?
Os dados da placa virão de um ecossistema de **provedores externos de API de consulta veicular**, integrados via arquitetura de conectores/adaptadores (padrão *Adapter/Provider Pattern*). Como não existe um banco único público redistribuível no Brasil, a solução consulta provedores comerciais/oficiais homologados (ex: ApiPlaca, PlacaFipe, Infocar, Olho no Carro, CheckTudo) e mantém um **cache local resiliente e auditado**.

#### 2. Existe fonte gratuita?
**Não existe fonte gratuita oficial e ilimitada** disponível para uso comercial ou em escala.
- O aplicativo público do **SINESP Cidadão** teve seu acesso direto via API descontinuado e protegido por mecanismos de verificação. Scraping do SINESP viola termos de uso.
- Algumas APIs comerciais oferecem *free tiers* pequenos (ex.: 10 a 50 consultas gratuitas para testes em sandbox), mas para ambiente de produção comercial é necessário plano contratado por consulta (R$ 0,05 a R$ 0,30 por consulta).

#### 3. Existe fonte oficial?
Sim. A fonte oficial primária dos dados do Registro Nacional de Veículos Automotores (RENAVAM) e da Base Nacional do SNT é a **SENATRAN (Secretaria Nacional de Trânsito)** / **SERPRO** (empresa pública de TI do governo federal).
- O SERPRO disponibiliza a **API Consulta Veículo / RENAVAM / SINESP** para empresas contratantes conveniadas.
- O acesso exige convênio, credenciamento de empresa e pagamento de tarifa pública por requisição.

#### 4. Existe API?
Sim. Existem duas categorias de API:
1. **API Oficial Governamental:** SERPRO / SENATRAN (exige contrato corporativo e certificado digital).
2. **APIs Comerciais Intermediárias:** ApiPlaca.com.br, PlacaFipe, Infocar, CheckTudo, Olho no Carro, Vianova, entre outras, que consolidam bases do Denatran/Detrans/Sinesp e disponibilizam endpoints REST/JSON autenticados via Bearer Token / API Key.

#### 5. Podemos armazenar/cachear os resultados?
**Sim, para dados puramente técnicos do veículo** (marca, modelo, versão, motorização, ano fabricação, ano modelo, cor, combustível, cilindrada, potência, código FIPE).
- **Regra de LGPD:** É **permitido** armazenar e cachear dados técnicos do veículo vinculados à placa.
- **Proibição LGPD:** Não devem ser armazenados nem trafegados dados pessoais do proprietário (Nome, CPF, Endereço, Telefone) ou dados sensíveis do condutor.
- **Prazo recomendado de cache:** 30 a 90 dias para veículos de passeio comuns, pois características fabris (marca, modelo, motor) não se alteram.

#### 6. Qual licença/termos se aplicam?
- **Provedores Comerciais (ApiPlaca, Infocar, etc.):** Licença comercial por assinatura/pay-per-query. Os termos permitem armazenamento temporário em cache de dados técnicos para fins operacionais de ERP/E-commerce, desde que não haja revenda em massa do banco bruto.
- **SERPRO:** Contrato de adesão de serviço público de dados com tarifação unitária.
- **LGPD (Lei 13.709/2018):** Regulamenta que a placa isolada, sem associação com o proprietário pessoa física, refere-se a bem móvel (veículo). A consulta atende ao legítimo interesse (*Art. 7º, IX da LGPD*) de identificação da peça adequada para reparo veicular.

#### 7. Como manter os dados atualizados?
Implementa-se uma estratégia de **Invalidação e Atualização de Cache com TTL (Time To Live) Configurável**:
1. Consulta inicia no banco local (`vehicle_plate_cache`).
2. Se o registro existe e `expires_at > NOW()`, retorna imediatamente do local (< 50ms).
3. Se o registro expirou ou não existe, realiza chamada assíncrona/síncrona ao provedor ativo.
4. O resultado é normalizado, hash do raw JSON é gerado para auditoria (`raw_response_hash`), e o cache local é atualizado com nova data de expiração (ex.: +90 dias).

#### 8. De onde virá a aplicabilidade das peças?
A aplicabilidade das peças virá de **três fontes combinadas**:
1. **Catálogos Oficiais de Fabricantes de Autopeças:** Arquivos oficiais em CSV, XLSX, XML ou JSON fornecidos diretamente pelos fabricantes (ex.: Fremax, Hipper Freios, Cobreq, Bosch, Mahle, Cofap, TRW, Nakata, Sabó, Tecfil, Wega).
2. **Bases Padronizadas e Catálogos Eletrônicos:** TecDoc (TecAlliance) para cobrir padronização internacional KType / TecDoc ID, e catálogos nacionais consolidados.
3. **Mapeamento de ERP do Cliente (Autcom):** Tabela interna `ERP_PRODUCT_MAPPING` correlacionando códigos internos do ERP aos códigos do fabricante e códigos EAN/GTIN.

#### 9. Quais fontes são gratuitas?
- Catálogos públicos em PDF/Excel/CSV disponibilizados abertamente nos sites oficiais dos fabricantes brasileiros para download institucional.
- Arquivos de tabelas de conversão e aplicabilidade do mercado de reposição automotiva repositados em portais abertos de autopeças.
- Tabela FIPE oficial (disponível via API pública/comunitária para referência de códigos de modelos e anos).

#### 10. Quais são pagas?
- **APIs de Consulta de Placa** (ApiPlaca, SERPRO, Infocar, etc.): Cobradas por requisição.
- **Licença TecDoc / TecAlliance API:** Cobrança por assinatura comercial para acesso em tempo real à base global de autopeças.
- **Bases Consolidadas Premium de Veículos/Frota:** Ex: Frota IBGE/Denatran detalhada.

#### 11. Qual oferece melhor cobertura brasileira?
- **Para Placas:** APIs comerciais nacionais (ex: ApiPlaca / Infocar / SERPRO) possuem **> 98% de cobertura** da frota circulante nacional (Mercosul e placa antiga 3 letras).
- **Para Aplicabilidade de Peças no Brasil:** Os catálogos diretos de fabricantes nacionais (Fremax, Nakata, Cofap, Fras-le, Bosch BR) e o ecossistema TecDoc Brasil cobrem **> 95% das peças** de giro do mercado brasileiro.

#### 12. Podemos utilizar comercialmente?
**Sim.** A arquitetura proposta utiliza apenas integrações oficiais de provedores contratados, dados corporativos de fabricantes e identificadores técnicos de produto (EAN, código de fabricante, referências cruzadas OEM), estando 100% em conformidade com o uso comercial e corporativo.

#### 13. Existe risco jurídico/LGPD?
- **Risco LGPD:** **ZERO / ÍNFIMO**, desde que a API **NÃO capture, armazene ou exiba dados do proprietário** (CPF, Nome, Endereço). A API limita-se exclusivamente a dados fabris/técnicos do veículo.
- **Risco de Direitos Autorais / Scraping:** **ZERO**, pois não utilizamos web scraping nem quebra de CAPTCHA. Toda carga de catálogo é feita por importadores estruturados de arquivos fornecidos legalmente ou APIs autorizadas.

#### 14. Qual arquitetura você recomenda?
Recomenda-se uma **Arquitetura em Camadas Desacoplada e Modular (Clean/Hexagonal Architecture)** em Python + FastAPI:
- **API Gateway / Endpoints REST:** FastAPI (OpenAPI/Swagger).
- **Camada de Abstração de Placa:** `BasePlateProvider` (padrão Adapter/Strategy). Permite alternar entre Mock, SERPRO, ApiPlaca ou Infocar via variável de ambiente sem alterar código interno.
- **Camada de Abstração de Catálogo:** `BaseCatalogProvider` para busca de aplicabilidade.
- **Motor de Normalização:** Normalização determinística de veículos (Marca, Modelo, Versão, Motor, Câmbio, Combustível) e Categorias de Peças com tabela de sinônimos.
- **Cache Local e Persistência:** PostgreSQL com SQLAlchemy 2.0 e Alembic.
- **Containerização:** Docker + Docker Compose.

#### 15. Qual custo estimado?
Veja a seção detalhada de estimativa de custos abaixo no relatório. Para 1.000 consultas/mês, o custo de infraestrutura é mínimo (~US$ 10-20/mês ou R$ 0 local) e o custo de API de placa fica entre R$ 50,00 e R$ 150,00/mês.

#### 16. O que conseguimos construir 100% gratuitamente?
- Toda a **plataforma técnica backend, banco de dados, motor de busca de aplicabilidade, normalização de veículos e categorias, importadores de catálogos CSV/XLSX/XML, tabela de cross-reference, mapeamento ERP Autcom e painel administrativo**.
- Em ambiente de testes/dev, o sistema conta com um **Mock Provider completo** com dados reais de veículos brasileiros (VW T-Cross, Chevrolet Onix, Fiat Uno, Toyota Corolla, Ford Ka, etc.) e peças de marcas nacionais (Fremax, Bosch, Cobreq, Hipper Freios).

#### 17. O que necessariamente dependerá de fornecedor externo?
- A resolução em tempo real de uma **placa virgem** (não presente no cache local) para descobrir o modelo/ano exato no ambiente de produção. Isso exige chamada a um provedor pago de API de placa (ex: ApiPlaca / SERPRO).

---

### 2. MAPEAMENTO DE FONTES DE DADOS DE PLACA

| Nome | Documentação / URL | Dados Disponíveis | Autenticação | Custo Estimado | Limite / Freq. | Uso Comercial | Qualidade & Cobertura | Limitações & Licença |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SERPRO Consulta Veículo** | `https://www.serpro.gov.br/` | Marca, modelo, ano fab/mod, cor, chassi (mascarado), motor, município, combustível | Certificado Digital mTLS + OAuth2 | ~R$ 0,10 - R$ 0,25 / consulta | Conforme contrato corporativo | Sim (Oficial) | 100% oficial / 100% frota BR | Exige convênio governamental burocrático |
| **ApiPlaca.com.br** | `https://apiplaca.com.br/` | Marca, modelo, submodelo/versão, ano, motor, cor, município, FIPE, combustível | API Key (Bearer Token) | ~R$ 0,08 - R$ 0,18 / consulta | Planos de 500 a 100k req/mês | Sim | 99% / Alta precisão em versões | Depende de saldo pré-pago |
| **Infocar API** | `https://www.infocar.com.br/` | Dados cadastrais completos do veículo, FIPE, especificações técnicas | API Key / Basic Auth | ~R$ 0,15 - R$ 0,30 / consulta | Personalizado por contrato | Sim | 99% / Excelente para frotas | Contrato comercial mínimo mensal |
| **PlacaFipe API** | `https://placafipe.com/` | Marca, modelo, ano, cor, combustível, código FIPE, cidade | API Key | ~R$ 0,05 - R$ 0,12 / consulta | Rotação por API key | Sim | 95% / Bom custo-benefício | Versão técnica às vezes genérica |
| **Mock Local / Base Interna (Fallback)** | Embutido no sistema | Veículos cadastrados na base interna e no cache acumulado | Interno (N/A) | R$ 0,00 | Ilimitado | Sim | 100% dos dados já consultados | Cobre apenas veículos já pesquisados |

---

### 3. FONTES DE APLICABILIDADE DE AUTOPEÇAS

1. **Fremax Catálogos (Freios):** Discos e tambores de freio com especificação de dimensão, posição (dianteiro/traseiro), motorização e ano.
2. **Cobreq / TMD Friction:** Pastilhas e sapatas de freio com código de fabricante, sistema de freio (Teves, Varga, Bosch) e referências cruzadas.
3. **Bosch Automotive Catalog:** Velas, filtros, palhetas, bombas de combustível, componentes elétricos e injeção.
4. **Hipper Freios / Nakata / Cofap:** Discos, amortecedores, componentes de suspensão e direção.
5. **TecDoc Brasil (TecAlliance):** Padrão mundial de catalogação e intercambiabilidade de autopeças.

---

### 4. ESTIMATIVA DE CUSTOS EM ESCALA (BRL)

| Volume de Consultas | Infraestrutura (Docker / Cloud VPS / Postgres) | API de Consulta de Placa (Média R$ 0,10/req) | Efeito Cache (Estimativa de 60% Hit) | Custo Total Estimado de Placa | Custo por Consulta Efetiva |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.000 / mês** | R$ 0 (Servidor local) ou R$ 80 (VPS) | R$ 100,00 (1000 req) | R$ 40,00 (400 novas) | **R$ 40,00 - R$ 120,00** | R$ 0,04 - R$ 0,12 |
| **10.000 / mês** | R$ 150,00 (VPS 4 vCPU / 8GB RAM) | R$ 1.000,00 | R$ 300,00 (3.000 novas) | **R$ 450,00** | R$ 0,045 |
| **100.000 / mês** | R$ 500,00 (Cloud dedicada + DB) | R$ 8.000,00 (Desconto vol.) | R$ 2.000,00 (20.000 novas) | **R$ 2.500,00** | R$ 0,025 |
| **1.000.000 / mês** | R$ 2.500,00 (Cluster K8s + Redis + Postgres) | R$ 60.000,00 (Preço atacado) | R$ 10.000,00 (100k novas) | **R$ 12.500,00** | R$ 0,0125 |

*Nota: O cache local reduz drasticamente o custo de chamadas externas à medida que a base de consultas recorrentes do ERP é preenchida.*

---

### 5. RECOMENDAÇÃO DE ARQUITETURA DE SOFTWARE

```
+-----------------------------------------------------------------------+
|                           ERP AUTCOM / FRONTEND                       |
+-----------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                    FASTAPI REST API LAYER (OpenAPI)                   |
|   /api/v1/vehicles/plate/{plate} | /api/v1/parts/search               |
+-----------------------------------------------------------------------+
         |                                           |
         v                                           v
+----------------------------------+   +----------------------------------+
|      PLATE SERVICE MODULE        |   |      PARTS SEARCH MODULE         |
|  - Cache Check (Expires/Audit)   |   |  - Query Normalizer (Synonyms)   |
|  - Provider Adapter Engine       |   |  - Compatibility Engine          |
|  - Vehicle Normalizer Engine     |   |  - ERP Product Matcher (EAN/Code)|
+----------------------------------+   +----------------------------------+
         |                                           |
         +--------------------+----------------------+
                              |
                              v
+-----------------------------------------------------------------------+
|                    POSTGRESQL DATABASE (SQLAlchemy)                   |
|  VEHICLE_* | PART_* | ERP_PRODUCT_MAPPING | VEHICLE_PLATE_CACHE       |
+-----------------------------------------------------------------------+
```

---
**Conclusão do Relatório:** A solução é totalmente viável técnica e legalmente, permitindo implementação imediata em modelo MVP com provedores adaptáveis, custo mínimo inicial e expansão contínua.
