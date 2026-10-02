# Guia de Importação de Catálogos de Autopeças (IMPORT_GUIDE.md)

---

## Formatos Suportados

O importador universal do sistema aceita arquivos nos formatos:
- **CSV** (`.csv`)
- **XLSX** (`.xlsx` - Microsoft Excel)
- **JSON** (`.json`)
- **XML** (`.xml`)

---

## Estrutura de Colunas Recomendada

Seu arquivo de catálogo pode utilizar qualquer cabeçalho de colunas. Por padrão, o sistema reconhece automaticamente os seguintes nomes em português e inglês:

| Campo do Sistema | Colunas Reconhecidas Automaticamente |
| :--- | :--- |
| **Código da Peça** | `codigo`, `code`, `part_number`, `cod_peca` |
| **Fabricante** | `fabricante`, `manufacturer`, `marca_peca` |
| **Categoria** | `categoria`, `category`, `produto` |
| **Descrição** | `descricao`, `description` |
| **Marca do Veículo** | `marca_veiculo`, `make`, `montadora` |
| **Modelo do Veículo**| `modelo_veiculo`, `model`, `modelo` |
| **Motor** | `motor`, `engine` |
| **Ano Inicial** | `ano_inicio`, `year_from`, `ano_inicial` |
| **Ano Final** | `ano_fim`, `year_to`, `ano_final` |
| **Posição** | `posicao`, `position` |
| **Eixo** | `eixo`, `axis` |
| **Código OEM** | `oem`, `codigo_oem`, `oem_codes` |
| **Especificações** | `especificacoes`, `technical_specs`, `specs` |

---

## Exemplo de Arquivo CSV (`catalogo_exemplo.csv`)

```csv
fabricante,codigo,categoria,descricao,marca_veiculo,modelo_veiculo,motor,ano_inicio,ano_fim,posicao,oem
Fremax,BD1234,Disco de Freio,Disco de Freio Dianteiro Ventilado,VW,T-Cross,1.0 TSI,2019,2024,Dianteiro,5UQ615301
Cobreq,N-1234,Pastilha de Freio,Jogo de Pastilhas Dianteiras,VW,T-Cross,1.0 TSI,2019,2024,Dianteiro,5UQ698151
```

---

## Como Importar via Painel Web

1. Acesse `http://localhost:8000/admin`.
2. Clique no menu lateral **Importar Catálogo**.
3. Selecione o arquivo no seu computador.
4. Clique em **Importar Catálogo**.
5. O sistema processará as linhas, registrará a origem como `IMPORTACAO_<NOME_ARQUIVO>` e exibirá o relatório com quantidade de registros processados e erros.
