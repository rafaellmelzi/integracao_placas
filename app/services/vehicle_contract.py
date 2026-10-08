"""Canonical, conservative input contract for parts applicability evaluation."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional
import re

from app.services.vehicle_normalizer import normalize_make, normalize_text, parse_version_specs


class Compatibility(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    CONDITIONAL = "CONDITIONAL"
    INCOMPATIBLE = "INCOMPATIBLE"


def normalize_transmission(value: Any) -> Optional[str]:
    clean = normalize_text(str(value)) if value else ""
    if clean in {"AUT", "AUTOMATICO", "AUTOMATICA"}:
        return "Automático"
    if clean in {"MEC", "MECANICO", "MECANICA", "MANUAL"}:
        return "Manual"
    return clean or None


@dataclass(frozen=True)
class MatchingVehicle:
    make: str = ""
    model: str = ""
    version: Optional[str] = None
    model_year: Optional[int] = None
    manufacture_year: Optional[int] = None
    engine_displacement: Optional[str] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    drivetrain: Optional[str] = None
    valves: Optional[int] = None
    turbo: Optional[bool] = None

    @classmethod
    def from_mapping(cls, vehicle: Mapping[str, Any]) -> "MatchingVehicle":
        def year(*keys):
            value = next((vehicle.get(k) for k in keys if vehicle.get(k) is not None), None)
            try:
                result = int(value)
                return result if 1900 <= result <= 2099 else None
            except (ValueError, TypeError):
                return None

        engine = vehicle.get("engine_displacement") or vehicle.get("engine")
        specs = parse_version_specs(str(engine).replace(",", ".")) if engine else {}
        engine_text = normalize_text(str(engine or "").replace(",", "."))
        displacement = re.search(r"\b([0-9]\.[0-9]|V6|V8|W12|V10)(?:L)?\b", engine_text)
        turbo = vehicle.get("turbo")
        if turbo is None and re.search(r"\b(TURBO|TSI|TFSI|TB)\b", engine_text):
            turbo = True
        elif turbo is None and "ASPIRADO" in engine_text:
            turbo = False
        fuel = normalize_text(str(vehicle.get("fuel") or "")) or None
        fuel = {"ETANOL": "ALCOOL", "GASOLINA E ALCOOL": "FLEX"}.get(fuel, fuel)
        drivetrain = normalize_text(str(vehicle.get("drivetrain") or "")) or None
        drivetrain = {"FWD": "4X2", "AWD": "4X4"}.get(drivetrain, drivetrain)
        return cls(
            make=normalize_text(normalize_make(vehicle.get("make")) or ""),
            model=normalize_text(str(vehicle.get("model") or "")),
            version=normalize_text(str(vehicle.get("version") or "")) or None,
            model_year=year("model_year", "year_model"),
            manufacture_year=year("manufacture_year", "year_manufacture"),
            engine_displacement=displacement[1] if displacement else None,
            fuel=fuel,
            transmission=normalize_transmission(vehicle.get("transmission")),
            drivetrain=drivetrain,
            valves=vehicle.get("valves") or specs.get("valves"),
            turbo=turbo,
        )
