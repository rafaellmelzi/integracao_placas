# Arquitetura do Sistema

## Visão Geral

O sistema utiliza a arquitetura limpa (*Clean Architecture*) com o padrão de adaptadores (*Adapter Pattern*) para desacoplar fornecedores externos de dados de consulta de placa e de aplicabilidade.

## Princípios de Design

1. **Provider Isolation (Pluggable Adapters):**
   - As consultas de placas utilizam a interface `BasePlateProvider`. Implementações concretas incluem `MockPlateProvider`, `SerproPlateProvider`, `ApiPlacaProvider`.
   - Se um provedor ficar indisponível, o sistema tenta o próximo adapter configurado.

2. **Normalização e Ambiguidade:**
   - Termos e variações de veículos enviados por APIs externas são normalizados para entidades internas (`vehicle_make`, `vehicle_model`, `vehicle_version`, `vehicle_engine`).
   - Caso os dados de retorno da placa não determinem uma única versão com 100% de precisão, o veículo é marcado com `VEHICLE_VARIANT_AMBIGUOUS`, e a busca de peças retorna todas as variações possíveis sinalizando o status.

3. **Pesquisa Inteligente e Sinônimos:**
   - A busca por termos ("disco de freio", "disco", "disco freio") é normalizada para uma categoria interna (ex.: `BRAKE_DISC`) por meio de um dicionário e normalizador.

4. **Níveis de Confiança de Aplicabilidade:**
   - `CONFIRMED`: Confirmado por catálogo oficial do fabricante.
   - `HIGH_CONFIDENCE`: Encontrado por código cruzado/OEM verificado.
   - `POSSIBLE`: Compatível por especificação genérica ou sugestão.
   - `UNVERIFIED`: Associação sem confirmação inequívoca.
