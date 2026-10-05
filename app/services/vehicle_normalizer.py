import re
import unicodedata
from typing import Optional, Dict, Any

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
        if "TSI" in clean or "TURBO" in clean or "1.0T" in clean or "TB" in clean:
            return "1.0 TSI"
        return "1.0"
    elif "1.4" in clean:
        if "TSI" in clean or "TURBO" in clean or "1.4T" in clean or "TB" in clean:
            return "1.4 TSI"
        return "1.4"
    elif "1.6" in clean:
        return "1.6 16V"
    elif "2.0" in clean:
        return "2.0"
    return clean

def parse_version_specs(version_name: Optional[str]) -> Dict[str, Any]:
    """
    Conservative parser for vehicle version text descriptions (e.g. 'ONIX HATCH LTZ 1.0 12V TB Flex 5p Aut.').
    Extracts explicitly stated displacement, valves, fuel, transmission, and generates a structured engine description.
    Never invents unstated fields (like power_hp or gears). Returns NULL for absent features.
    """
    if not version_name or not version_name.strip():
        return {"displacement": None, "valves": None, "engine_desc": None, "transmission": None, "fuel": None}

    clean = normalize_text(version_name)

    # 1. Displacement (e.g. 1.0, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0, 2.4, 3.0, 3.8, V6, V8)
    disp_match = re.search(r'\b([0-9]\.[0-9]|V6|V8|W12|V10)\b', clean)
    displacement = disp_match.group(1) if disp_match else None

    # 2. Valves (e.g. 8V, 12V, 16V, 24V)
    valve_match = re.search(r'\b(8|12|16|20|24)V\b', clean)
    valves = int(valve_match.group(1)) if valve_match else None

    # 3. Turbo / Induction indicators (e.g. TURBO, TB, TSI, TFSI, BITURBO)
    has_turbo = bool(re.search(r'\b(TURBO|TB|TSI|TFSI|BITURBO|T)\b', clean))

    # 4. Transmission (e.g. AUT, AUTOMATICO, MEC, MANUAL, CVT, DCT)
    transmission = None
    if re.search(r'\b(AUT|AUTOMATICO|AUTOMATICA)\b', clean):
        transmission = "Automático"
    elif re.search(r'\b(MEC|MANUAL)\b', clean):
        transmission = "Manual"
    elif "CVT" in clean:
        transmission = "CVT"

    # 5. Fuel (e.g. FLEX, GASOLINA, DIESEL, ELETRICO, HIBRIDO)
    fuel = None
    if "FLEX" in clean:
        fuel = "Flex"
    elif "DIESEL" in clean:
        fuel = "Diesel"
    elif "GASOLINA" in clean:
        fuel = "Gasolina"
    elif "ELETRICO" in clean or "ELECTRIC" in clean:
        fuel = "Eletrico"
    elif "HIBRIDO" in clean or "HYBRID" in clean:
        fuel = "Hibrido"

    # Construct Engine Description if displacement or turbo is present
    engine_desc = None
    if displacement:
        parts = [displacement]
        if valves:
            parts.append(f"{valves}V")
        if has_turbo and "TSI" not in displacement:
            parts.append("Turbo")
        engine_desc = " ".join(parts)
    elif has_turbo:
        engine_desc = "Turbo"

    return {
        "displacement": displacement,
        "valves": valves,
        "engine_desc": engine_desc,
        "transmission": transmission,
        "fuel": fuel
    }
