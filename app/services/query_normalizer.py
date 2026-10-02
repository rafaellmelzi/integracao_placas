import re
from typing import Optional, Dict

CATEGORY_SYNONYMS: Dict[str, list[str]] = {
    "BRAKE_DISC": [
        "DISCO", "DISCO DE FREIO", "DISCO FREIO", "DISCOS", "DISCO DE FREIO DIANTEIRO", "DISCO DE FREIO TRASEIRO"
    ],
    "BRAKE_PAD": [
        "PASTILHA", "PASTILHA DE FREIO", "PASTILHAS", "PASTILHA FREIO"
    ],
    "SHOCK_ABSORBER": [
        "AMORTECEDOR", "AMORTECEDORES", "AMORTECEDOR DIANTEIRO", "AMORTECEDOR TRASEIRO"
    ],
    "OIL_FILTER": [
        "FILTRO DE OLEO", "FILTRO OLEO", "FILTRO DE OLEO LUBRIFICANTE"
    ],
    "TIMING_BELT": [
        "CORREIA DENTADA", "CORREIA DE TRANSMISSAO", "CORREIA DENTADA DO MOTOR", "CORREIA"
    ],
    "CLUTCH_KIT": [
        "KIT EMBREAGEM", "KIT DE EMBREAGEM", "EMBREAGEM"
    ]
}

def normalize_part_query(query: str) -> Optional[str]:
    if not query:
        return None
    clean = re.sub(r'[^A-Z0-9\s]', '', query.strip().upper())
    clean = re.sub(r'\s+', ' ', clean)

    for category_code, synonyms in CATEGORY_SYNONYMS.items():
        for syn in synonyms:
            if syn in clean or clean in syn:
                return category_code

    return None
