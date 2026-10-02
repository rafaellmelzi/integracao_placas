from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.database import get_db
from app.schemas.schemas import (
    PlateLookupResponseSchema, PartsSearchResponseSchema,
    ERPProductMappingCreateSchema, ERPProductMappingSchema
)
from app.services.plate_lookup_service import PlateLookupService
from app.services.parts_search_service import PartsSearchService
from app.importers.catalog_importer import CatalogImporter
from app.db.models import ERPProductMapping, ERPProductMappingType, ConfidenceLevel, Part

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Healthcheck endpoint verifying DB connectivity and provider configuration status.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    plate_provider_status = "configured" if (settings.VEHICLE_PROVIDER.upper() == "MOCK" or bool(settings.VEHICLE_API_KEY)) else "not_configured"
    catalog_parts_count = db.query(Part).count()
    catalog_status = "configured" if catalog_parts_count > 0 else "not_configured"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "app_env": settings.APP_ENV,
        "database": db_status,
        "plate_provider": settings.VEHICLE_PROVIDER,
        "plate_provider_status": plate_provider_status,
        "catalog_status": catalog_status,
        "catalog_parts_count": catalog_parts_count
    }

@router.get("/vehicles/plate/{plate}", response_model=PlateLookupResponseSchema)
def lookup_vehicle_by_plate(plate: str, db: Session = Depends(get_db)):
    """
    Look up vehicle information by old or Mercosul license plate.
    """
    try:
        service = PlateLookupService(db)
        res = service.get_or_fetch_plate(plate)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/parts/search", response_model=PartsSearchResponseSchema)
def search_parts(
    plate: str = Query(..., description="Vehicle plate number"),
    query: str = Query(..., description="Part query term, e.g. 'disco de freio'"),
    db: Session = Depends(get_db)
):
    """
    Search for compatible auto parts by vehicle plate and item name/category.
    """
    try:
        service = PartsSearchService(db)
        return service.search_parts_by_plate_and_query(plate, query)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/erp/mapping")
def create_or_update_erp_mapping(payload: ERPProductMappingCreateSchema, db: Session = Depends(get_db)):
    """
    Create or update an Autcom ERP Product mapping to a catalog part.
    """
    mapping = db.query(ERPProductMapping).filter(ERPProductMapping.erp_product_id == payload.erp_product_id).first()
    if not mapping:
        mapping = ERPProductMapping(
            erp_product_id=payload.erp_product_id,
            part_id=payload.part_id,
            manufacturer_code=payload.manufacturer_code,
            ean=payload.ean,
            mapping_type=ERPProductMappingType[payload.mapping_type],
            confidence=ConfidenceLevel.CONFIRMED if payload.verified else ConfidenceLevel.UNVERIFIED,
            verified=payload.verified
        )
        db.add(mapping)
    else:
        mapping.part_id = payload.part_id
        mapping.manufacturer_code = payload.manufacturer_code
        mapping.ean = payload.ean
        mapping.mapping_type = ERPProductMappingType[payload.mapping_type]
        mapping.verified = payload.verified
        mapping.confidence = ConfidenceLevel.CONFIRMED if payload.verified else ConfidenceLevel.UNVERIFIED

    db.commit()
    return {"status": "SUCCESS", "erp_product_id": payload.erp_product_id}

@router.post("/catalog/import")
async def import_catalog_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Import catalog applicability data from CSV, XLSX, JSON, or XML files.
    """
    importer = CatalogImporter(db)
    filename = file.filename.lower()
    content_bytes = await file.read()

    if filename.endswith(".csv"):
        res = importer.import_from_csv(content_bytes.decode("utf-8", errors="ignore"), source_name=filename)
    elif filename.endswith(".xlsx"):
        res = importer.import_from_xlsx(content_bytes, source_name=filename)
    elif filename.endswith(".json"):
        res = importer.import_from_json(content_bytes.decode("utf-8", errors="ignore"), source_name=filename)
    elif filename.endswith(".xml"):
        res = importer.import_from_xml(content_bytes.decode("utf-8", errors="ignore"), source_name=filename)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Allowed: .csv, .xlsx, .json, .xml")

    return res
