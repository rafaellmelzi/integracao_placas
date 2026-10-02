import csv
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional
import openpyxl
from sqlalchemy.orm import Session

from app.db.models import (
    Part, PartManufacturer, PartCategory, PartApplication,
    Vehicle, VehicleMake, VehicleModel, VehicleEngine, SyncLog, ConfidenceLevel
)
from app.services.vehicle_normalizer import normalize_make, normalize_model, normalize_engine
from app.services.query_normalizer import normalize_part_query

DEFAULT_COLUMN_MAPPING = {
    "codigo": "part_number",
    "code": "part_number",
    "part_number": "part_number",
    "cod_peca": "part_number",
    "fabricante": "manufacturer",
    "manufacturer": "manufacturer",
    "marca_peca": "manufacturer",
    "categoria": "category",
    "category": "category",
    "produto": "category",
    "descricao": "description",
    "description": "description",
    "ean": "ean",
    "gtin": "ean",
    "oem": "oem_codes",
    "codigo_oem": "oem_codes",
    "oem_codes": "oem_codes",
    "especificacoes": "technical_specs",
    "technical_specs": "technical_specs",
    "specs": "technical_specs",
    "marca_veiculo": "make",
    "make": "make",
    "montadora": "make",
    "modelo_veiculo": "model",
    "model": "model",
    "modelo": "model",
    "motor": "engine",
    "engine": "engine",
    "ano_inicio": "year_from",
    "year_from": "year_from",
    "ano_inicial": "year_from",
    "ano_fim": "year_to",
    "year_to": "year_to",
    "ano_final": "year_to",
    "posicao": "position",
    "position": "position",
    "eixo": "axis",
    "axis": "axis",
    "observacoes": "notes",
    "notes": "notes"
}

class CatalogImporter:
    def __init__(self, db: Session):
        self.db = db

    def import_from_csv(self, file_content: str, source_name: str = "CSV_IMPORT", column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        lines = file_content.strip().splitlines()
        reader = csv.DictReader(lines)
        records = [row for row in reader]
        return self._process_records(records, source_name, column_mapping)

    def import_from_json(self, json_str: str, source_name: str = "JSON_IMPORT", column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        records = json.loads(json_str)
        if isinstance(records, dict) and "data" in records:
            records = records["data"]
        return self._process_records(records, source_name, column_mapping)

    def import_from_xlsx(self, file_bytes: bytes, source_name: str = "XLSX_IMPORT", column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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
        return self._process_records(records, source_name, column_mapping)

    def import_from_xml(self, xml_str: str, source_name: str = "XML_IMPORT", column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        root = ET.fromstring(xml_str)
        records = []
        for item in root.findall(".//item"):
            rec = {}
            for child in item:
                rec[child.tag.lower()] = child.text.strip() if child.text else ""
            records.append(rec)
        return self._process_records(records, source_name, column_mapping)

    def _process_records(self, records: List[Dict[str, Any]], source_name: str, column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        mapping = DEFAULT_COLUMN_MAPPING.copy()
        if column_mapping:
            mapping.update({k.lower().strip(): v.lower().strip() for k, v in column_mapping.items()})

        processed = 0
        success = 0
        failed = 0
        errors = []

        for row in records:
            processed += 1
            try:
                # Standardize keys using mapping
                standardized = {}
                for raw_k, raw_v in row.items():
                    key_clean = str(raw_k).lower().strip()
                    val_clean = str(raw_v).strip() if raw_v is not None else ""
                    mapped_target = mapping.get(key_clean, key_clean)
                    standardized[mapped_target] = val_clean

                code = standardized.get("part_number")
                mfg_name = standardized.get("manufacturer") or "FABRICANTE_GENERICO"
                category_name = standardized.get("category") or standardized.get("description") or "OUTROS"
                desc = standardized.get("description") or category_name
                ean = standardized.get("ean")
                oem_codes = standardized.get("oem_codes")
                tech_specs = standardized.get("technical_specs")

                v_make = normalize_make(standardized.get("make"))
                v_model = normalize_model(standardized.get("model"))
                v_engine = normalize_engine(standardized.get("engine"))
                year_from = int(standardized.get("year_from")) if standardized.get("year_from") and str(standardized.get("year_from")).isdigit() else 2000
                year_to = int(standardized.get("year_to")) if standardized.get("year_to") and str(standardized.get("year_to")).isdigit() else 2025
                position = standardized.get("position") or "Dianteiro"
                axis = standardized.get("axis") or "Dianteiro"
                notes = standardized.get("notes")

                if not code or not v_make or not v_model:
                    failed += 1
                    errors.append(f"Linha {processed}: Campos essenciais ausentes (código da peça, marca ou modelo do veículo)")
                    continue

                # 1. Manufacturer
                mfg = self.db.query(PartManufacturer).filter(PartManufacturer.name == mfg_name).first()
                if not mfg:
                    mfg = PartManufacturer(name=mfg_name)
                    self.db.add(mfg)
                    self.db.flush()

                # 2. Category
                cat_code = normalize_part_query(category_name) or "GENERAL_PARTS"
                cat = self.db.query(PartCategory).filter(PartCategory.code == cat_code).first()
                if not cat:
                    cat = PartCategory(code=cat_code, name=category_name.upper())
                    self.db.add(cat)
                    self.db.flush()

                # 3. Part (avoid duplicate code per manufacturer)
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
                        description=desc,
                        oem_codes=oem_codes,
                        technical_specs=tech_specs,
                        source=f"IMPORTACAO_{source_name.upper()}"
                    )
                    self.db.add(part)
                    self.db.flush()
                else:
                    if oem_codes and not part.oem_codes:
                        part.oem_codes = oem_codes
                    if tech_specs and not part.technical_specs:
                        part.technical_specs = tech_specs

                # 4. Vehicle
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

                engine_entity = None
                if v_engine:
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
                        engine_id=engine_entity.id if engine_entity else None,
                        year_manufacture=year_from,
                        year_model=year_to
                    )
                    self.db.add(vehicle_entity)
                    self.db.flush()

                # 5. Application Relationship
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
                        axis=axis,
                        notes=notes,
                        source=f"IMPORTACAO_{source_name.upper()}",
                        confidence=ConfidenceLevel.CONFIRMED
                    )
                    self.db.add(app_match)

                success += 1

            except Exception as e:
                failed += 1
                errors.append(f"Linha {processed}: Erro - {str(e)}")

        self.db.commit()

        sync_log = SyncLog(
            source_name=source_name,
            records_processed=processed,
            records_success=success,
            records_failed=failed,
            status="SUCCESS" if failed == 0 else ("COMPLETED_WITH_ERRORS" if success > 0 else "FAILED"),
            details="\n".join(errors[:20]) if errors else "Importado com sucesso"
        )
        self.db.add(sync_log)
        self.db.commit()

        return {
            "status": sync_log.status,
            "source_name": source_name,
            "processed": processed,
            "success": success,
            "failed": failed,
            "errors": errors[:10]
        }
