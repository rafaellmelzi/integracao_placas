# AutoParts Plate & Applicability API

API REST de consulta de veículos por placa (padrão antigo e Mercosul), catalogação de aplicabilidade automotiva, equivalências de peças (cross-reference) e integração com produtos do ERP Autcom.

## Arquitetura e Tecnologias

- **Backend:** Python 3.12+, FastAPI, Pydantic v2
- **Banco de Dados:** PostgreSQL 16
- **ORM & Migrations:** SQLAlchemy 2.0, Alembic
- **Containerização:** Docker, Docker Compose
- **Testes:** Pytest

## Funcionalidades Principais

1. **Consulta de Veículo por Placa:** Suporte a placas tradicionais (`ABC1234`) e Mercosul (`ABC1D23`). Cache inteligente com auditoria, invalidação por TTL e fallback para múltiplos provedores.
2. **Normalização Automática de Veículos:** Unificação de nomenclaturas de marcas, modelos, motorizações e transmissões.
3. **Catálogo de Aplicabilidade de Autopeças:** Busca inteligente de peças por categoria, veículo, motor e ano com níveis de confiança (`CONFIRMED`, `HIGH_CONFIDENCE`, `POSSIBLE`, `UNVERIFIED`).
4. **Cross-Reference:** Tabela de equivalência entre fabricantes, peças OEM e aftermarket.
5. **Integração ERP Autcom:** Mapeamento de produtos do ERP por EAN, código do fabricante e referências cruzadas.
6. **Importador de Catálogos:** Suporte a arquivos CSV, XLSX, XML e JSON para carga em massa de aplicabilidades.
7. **Painel Administrativo Web:** Interface para gestão de placas, veículos, peças, importações e correspondências ERP.

## Quick Start (Docker)

```bash
docker compose up -d
```

Acesse no navegador:
- **Swagger UI (API Docs):** http://localhost:8000/docs
- **Painel Administrativo:** http://localhost:8000/admin

## Documentação Completa

- [Relatório de Viabilidade](FEASIBILITY_REPORT.md)
- [Arquitetura do Sistema](ARCHITECTURE.md)
- [Modelagem de Banco de Dados](DATABASE.md)
- [Especificação de API](API.md)
- [Fontes de Dados](DATA_SOURCES.md)
- [Guia de Instalação](INSTALL.md)
- [Segurança e LGPD](SECURITY.md)
