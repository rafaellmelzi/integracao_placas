# Fontes Gratuitas de Dados Veiculares (VEHICLE_DATA_SOURCES.md)

---

## Visão Geral

Este documento descreve as fontes públicas e gratuitas de dados veiculares no Brasil para formação de base própria (Marca, Modelo, Ano, Versão e Motorização), visando custo zero no MVP.

---

## 1. Tabela FIPE (Fundação Instituto de Pesquisas Econômicas)

- **Site Oficial:** `https://veiculos.fipe.org.br/`
- **Status:** **GRATUITO / USO PÚBLICO**
- **Acesso:** Serviços comunitários REST / Tabela FIPE aberta.
- **Campos Fornecidos:**
  - Marca (`brand`)
  - Modelo (`model`)
  - Ano Modelo (`year_model`)
  - Código FIPE (`fipe_code`)
  - Combustível (`fuel`)
- **Uso:** Utilizado no sistema para estruturar o cadastro base de marcas, modelos e anos.

---

## 2. Dados Abertos Denatran / Senatran (Frota Circulante)

- **Site Oficial:** `https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-2024`
- **Status:** **GRATUITO / DADOS ABERTOS GOVERNAMENTAIS**
- **Licença:** Licença Aberta para Informações Públicas (Lei de Acesso à Informação nº 12.527/2011).
- **Campos Fornecidos:**
  - Marca/Modelo oficial
  - Ano de Fabricação
  - UF/Município de licenciamento
- **Uso:** Formação do dicionário oficial de nomenclaturas de marcas e modelos para normalização.

---

## 3. Base Interna de Demonstração (DEMO SEED)

- **Status:** **GRATUITO / EMBUTIDO NO PROJETO**
- **Origem:** Script `app/seeds/seed_data.py`.
- **Identificador de Origem:** `DEMO_CATALOG`
- **Finalidade:** Demonstração completa de consultas por Marca, Modelo, Versão e Motorização sem necessidade de conexões pagas.
