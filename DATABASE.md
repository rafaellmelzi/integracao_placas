# Modelagem de Banco de Dados

## Entidades Principais

### Veículos e Cache
- `vehicle_make`: Marcas (ex: Volkswagen, Chevrolet)
- `vehicle_model`: Modelos (ex: T-Cross, Onix)
- `vehicle_generation`: Geração (ex: Mk1, G1)
- `vehicle_version`: Versão (ex: Comfortline, LTZ)
- `vehicle_engine`: Motorização (ex: 1.0 TSI, 1.4 Turbo)
- `vehicle_transmission`: Transmissão (ex: Manual 5v, Automático 6v)
- `vehicle_fuel`: Combustível (ex: Flex, Gasolina, Diesel)
- `vehicle`: Entidade unificada representando uma configuração específica de veículo.
- `vehicle_plate_cache`: Cache local de placas com campos de auditoria (`source`, `source_vehicle_id`, `consulted_at`, `updated_at`, `expires_at`, `data_quality`, `confidence`, `raw_response_hash`).

### Peças e Aplicabilidade
- `part_manufacturer`: Fabricantes de peças (ex: Fremax, Bosch, Cobreq)
- `part_category`: Categorias e sinônimos (ex: BRAKE_DISC)
- `part`: Peças do catálogo (`manufacturer_part_number`, `ean`, `description`)
- `part_application`: Aplicabilidade veículo-peça (`year_from`, `year_to`, `position`, `confidence`, `notes`)
- `part_cross_reference`: Equivalências (`OEM`, `AFTERMARKET`, `EQUIVALENT`, `REPLACEMENT`)

### ERP e Auditoria
- `erp_product_mapping`: Vínculo entre produtos do Autcom ERP e peças da base.
- `data_source`: Fornecedores configurados.
- `api_request_log`: Logs de auditoria de chamadas de API.
- `sync_log`: Registros de importação de catálogos.
