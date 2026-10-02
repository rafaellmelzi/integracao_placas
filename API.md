# Especificação da API REST

## Endpoints Principais

### 1. Consultar Veículo por Placa
`GET /api/v1/vehicles/plate/{plate}`

**Parâmetros:**
- `plate`: Placa em formato Antigo (`ABC1234`) ou Mercosul (`ABC1D23`).

**Exemplo de Resposta:**
```json
{
  "plate": "ABC1D23",
  "status": "SUCCESS",
  "vehicle": {
    "id": 58291,
    "make": "Volkswagen",
    "model": "T-Cross",
    "version": "Comfortline 200 TSI",
    "year_manufacture": 2022,
    "year_model": 2023,
    "engine": "1.0 TSI",
    "fuel": "Flex",
    "transmission": "Automático 6v",
    "fipe_code": "005512-3"
  },
  "is_ambiguous": false,
  "cache_info": {
    "source": "MOCK_PROVIDER",
    "consulted_at": "2025-01-15T10:30:00Z",
    "expires_at": "2025-04-15T10:30:00Z",
    "data_quality": "HIGH",
    "confidence": 1.0
  }
}
```

### 2. Pesquisar Peças Compatíveis
`GET /api/v1/parts/search`

**Query Parameters:**
- `plate`: Placa do veículo (obrigatório)
- `query`: Termo de busca da peça (ex: `disco de freio`)

**Exemplo de Resposta:**
```json
{
  "vehicle": {
    "id": 58291,
    "make": "Volkswagen",
    "model": "T-Cross",
    "year": 2023,
    "engine": "1.0 TSI"
  },
  "query": "disco de freio",
  "category_identified": "BRAKE_DISC",
  "status": "SUCCESS",
  "results_count": 1,
  "results": [
    {
      "part_id": 101,
      "manufacturer": "Fremax",
      "manufacturer_code": "BD1234",
      "ean": "7891234567890",
      "description": "Disco de Freio Dianteiro Ventilado",
      "position": "Dianteiro",
      "compatibility": "CONFIRMED",
      "confidence": 1.0,
      "source": "CATALOG_FREMAX_2024",
      "erp_mapping": {
        "erp_product_id": "AUTCOM-PRD-9988",
        "verified": true,
        "confidence": 1.0
      }
    }
  ]
}
```
