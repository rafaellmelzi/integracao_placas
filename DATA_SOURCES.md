# Documentação de Fontes de Dados (DATA_SOURCES.md)

---

## 1. PROVIDERS DE CONSULTA DE PLACA VEICULAR

| Nome | Site Oficial / Documentação | Status Validação | Preço Estimado | Free Tier | Limite Grátis | Campos Retornados | Licença / Uso Comercial | Cache Permitido? | Status Integração |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ApiPlaca.com.br** | `https://apiplaca.com.br` | **VERIFIED** | R$ 0,08 - R$ 0,18 / req | Sim (Sandbox Dev) | ~50 req/mês | Marca, modelo, versão, ano fab/mod, motor, combustível, câmbio, FIPE | Comercial | SIM (Dados Técnicos Isolados) | **IMPLEMENTADO (Adapter Ativo)** |
| **PlacaFipe** | `https://placafipe.com` | **NOT_VERIFIED** | Não verificado | Não verificado | N/A | Não documentado oficialmente | Desconhecido | Desconhecido | **DESABILITADO (Marcação NOT_VERIFIED)** |
| **SERPRO Consulta Veículo** | `https://www.serpro.gov.br` | **VERIFIED** | R$ 0,10 - R$ 0,25 / req | Não | N/A | Dados oficiais RENAVAM/SNT | Oficial / Governamental | SIM (Dados Técnicos Isolados) | **PRONTO PARA ADAPTER** |
| **Mock Provider** | Interno do sistema | **VERIFIED** | R$ 0,00 | Ilimitado | Ilimitado | Marca, modelo, versão, ano, motor, combustível, FIPE | Livre (Dev/Testes) | N/A | **IMPLEMENTADO (Modo Dev)** |

---

## 2. CATÁLOGOS DE APLICABILIDADE DE AUTOPEÇAS

| Nome | Site Oficial / Origem | Status Validação | Preço | Formato de Carga | Campos Suportados | Licença / Uso Comercial | Status Integração |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Importador de Catálogo de Fabricante** | Interno do sistema | **VERIFIED** | R$ 0,00 | CSV, XLSX, JSON, XML | Código fabricante, Marca, Veículo, Motor, Ano inicial/final, Posição, EAN | Livre / Proprietário do ERP | **IMPLEMENTADO** |
| **Fremax Freios** | `https://www.fremax.com.br` | **VERIFIED** | R$ 0,00 (Download Público) | CSV / XLSX | Discos e tambores de freio, dimensões, posições, ano, motor | Uso Corporativo | **SUPORTADO VIA IMPORTADOR** |
| **Cobreq / TMD Friction** | `https://www.cobreq.com.br` | **VERIFIED** | R$ 0,00 (Download Público) | CSV / XLSX | Pastilhas e sapatas de freio, sistema de freio | Uso Corporativo | **SUPORTADO VIA IMPORTADOR** |
| **TecDoc / TecAlliance API** | `https://www.tecalliance.net` | **VERIFIED** | Por contrato comercial | REST API / Webservice | Padrão global de aplicabilidade e intercambiabilidade (KType) | Comercial | **PRONTO PARA ADAPTER FUTURO** |
