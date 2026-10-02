# Fontes de Dados de Aplicabilidade de Autopeças (PARTS_DATA_SOURCES.md)

---

## Mapeamento de Fabricantes de Autopeças no Brasil

| Fabricante | Categoria Principal | Status no Projeto | Origem dos Dados | Permite Importação? | Observações / Procedimento |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fremax** | Freios (Discos e Tambores) | **AVAILABLE** | Catálogo Oficial em Excel / CSV | **SIM (IMPORTAÇÃO MANUAL / AUTOMÁTICA)** | Download do catálogo técnico em `fremax.com.br` e carga via `/admin`. |
| **Cobreq** | Freios (Pastilhas e Sapatas) | **AVAILABLE** | Catálogo Técnico Público | **SIM (IMPORTAÇÃO MANUAL / AUTOMÁTICA)** | Download de tabelas de aplicação e carga em CSV/XLSX. |
| **Bosch** | Injeção, Filtros, Velas | **AVAILABLE** | Catálogo Automotivo Bosch | **SIM (IMPORTAÇÃO MANUAL)** | Arquivos de tabela de conversão e aplicabilidade. |
| **Hipper Freios** | Discos e Tambores de Freio | **AVAILABLE** | Catálogo Eletrônico Hipper | **SIM (IMPORTAÇÃO MANUAL)** | Carga via importador universal com mapeamento de colunas. |
| **TecDoc / TecAlliance** | Multi-categoria | **MANUAL_IMPORT_REQUIRED** | API Licenciada / Arquivos de Carga | **SIM (VIA CONTRATO COMERCIAL)** | Estrutura pronta para KType e tabelas de equivalência cruzada. |

---

## Regra Anti-Falso Positivo

O sistema **NÃO utiliza Inteligência Artificial nem similaridade de texto** para assumir compatibilidade entre veículos e peças.

A associação é estritamente estruturada:
`Part` → `PartApplication` → `Vehicle`

Se o veículo consultado for ambíguo (ex.: T-Cross 1.0 TSI vs 1.4 TSI), a API retorna o status `APPLICATION_AMBIGUOUS` solicitando especificação de versão ou motor.
