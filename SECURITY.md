# Segurança e Conformidade com a LGPD

## Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018)

1. **Princípio da Minimização de Dados:**
   - O sistema **NÃO armazena** dados de proprietários (Nome, CPF/CNPJ, Endereço, Telefone).
   - O foco é exclusivamente na identificação técnica do veículo (Marca, Modelo, Ano, Motor, Transmissão).

2. **Segurança e Acesso:**
   - Autenticação de API via API Keys ou JWT Tokens.
   - Proteção contra SQL Injection e validação rigorosa de entradas com Pydantic v2.
   - Hashing e auditoria das chamadas brutas (`raw_response_hash`).
   - Rate limiting por IP/Cliente.
