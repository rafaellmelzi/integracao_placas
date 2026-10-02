import hashlib
import json
from typing import Dict, Any, Optional
from app.providers.base_plate_provider import BasePlateProvider

MOCK_VEHICLES_DATABASE = {
    "ABC1D23": {
        "make": "Volkswagen",
        "model": "T-Cross",
        "version": "Comfortline 200 TSI",
        "year_manufacture": 2022,
        "year_model": 2023,
        "engine": "1.0 TSI",
        "fuel": "Flex",
        "transmission": "Automático 6v",
        "fipe_code": "005512-3",
        "source_vehicle_id": "VW-TCROSS-10TSI-2023",
        "data_quality": "HIGH",
        "confidence": 1.0,
        "is_ambiguous": False
    },
    "ABC1234": {
        "make": "Volkswagen",
        "model": "Gol",
        "version": "1.0 8V",
        "year_manufacture": 2018,
        "year_model": 2019,
        "engine": "1.0 8V",
        "fuel": "Flex",
        "transmission": "Manual 5v",
        "fipe_code": "005110-1",
        "source_vehicle_id": "VW-GOL-108V-2019",
        "data_quality": "HIGH",
        "confidence": 1.0,
        "is_ambiguous": False
    },
    "XYZ9876": {
        "make": "Chevrolet",
        "model": "Onix",
        "version": "LT Turbo",
        "year_manufacture": 2021,
        "year_model": 2022,
        "engine": "1.0 Turbo",
        "fuel": "Flex",
        "transmission": "Manual 6v",
        "fipe_code": "004480-2",
        "source_vehicle_id": "GM-ONIX-10T-2022",
        "data_quality": "HIGH",
        "confidence": 0.95,
        "is_ambiguous": False
    },
    "AMB1G88": {
        "make": "Volkswagen",
        "model": "Polo",
        "version": "Ambiguous Variant 1.0",
        "year_manufacture": 2020,
        "year_model": 2021,
        "engine": "1.0 MPI / TSI",
        "fuel": "Flex",
        "transmission": "Manual 5v",
        "fipe_code": "005470-4",
        "source_vehicle_id": "VW-POLO-VARIANTS",
        "data_quality": "MEDIUM",
        "confidence": 0.70,
        "is_ambiguous": True
    }
}

class MockPlateProvider(BasePlateProvider):
    @property
    def provider_name(self) -> str:
        return "MOCK_PROVIDER"

    def fetch_plate_info(self, plate: str) -> Optional[Dict[str, Any]]:
        clean_plate = plate.upper().replace("-", "").strip()
        data = MOCK_VEHICLES_DATABASE.get(clean_plate)
        if not data:
            return None

        raw_json_str = json.dumps(data, sort_keys=True)
        raw_hash = hashlib.sha256(raw_json_str.encode('utf-8')).hexdigest()

        result = data.copy()
        result["raw_data"] = data
        result["raw_response_hash"] = raw_hash
        return result
