import csv
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple
import openpyxl
from sqlalchemy.orm import Session

from app.db.models import (
    Part, PartManufacturer, PartCategory, PartApplication,
    Vehicle, VehicleMake, VehicleModel, VehicleEngine, SyncLog, ConfidenceLevel
)
from app.services.vehicle_normalizer import normalize_make, normalize_model, normalize_engine
from app.services.query_normalizer import normalize_part_query

class CatalogImporter:
    def __init__(self, db: Session):
        self.db = db

    def import_from_csv(self, file_content: str, source_name: str = "CSV_IMPORT") -> Dict[str, Any]:
        lines = file_content.strip().splitlines()
        reader = csv.DictReader(lines)
        records = [row for row in reader]
        return self._process_records(records, source_name)

    def import_from_json(self, json_str: str, source_name: str = "JSON_IMPORT") -> Dict[str, Any]:
        records = json.loads(json_str)
        if isinstance(records, dict) and "data" in records:
            records = records["data"]
        return self._process_records(records, source_name)

    def import_from_xlsx(self, file_bytes: bytes, source_name: str = "XLSX_IMPORT") -> Dict[str, Any]:
        from io import BytesIO
        wb = openpyxl.load_workbook(filename=BytesIO(file_bytes))
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return {"status": "FAILED", "processed": 0, "success": 0, "failed": 0, "message": "Empty file"}

        headers = [str(h).strip().lower() for h in rows[0]]
        records = []
        for row in rows[1:]:
            record = {headers[i]: str(row[i]).strip() if row[i] is not None else "" for i in range(min(len(headers), len(row)))}
            records.append(record)
        return self._process_records(records, source_name)

    def import_from_xml(self, xml_str: str, source_name: str = "XML_IMPORT") -> Dict[str, Any]:
        root = ET.fromstring(xml_str)
        records = []
        for item in root.findall(".//item"):
            rec = {}
            for child in item:
                rec[child.tag.lower()] = child.text.strip() if child.text else ""
            records.append(rec)
        return self._process_records(records, source_name)

    def _process_records(self, records: List[Dict[str, Any]], source_name: str) -> Dict[str, Any]:
        processed = 0
        success = 0
        failed = 0
        errors = []

        for row in records:
            processed += 1
            try:
                # Normalize key names
                rec = {str(k).lower().strip(): str(v).strip() for k, v in row.items()}

                mfg_name = rec.get("fabricante") or rec.get("manufacturer") or rec.get("marca_peca") or "GENERIC"
                code = rec.get("codigo") or rec.get("code") or rec.get("part_number") or rec.get("part_code")
                category_name = rec.get("categoria") or rec.get("category") or rec.get("produto") or rec.get("description") or "OUTROS"
                desc = rec.get("descricao") or rec.get("description") or category_name
                ean = rec.get("ean") or rec.get("gtin")

                v_make = normalize_make(rec.get("marca_veiculo") or rec.get("make") or rec.get("montadora") or "")
                v_model = normalize_model(rec.get("modelo_veiculo") or rec.get("model") or rec.get("modelo") or "")
                v_engine = normalize_engine(rec.get("motor") or rec.get("engine") or "")
                year_from = int(rec.get("ano_inicio") or rec.get("year_from") or 2000)
                year_to = int(rec.get("ano_fim") or rec.get("year_to") or 2025)
                position = rec.get("posicao") or rec.get("position") or "Dianteiro"

                if not code or not v_make or not v_model:
                    failed += 1
                    errors.append(f"Row {processed}: Missing essential fields (code, vehicle make, or model)")
                    continue

                # 1. Get/Create Part Manufacturer
                mfg = self.db.query(PartManufacturer).filter(PartManufacturer.name == mfg_name).first()
                if not mfg:
                    mfg = PartManufacturer(name=mfg_name)
                    self.db.add(mfg)
                    self.db.flush()

                # 2. Get/Create Part Category
                cat_code = normalize_part_query(category_name) or "GENERAL_PARTS"
                cat = self.db.query(PartCategory).filter(PartCategory.code == cat_code).first()
                if not cat:
                    cat = PartCategory(code=cat_code, name=category_name.upper())
                    self.db.add(cat)
                    self.db.flush()

                # 3. Get/Create Part
                part = self.db.query(Part).filter(
                    Part.manufacturer_id == mfg.id,
                    Part.manufacturer_part_number == code
                ).first()
                if not part:
                    part = Part(
                        manufacturer_id=mfg.id,
                        category_id=cat.id,
                        manufacturer_part_number=code,
                        ean=ean,
                        description=desc
                    )
                    self.db.add(part)
                    self.db.flush()

                # 4. Get/Create Vehicle
                make_entity = self.db.query(VehicleMake).filter(VehicleMake.name == v_make).first()
                if not make_entity:
                    make_entity = VehicleMake(name=v_make, normalized_name=v_make.upper())
                    self.db.add(make_entity)
                    self.db.flush()

                model_entity = self.db.query(VehicleModel).filter(
                    VehicleModel.make_id == make_entity.id,
                    VehicleModel.normalized_name == v_model.upper()
                ).first()
                if not model_entity:
                    model_entity = VehicleModel(make_id=make_entity.id, name=v_model, normalized_name=v_model.upper())
                    self.db.add(model_entity)
                    self.db.flush()

                engine_entity = self.db.query(VehicleEngine).filter(VehicleEngine.description == v_engine).first()
                if not engine_entity:
                    engine_entity = VehicleEngine(description=v_engine)
                    self.db.add(engine_entity)
                    self.db.flush()

                vehicle_entity = self.db.query(Vehicle).filter(
                    Vehicle.make_id == make_entity.id,
                    Vehicle.model_id == model_entity.id,
                    Vehicle.year_manufacture == year_from,
                    Vehicle.year_model == year_to
                ).first()
                if not vehicle_entity:
                    vehicle_entity = Vehicle(
                        make_id=make_entity.id,
                        model_id=model_entity.id,
                        engine_id=engine_entity.id,
                        year_manufacture=year_from,
                        year_model=year_to
                    )
                    self.db.add(vehicle_entity)
                    self.db.flush()

                # 5. Create Part Application
                app_match = self.db.query(PartApplication).filter(
                    PartApplication.part_id == part.id,
                    PartApplication.vehicle_id == vehicle_entity.id
                ).first()
                if not app_match:
                    app_match = PartApplication(
                        part_id=part.id,
                        vehicle_id=vehicle_entity.id,
                        year_from=year_from,
                        year_to=year_to,
                        position=position,
                        source=source_name,
                        confidence=ConfidenceLevel.CONFIRMED
                    )
                    self.db.add(app_match)

                success += 1

            except Exception as e:
                failed += 1
                errors.append(f"Row {processed}: Error - {str(e)}")

        self.db.commit()

        # Log sync
        sync_log = SyncLog(
            source_name=source_name,
            records_processed=processed,
            records_success=success,
            records_failed=failed,
            status="SUCCESS" if failed == 0 else ("COMPLETED_WITH_ERRORS" if success > 0 else "FAILED"),
            details="\n".join(errors[:20]) if errors else "Imported successfully"
        )
        self.db.add(sync_log)
        self.db.commit()

        return {
            "status": sync_log.status,
            "processed": processed,
            "success": success,
            "failed": failed,
            "errors": errors[:10]
        }
