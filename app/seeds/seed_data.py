import logging
from app.db.database import SessionLocal, init_db
from app.db.models import (
    VehicleMake, VehicleModel, VehicleVersion, VehicleEngine,
    VehicleFuel, VehicleTransmission, Vehicle, VehiclePlateCache,
    PartManufacturer, PartCategory, Part, PartApplication,
    PartCrossReference, ERPProductMapping, ERPProductMappingType,
    ConfidenceLevel, CrossReferenceType
)

logger = logging.getLogger(__name__)

def seed_database():
    init_db()
    db = SessionLocal()

    try:
        # Check if seed already performed
        if db.query(PartManufacturer).count() > 0:
            print("Database already seeded.")
            return

        print("Seeding database with sample automotive data...")

        # 1. Manufacturers & Categories
        fremax = PartManufacturer(name="Fremax", code="FREMAX")
        bosch = PartManufacturer(name="Bosch", code="BOSCH")
        cobreq = PartManufacturer(name="Cobreq", code="COBREQ")
        hipper = PartManufacturer(name="Hipper Freios", code="HIPPER")
        db.add_all([fremax, bosch, cobreq, hipper])
        db.flush()

        cat_brake_disc = PartCategory(code="BRAKE_DISC", name="Disco de Freio", synonyms="DISCO,DISCO FREIO,DISCOS")
        cat_brake_pad = PartCategory(code="BRAKE_PAD", name="Pastilha de Freio", synonyms="PASTILHA,PASTILHAS")
        cat_oil_filter = PartCategory(code="OIL_FILTER", name="Filtro de Óleo", synonyms="FILTRO OLEO,FILTRO DE OLEO")
        db.add_all([cat_brake_disc, cat_brake_pad, cat_oil_filter])
        db.flush()

        # 2. Vehicles
        vw = VehicleMake(name="Volkswagen", normalized_name="VOLKSWAGEN")
        gm = VehicleMake(name="Chevrolet", normalized_name="CHEVROLET")
        db.add_all([vw, gm])
        db.flush()

        tcross = VehicleModel(make_id=vw.id, name="T-Cross", normalized_name="T-CROSS")
        gol = VehicleModel(make_id=vw.id, name="Gol", normalized_name="GOL")
        onix = VehicleModel(make_id=gm.id, name="Onix", normalized_name="ONIX")
        db.add_all([tcross, gol, onix])
        db.flush()

        v_comfortline = VehicleVersion(name="Comfortline 200 TSI", normalized_name="COMFORTLINE 200 TSI")
        v_lt = VehicleVersion(name="LT Turbo", normalized_name="LT TURBO")
        db.add_all([v_comfortline, v_lt])
        db.flush()

        eng_10_tsi = VehicleEngine(description="1.0 TSI", displacement="1.0", power_hp=128)
        eng_10_turbo = VehicleEngine(description="1.0 Turbo", displacement="1.0", power_hp=116)
        db.add_all([eng_10_tsi, eng_10_turbo])
        db.flush()

        fuel_flex = VehicleFuel(name="Flex")
        trans_auto6 = VehicleTransmission(type="Automático 6v")
        db.add_all([fuel_flex, trans_auto6])
        db.flush()

        # Specific Vehicle 1: VW T-Cross
        v1 = Vehicle(
            make_id=vw.id,
            model_id=tcross.id,
            version_id=v_comfortline.id,
            engine_id=eng_10_tsi.id,
            transmission_id=trans_auto6.id,
            fuel_id=fuel_flex.id,
            year_manufacture=2022,
            year_model=2023,
            fipe_code="005512-3"
        )
        db.add(v1)
        db.flush()

        # 3. Parts
        part_fremax_bd = Part(
            manufacturer_id=fremax.id,
            category_id=cat_brake_disc.id,
            manufacturer_part_number="BD1234",
            ean="7891234567890",
            description="Disco de Freio Dianteiro Ventilado"
        )
        part_hipper_hf = Part(
            manufacturer_id=hipper.id,
            category_id=cat_brake_disc.id,
            manufacturer_part_number="HF1234",
            ean="7891234567891",
            description="Disco de Freio Dianteiro Ventilado HF"
        )
        part_cobreq_pad = Part(
            manufacturer_id=cobreq.id,
            category_id=cat_brake_pad.id,
            manufacturer_part_number="N-1234",
            ean="7891234567892",
            description="Jogo de Pastilhas de Freio Dianteiras"
        )
        db.add_all([part_fremax_bd, part_hipper_hf, part_cobreq_pad])
        db.flush()

        # 4. Applications
        app1 = PartApplication(
            part_id=part_fremax_bd.id,
            vehicle_id=v1.id,
            year_from=2019,
            year_to=2024,
            position="Dianteiro",
            source="CATALOG_FREMAX_OFFICIAL",
            confidence=ConfidenceLevel.CONFIRMED
        )
        app2 = PartApplication(
            part_id=part_cobreq_pad.id,
            vehicle_id=v1.id,
            year_from=2019,
            year_to=2024,
            position="Dianteiro",
            source="CATALOG_COBREQ_OFFICIAL",
            confidence=ConfidenceLevel.CONFIRMED
        )
        db.add_all([app1, app2])
        db.flush()

        # 5. Cross Reference
        cross1 = PartCrossReference(
            part_id=part_fremax_bd.id,
            reference_part_id=part_hipper_hf.id,
            reference_type=CrossReferenceType.EQUIVALENT,
            confidence=ConfidenceLevel.HIGH_CONFIDENCE
        )
        db.add(cross1)

        # 6. ERP Autcom Mapping
        erp_map1 = ERPProductMapping(
            erp_product_id="AUTCOM-PRD-9988",
            part_id=part_fremax_bd.id,
            manufacturer_code="BD1234",
            ean="7891234567890",
            mapping_type=ERPProductMappingType.EAN,
            confidence=ConfidenceLevel.CONFIRMED,
            verified=True
        )
        db.add(erp_map1)

        db.commit()
        print("Database seeded successfully with sample vehicles, parts, applications, cross-references, and Autcom ERP mappings!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
