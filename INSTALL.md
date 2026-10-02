# Guia de Instalação e Execução

## Requisitos Prévia
- Docker & Docker Compose
- Python 3.12+ (para desenvolvimento local sem Docker)

## Passos para Execução com Docker

1. Clone o repositório:
```bash
git clone https://github.com/empresa/autoparts-api.git
cd autoparts-api
```

2. Configure as variáveis de ambiente:
```bash
cp .env.example .env
```

3. Inicie a aplicação com Docker Compose:
```bash
docker compose up -d --build
```

4. Acesse os endpoints:
- API Docs / Swagger: http://localhost:8000/docs
- Painel Administrativo: http://localhost:8000/admin

## Execução de Testes
```bash
pytest
```
