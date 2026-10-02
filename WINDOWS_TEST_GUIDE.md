# Guia de Teste no Windows (WINDOWS_TEST_GUIDE.md)

Este guia destina-se a executores no sistema operacional Windows. Nenhuma instalação local de Python, PostgreSQL ou Node é necessária.

---

## Pré-requisitos Únicos (PASSO 1)

1. Instale o **Git for Windows**: https://git-scm.com/download/win
2. Instale o **Docker Desktop for Windows**: https://www.docker.com/products/docker-desktop/

---

## Execução em 3 Passos (PASSO 2)

Abra o **PowerShell** ou **Prompt de Comando (cmd)** e execute:

```powershell
# 1. Clonar ou acessar a pasta do projeto
cd C:\caminho\para\o\projeto

# 2. Criar arquivo .env a partir do modelo
copy .env.example .env

# 3. Subir todos os serviços via Docker Compose
docker compose up -d
```

---

## Verificando os Serviços (PASSO 3)

Após subir o Docker, acesse no seu navegador:

- **Painel Administrativo:** http://localhost:8000/admin
- **Swagger UI (Documentação Interativa):** http://localhost:8000/docs
- **Status do Sistema (Healthcheck):** http://localhost:8000/health

---

## Como Configurar uma API Key Real de Placa

Para testar uma placa real de produção:

1. Abra o arquivo `.env` em um editor de texto (ex: Bloco de Notas).
2. Altere:
   ```env
   APP_ENV=production
   VEHICLE_PROVIDER=apiplaca
   VEHICLE_API_KEY=SUA_CHAVE_OBTIDA_NO_PROVEDOR
   ```
3. Reinicie os containers:
   ```powershell
   docker compose restart
   ```
