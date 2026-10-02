# Guia MVP Custo Zero (FREE_MVP.md)

## O que é possível realizar com Custo R$ 0.00?

Toda a plataforma técnica do projeto foi desenvolvida para rodar com **Custo Zero de Licenciamento e Infraestrutura**:

1. **Backend & Banco de Dados:** FastAPI, Python, PostgreSQL, SQLAlchemy e Docker (100% Open Source e sem custo de licença).
2. **Ambiente de Desenvolvimento e Testes:** O sistema inclui o `MockPlateProvider` que permite testar toda a lógica de consulta por placa, normalização, busca de peças, cross-reference e integração Autcom ERP gratuitamente.
3. **Importador de Catálogos:** Você pode baixar catálogos de aplicabilidade em formato Excel (XLSX) ou CSV disponibilizados gratuitamente nos sites dos principais fabricantes (Fremax, Cobreq, Bosch, Hipper Freios) e importá-los via painel em `/admin`.

---

## O que depende de Credencial / Contratação Externa?

Para consultar uma **placa virgem real** em ambiente de produção (fora do ambiente de dev/mock):

- É necessário cadastrar-se em um provedor pago de API de placa (ex: ApiPlaca.com.br ou PlacaFipe.com).
- Muitos provedores oferecem um **Free Tier de Testes** (50 a 100 consultas gratuitas ao se cadastrar).
- Insira a API Key obtida no seu arquivo `.env`:
  ```env
  APP_ENV=production
  VEHICLE_PROVIDER=apiplaca
  VEHICLE_API_KEY=sua_chave_aqui
  ```
