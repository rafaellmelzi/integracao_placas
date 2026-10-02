# Fontes de Dados e Integrações

## Configuração dos Provedores de Placa

O sistema suporta troca dinâmica do provedor ativo via variável de ambiente:

- `PLATE_PROVIDER_PRIMARY=MOCK`
- `PLATE_PROVIDER_SECONDARY=APIPLACA`

### Provedores Implementados:
1. **Mock Provider:** Utilizado para ambiente de desenvolvimento e testes offline.
2. **ApiPlaca / Commercial API Adapter:** Adapter pré-configurado para APIs do mercado.
3. **SERPRO Adapter:** Conector para infraestrutura governamental.

## Importação de Catálogos de Peças

O sistema disponibiliza importadores para os formatos:
- CSV
- XLSX
- JSON
- XML
