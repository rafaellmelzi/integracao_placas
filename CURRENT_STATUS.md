# Status Atual do Projeto (CURRENT_STATUS.md)

## Tabela de Auditoria de Funcionalidades

| FUNCIONALIDADE | STATUS | DADOS REAIS? | MOCK? | PROVEDOR | PRECISA CREDENCIAL? | PRONTO PARA TESTE? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Consulta por Placa (Dev/Testes)** | Implementado | NÃO (Exemplos dev) | SIM | `MockPlateProvider` | NÃO | SIM |
| **Consulta por Placa (Produção Real)** | Implementado (Adapters) | SIM | NÃO | `ApiPlacaProvider` / `SerproProvider` / `PlacaFipeProvider` | SIM (`VEHICLE_API_KEY`) | SIM (Aguardando Key) |
| **Cache Local de Placas (PostgreSQL/SQLite)** | Implementado | SIM (Persiste buscas) | NÃO | Banco de Dados Local | NÃO | SIM |
| **Normalização de Veículos** | Implementado | SIM | NÃO | Motor de Normalização Interno | NÃO | SIM |
| **Pesquisa de Aplicabilidade de Peças** | Implementado | SIM (Quando alimentado) | NÃO (Depende da base) | Catálogos Locais / Importados | NÃO | SIM |
| **Importador de Catálogos (CSV/XLSX/JSON/XML)**| Implementado | SIM | NÃO | Módulo de Importação Interno | NÃO | SIM |
| **Tabela Cross-Reference de Peças** | Implementado | SIM | NÃO | Base Interna | NÃO | SIM |
| **Mapeamento ERP Autcom** | Implementado | SIM | NÃO | Tabela `ERP_PRODUCT_MAPPING` | NÃO | SIM |
| **Painel Web Administrativo (`/admin`)** | Implementado | SIM | NÃO | FastAPI + HTML/JS Static | NÃO | SIM |
| **Endpoint de Healthcheck (`/health`)** | Implementado | SIM | NÃO | FastAPI Internal | NÃO | SIM |

---

## Observação Importante sobre Exemplos e Testes

- **Exemplos na Documentação (ex.: `ABC1D23`, `Volkswagen T-Cross`):** São exemplos demonstrativos de desenvolvimento (*Mock Data* em modo de teste `APP_ENV=development`). **NÃO são apresentados como consultas reais de placas.**
- **Modo Produção (`APP_ENV=production`):** Se nenhuma API key real for configurada, o sistema retorna estritamente `DATA_SOURCE_NOT_CONFIGURED`. Nunca inventa veículos fictícios em produção.
