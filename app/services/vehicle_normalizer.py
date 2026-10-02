import re
import unicodedata
from typing import Optional, Dict

MAKE_ALIASES: Dict[str, str] = {
    "VW": "Volkswagen",
    "VOLKSWAGEN": "Volkswagen",
    "VOLKSWAGEN DO BRASIL": "Volkswagen",
    "GM": "Chevrolet",
    "CHEVROLET": "Chevrolet",
    "CHEVROLET/GM": "Chevrolet",
    "GENERAL MOTORS": "Chevrolet",
    "FIAT": "Fiat",
    "FIAT AUTOMOVEIS": "Fiat",
    "FORD": "Ford",
    "FORD BRASIL": "Ford",
    "TOYOTA": "Toyota",
    "HONDA": "Honda",
    "HYUNDAI": "Hyundai",
    "RENAULT": "Renault",
    "NISSAN": "Nissan",
    "PEUGEOT": "Peugeot",
    "CITROEN": "Citroën",
    "JEEP": "Jeep"
}

def remove_accents(text: str) -> str:
    text = unicodedata.normalize('NFD', text)
    return ''.join(c for c in text if unicodedata.category(c) != 'Mn')

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = remove_accents(text.strip().upper())
    text = re.sub(r'[^A-Z0-9\s\.\-]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def normalize_make(make_raw: Optional[str]) -> Optional[str]:
    if not make_raw:
        return None
    clean = normalize_text(make_raw)
    if not clean:
        return None
    return MAKE_ALIASES.get(clean, make_raw.strip().title())

def normalize_model(model_raw: Optional[str]) -> Optional[str]:
    if not model_raw:
        return None
    clean = normalize_text(model_raw)
    if not clean:
        return None
    for brand, canonical in MAKE_ALIASES.items():
        if clean.startswith(brand + " "):
            clean = clean[len(brand) + 1:].strip()
    return clean.title()

def normalize_engine(engine_raw: Optional[str]) -> Optional[str]:
    if not engine_raw or not engine_raw.strip():
        return None
    clean = normalize_text(engine_raw)
    if not clean:
        return None
    if "1.0" in clean:
        if "TSI" in clean or "TURBO" in clean:
            return "1.0 TSI"
        return "1.0"
    elif "1.4" in clean:
        if "TSI" in clean or "TURBO" in clean:
            return "1.4 TSI"
        return "1.4"
    elif "1.6" in clean:
        return "1.6 16V"
    elif "2.0" in clean:
        return "2.0"
    return clean
