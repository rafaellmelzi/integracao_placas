import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, Enum, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class ConfidenceLevel(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    POSSIBLE = "POSSIBLE"
    UNVERIFIED = "UNVERIFIED"

class CrossReferenceType(str, enum.Enum):
    OEM = "OEM"
    AFTERMARKET = "AFTERMARKET"
    EQUIVALENT = "EQUIVALENT"
    REPLACEMENT = "REPLACEMENT"

class ERPProductMappingType(str, enum.Enum):
    EAN = "EAN"
    MANUFACTURER_CODE = "MANUFACTURER_CODE"
    OEM_CODE = "OEM_CODE"
    CROSS_REFERENCE = "CROSS_REFERENCE"
    MANUAL = "MANUAL"
    SUGGESTED_AI = "SUGGESTED_AI"

# Vehicles Schema Models
class VehicleMake(Base):
    __tablename__ = "vehicle_make"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    models: Mapped[List["VehicleModel"]] = relationship(back_populates="make", cascade="all, delete-orphan")

class VehicleModel(Base):
    __tablename__ = "vehicle_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    make_id: Mapped[int] = mapped_column(ForeignKey("vehicle_make.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    make: Mapped["VehicleMake"] = relationship(back_populates="models")
    generations: Mapped[List["VehicleGeneration"]] = relationship(back_populates="model", cascade="all, delete-orphan")
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="model")

    __table_args__ = (
        UniqueConstraint("make_id", "normalized_name", name="uq_make_model_normalized"),
    )

class VehicleGeneration(Base):
    __tablename__ = "vehicle_generation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("vehicle_model.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    model: Mapped["VehicleModel"] = relationship(back_populates="generations")

class VehicleVersion(Base):
    __tablename__ = "vehicle_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

class VehicleEngine(Base):
    __tablename__ = "vehicle_engine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 1.0 TSI, 1.4 TSI
    displacement: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    valves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    power_hp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

class VehicleTransmission(Base):
    __tablename__ = "vehicle_transmission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False) # Manual, Automatic, CVT, DCT
    gears: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

class VehicleFuel(Base):
    __tablename__ = "vehicle_fuel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

class Vehicle(Base):
    __tablename__ = "vehicle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    make_id: Mapped[int] = mapped_column(ForeignKey("vehicle_make.id"), nullable=False, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("vehicle_model.id"), nullable=False, index=True)
    version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vehicle_version.id"), nullable=True, index=True)
    engine_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vehicle_engine.id"), nullable=True, index=True)
    transmission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vehicle_transmission.id"), nullable=True)
    fuel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vehicle_fuel.id"), nullable=True)

    year_manufacture: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year_model: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fipe_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    fipe_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    make: Mapped["VehicleMake"] = relationship()
    model: Mapped["VehicleModel"] = relationship(back_populates="vehicles")
    version: Mapped[Optional["VehicleVersion"]] = relationship()
    engine: Mapped[Optional["VehicleEngine"]] = relationship()
    transmission: Mapped[Optional["VehicleTransmission"]] = relationship()
    fuel: Mapped[Optional["VehicleFuel"]] = relationship()

class VehiclePlateCache(Base):
    __tablename__ = "vehicle_plate_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plate: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    vehicle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vehicle.id"), nullable=True, index=True)

    is_ambiguous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    possible_vehicle_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_vehicle_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    consulted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    data_quality: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    raw_response_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_response_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    vehicle: Mapped[Optional["Vehicle"]] = relationship()

# Parts Schema Models
class PartManufacturer(Base):
    __tablename__ = "part_manufacturer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

class PartCategory(Base):
    __tablename__ = "part_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    synonyms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class Part(Base):
    __tablename__ = "part"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("part_manufacturer.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("part_category.id"), nullable=False, index=True)

    manufacturer_part_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ean: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    oem_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Comma-separated or JSON list
    equivalent_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_specs: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON or specs string
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="CATALOGO_OFICIAL")

    manufacturer: Mapped["PartManufacturer"] = relationship()
    category: Mapped["PartCategory"] = relationship()
    applications: Mapped[List["PartApplication"]] = relationship(back_populates="part", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("manufacturer_id", "manufacturer_part_number", name="uq_mfg_part_number"),
    )

class PartApplication(Base):
    __tablename__ = "part_application"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicle.id", ondelete="CASCADE"), nullable=False, index=True)

    year_from: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    engine_spec: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Dianteiro, Traseiro
    axis: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Dianteiro, Traseiro
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source: Mapped[str] = mapped_column(String(100), nullable=False, default="CATALOGO_FABRICANTE")
    source_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    confidence: Mapped[ConfidenceLevel] = mapped_column(Enum(ConfidenceLevel), default=ConfidenceLevel.CONFIRMED, nullable=False)

    part: Mapped["Part"] = relationship(back_populates="applications")
    vehicle: Mapped["Vehicle"] = relationship()

class PartCrossReference(Base):
    __tablename__ = "part_cross_reference"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_part_id: Mapped[int] = mapped_column(ForeignKey("part.id", ondelete="CASCADE"), nullable=False, index=True)

    reference_type: Mapped[CrossReferenceType] = mapped_column(Enum(CrossReferenceType), default=CrossReferenceType.EQUIVALENT, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="MANUFACTURER")
    confidence: Mapped[ConfidenceLevel] = mapped_column(Enum(ConfidenceLevel), default=ConfidenceLevel.HIGH_CONFIDENCE, nullable=False)

    part: Mapped["Part"] = relationship(foreign_keys=[part_id])
    reference_part: Mapped["Part"] = relationship(foreign_keys=[reference_part_id])

class ERPProductMapping(Base):
    __tablename__ = "erp_product_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    erp_product_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    part_id: Mapped[Optional[int]] = mapped_column(ForeignKey("part.id"), nullable=True, index=True)

    manufacturer_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    ean: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    mapping_type: Mapped[ERPProductMappingType] = mapped_column(Enum(ERPProductMappingType), default=ERPProductMappingType.MANUFACTURER_CODE, nullable=False)
    confidence: Mapped[ConfidenceLevel] = mapped_column(Enum(ConfidenceLevel), default=ConfidenceLevel.CONFIRMED, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    part: Mapped[Optional["Part"]] = relationship()

class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class ApiRequestLog(Base):
    __tablename__ = "api_request_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    query_params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_success: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class FipeCacheTracking(Base):
    __tablename__ = "fipe_cache_tracking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True) # e.g. MAKES, MODELS:2, YEARS:101, VERSIONS:101:2023
    fipe_reference: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g. outubro/2026 or 338
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="VALID", nullable=False)
