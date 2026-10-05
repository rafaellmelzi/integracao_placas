# Fontes de Dados de Veículos (Vehicle Data Sources)

Este documento detalha as fontes de dados para identificação e catálogo de veículos utilizadas no projeto **AutoParts API**.

---

## 1. Fonte Pública Gratuita: Parallelum FIPE API

* **Nome:** Parallelum FIPE REST API (com base nos dados oficiais da Fundação Instituto de Pesquisas Econômicas - FIPE)
* **URL Oficial:** [https://parallelum.com.br/fipe/api/v1](https://parallelum.com.br/fipe/api/v1)
* **Documentação:** [https://deividfortuna.github.io/fipe/](https://deividfortuna.github.io/fipe/)
* **Custo:** R$ 0,00 (100% Gratuito)
* **Status de Autenticação:** Pública (Sem necessidade de API Key ou Token)
* **Data da Validação:** 2025-10-02
* **Licença / Termos de Uso:** `USAGE_TERMS_NOT_VERIFIED` (Serviço público comunitário mantido por Deivid Fortuna; os dados FIPE de preços e nomes são de domínio público comercial no Brasil, porém a licença específica do servidor de API pública não é explicitamente declarada).

### Endpoints Utilizados:
1. `GET /carros/marcas` - Retorna a lista completa de marcas brasileiras (ex: VW, Chevrolet, Fiat, Toyota).
2. `GET /carros/marcas/{marca_id}/modelos` - Retorna todos os modelos associados a uma marca.
3. `GET /carros/marcas/{marca_id}/modelos/{modelo_id}/anos` - Retorna as combinações de ano/combustível atreladas ao modelo.
4. `GET /carros/marcas/{marca_id}/modelos/{modelo_id}/anos/{ano_id}` - Retorna o detalhamento técnico do veículo, contendo Ano Modelo, Combustível e Código FIPE.

### Dados Efetivamente Fornecidos:
- Marca (`Marca`)
- Modelo / Versão original (`Modelo`)
- Ano Modelo (`AnoModelo`)
- Combustível (`Combustivel`)
- Código FIPE (`CodigoFipe`)
- Valor de Referência FIPE (`Valor`)
- Mês de Referência (`MesReferencia`)

### Dados NÃO Fornecidos (gravados como `NULL`):
- Motorização explícita (cilindrada em litros, potência hp, número de válvulas separado)
- Tipo de Transmissão (Câmbio manual/automático)
- Tipo de Carroceria (Sedan, Hatch, SUV)
- Número de portas / Lugares

> **IMPORTANTE (REGRA DE INTEGRIDADE DE DADOS):**
> Em estrita conformidade com os requisitos do sistema, a API **jamais inferirá ou inventará** dados técnicos (como motorização ou câmbio) a partir do texto do modelo. Se o campo não vier explicitamente preenchido pela fonte, será gravado como `NULL` no PostgreSQL.
