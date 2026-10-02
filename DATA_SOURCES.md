# Fontes de Dados de Placas e Aplicabilidade de Autopeças

## 1. CONSULTA DE PLACA VEICULAR

| Nome | Site Oficial | Documentação | Preço | Free Tier | Limite | Campos | Licença / Uso | Permite Cache? | Status Integração |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ApiPlaca.com.br** | `https://apiplaca.com.br` | `https://apiplaca.com.br/docs` | R$ 0,08 - R$ 0,18 / req | Sim (Dev sandbox) | 50 req/mês | Marca, modelo, ano fab/mod, motor, FIPE | Comercial | SIM (Dados Técnicos) | **IMPLEMENTADO (Adapter)** |
| **PlacaFipe API** | `https://placafipe.com` | `https://placafipe.com/api` | R$ 0,05 - R$ 0,12 / req | Sim (Grátis testes) | 100 req/mês | Marca, modelo, ano, cor, combustível, FIPE | Comercial | SIM (Dados Técnicos) | **IMPLEMENTADO (Adapter)** |
| **SERPRO Consulta Veículo** | `https://www.serpro.gov.br` | Portal SERPRO | R$ 0,10 - R$ 0,25 / req | Não | Conforme contrato | Dados oficiais RENAVAM/DENATRAN | Governamental | SIM (Dados Técnicos) | **IMPLEMENTADO (Adapter)** |
| **Mock Provider** | Interno | N/A | R$ 0,00 | Ilimitado | Ilimitado | Veículos de teste | Livre | N/A | **IMPLEMENTADO (Dev Mode)** |

---

## 2. APLICABILIDADE DE PEÇAS E CATÁLOGOS

| Nome | Site Oficial | Documentação | Preço | Free Tier | Limite | Campos | Licença / Uso | Permite Cache? | Status Integração |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Importador Próprio (CSV/XLSX/JSON/XML)** | Interno | N/A | R$ 0,00 | Ilimitado | Ilimitado | Código, Fabricante, Veículo, Motor, Ano, Posição | Livre | SIM | **IMPLEMENTADO** |
| **Catálogos Fremax / Cobreq / Bosch / Hipper** | Sites dos Fabricantes | Downloads Oficiais | R$ 0,00 (Downloads) | Arquivos Públicos | Ilimitado | Aplicabilidade por veículo e dimensões | Comercial | SIM | **SUPORTADO VIA IMPORTADOR** |
| **TecDoc / TecAlliance API** | `https://www.tecalliance.net` | Portal TecAlliance | Sob Consulta (Pago) | Não | Por contrato | Padrão mundial de autopeças e KType | Comercial | SIM | **PRONTO PARA ADAPTER FUTURO** |
