# Guia para Teste com Provedor Real de Placa (FREE_MVP.md)

---

## 1. Provedor Validade para Teste do MVP
Para o teste com placas brasileiras reais em ambiente de produção sem dados fictícios, foi implementado o adapter do **ApiPlaca.com.br**.

- **Site Oficial:** https://apiplaca.com.br
- **Documentação:** https://apiplaca.com.br/docs (REST API JSON)
- **Status da Validação:** **VERIFIED**

---

## 2. Como Fazer o Cadastro e Obter a API Key
1. Acesse https://apiplaca.com.br e clique em **Cadastrar** / **Acessar Painel**.
2. Após o cadastro, você receberá acesso ao painel de desenvolvedor.
3. Copie o seu **Bearer Token / API Key** disponibilizado na aba de credenciais de API.
4. O provedor oferece saldo inicial / requisições de sandbox para testes de integração.

---

## 3. Como Configurar o arquivo `.env` para Testar Placa Real
Abra o seu arquivo `.env` no diretório raiz do projeto e configure:

```env
APP_ENV=production
VEHICLE_PROVIDER=apiplaca
VEHICLE_API_URL=https://apiplaca.com.br/v1/consultar
VEHICLE_API_KEY=SEU_BEARER_TOKEN_AQUI
```

---

## 4. Reiniciando os Containers no Windows
Apenas execute no PowerShell:

```powershell
docker compose restart
```

---

## 5. Testando pelo Swagger (`/docs`)
1. Acesse: http://localhost:8000/docs
2. Clique em `GET /api/v1/vehicles/plate/{plate}`.
3. Clique em **Try it out**.
4. Insira uma placa brasileira REAL (ex: `ABC1D23` ou qualquer placa de veículo circulante).
5. Clique em **Execute**.
6. O sistema irá consultar a API real, normalizar marca/modelo/ano/motor/combustível e salvar no cache local PostgreSQL.
