from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

# Vehicle Schemas
class VehicleResponseSchema(BaseModel):
    id: int
    make: str
    model: str
    version: Optional[str] = ""
    year_manufacture: int
    year_model: int
    engine: Optional[str] = ""
    fuel: Optional[str] = ""
    transmission: Optional[str] = ""
    fipe_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CacheInfoSchema(BaseModel):
    source: str
    consulted_at: str
    expires_at: str
    data_quality: str
    confidence: float
    from_cache: bool

class PlateLookupResponseSchema(BaseModel):
    plate: str
    status: str
    vehicle: Optional[VehicleResponseSchema] = None
    is_ambiguous: bool = False
    possible_vehicle_ids: Optional[List[int]] = []
    cache_info: Optional[CacheInfoSchema] = None
    message: Optional[str] = None

# Parts Schemas
class ERPProductMappingSchema(BaseModel):
    erp_product_id: str
    verified: bool
    mapping_type: str
    confidence: str

class CrossReferenceSchema(BaseModel):
    manufacturer: str
    code: str
    type: str
    confidence: str

class PartResultSchema(BaseModel):
    part_id: int
    manufacturer: str
    manufacturer_code: str
    ean: Optional[str] = None
    description: str
    category: str
    position: Optional[str] = None
    compatibility: str
    confidence_score: float
    source: str
    notes: Optional[str] = None
    cross_references: List[CrossReferenceSchema] = []
    erp_mapping: Optional[ERPProductMappingSchema] = None

class PartsSearchResponseSchema(BaseModel):
    vehicle: Optional[VehicleResponseSchema] = None
    query: str
    category_identified: Optional[str] = None
    status: str
    results_count: int = 0
    results: List[PartResultSchema] = []
    message: Optional[str] = None

# ERP Mapping Create/Update Schema
class ERPProductMappingCreateSchema(BaseModel):
    erp_product_id: str
    part_id: Optional[int] = None
    manufacturer_code: Optional[str] = None
    ean: Optional[str] = None
    mapping_type: str = "MANUFACTURER_CODE"
    verified: bool = True
