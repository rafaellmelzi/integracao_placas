from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Vehicle Schemas
class VehicleResponseSchema(BaseModel):
    id: Optional[int] = None
    make: str
    model: str
    version: Optional[str] = None
    year_manufacture: Optional[int] = None
    year_model: Optional[int] = None
    engine: Optional[str] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
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
    axis: Optional[str] = None
    compatibility: str
    confidence_score: float
    source: str
    oem_codes: Optional[str] = None
    equivalent_codes: Optional[str] = None
    technical_specs: Optional[str] = None
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


class ApplicationMatchDetailsSchema(BaseModel):
    reason: str
    matched: List[str]
    unknown: List[str]
    conflicts: List[str]


class ApplicableERPPartSchema(BaseModel):
    internal_code: str
    factory_code: Optional[str]
    description: str
    brand: Optional[str]
    application: Optional[str]
    compatibility: Literal["COMPATIBLE", "CONDITIONAL"]
    compatibility_score: int = Field(ge=0, le=100)
    requires_confirmation: bool
    match_details: ApplicationMatchDetailsSchema
    availability: List[Dict[str, Any]]

    @model_validator(mode="after")
    def consistent_compatibility(self):
        conditional = self.compatibility == "CONDITIONAL"
        if self.requires_confirmation != conditional or bool(self.match_details.unknown) != conditional:
            raise ValueError("Classification must agree with confirmation requirements")
        if self.match_details.conflicts:
            raise ValueError("An applicable part cannot contain attribute conflicts")
        return self


class PlatePartsResponseSchema(BaseModel):
    plate: str
    vehicle: Optional[Dict[str, Any]] = None
    identification_status: Optional[str] = None
    fipe_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    erp_enabled: bool
    erp_status: Literal["AVAILABLE", "DISABLED", "NOT_CONFIGURED", "PRIVATE_NETWORK_UNAVAILABLE", "UNAVAILABLE"] = "NOT_CONFIGURED"
    availability_status: Literal["AVAILABLE", "UNAVAILABLE", "NOT_QUERIED"] = "NOT_QUERIED"
    parts_count: int = Field(ge=0)
    parts: List[ApplicableERPPartSchema]
    message: Optional[str] = None
    error: Optional[str] = None

    @model_validator(mode="after")
    def consistent_count(self):
        if self.parts_count != len(self.parts):
            raise ValueError("parts_count must equal the number of returned parts")
        return self

# ERP Mapping Create/Update Schema
class ERPProductMappingCreateSchema(BaseModel):
    erp_product_id: str
    part_id: Optional[int] = None
    manufacturer_code: Optional[str] = None
    ean: Optional[str] = None
    mapping_type: str = "MANUFACTURER_CODE"
    verified: bool = True
