import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.services.vehicle_normalizer import normalize_text, parse_version_specs

logger = logging.getLogger("application_matcher")

class ApplicationMatcher:
    """
    Intelligent & Conservative Parser/Matcher for Brazilian Auto Parts Application Text.
    Segments multi-vehicle strings ('--', ';', ',') and evaluates compatibility between
    a normalized vehicle (e.g. Jeep Renegade 1.8 Flex 2016 4x2 Aut.) and ERP application text.
    Classifies result into: EXACT, COMPATIBLE, CONDITIONAL, or REJECTED with full explainability.
    """

    @staticmethod
    def parse_year_ranges(text: str) -> List[Tuple[int, Optional[int]]]:
        """
        Parses Brazilian catalog year expressions:
        '2015/...', '15/...', '2015 A 2021', '2015 Á 2021', '2015-2021', '2015 2016 2017'
        Returns list of (start_year, end_year) ranges.
        """
        ranges = []
        raw_clean = re.sub(r'[^A-Z0-9\s\.\-/]', '', text.upper().strip())
        raw_clean = re.sub(r'\s+', ' ', raw_clean)

        # Normalize slashes with dots (e.g. 2015... -> 2015/...)
        norm_years_text = re.sub(r'\b(19[89][0-9]|20[0-2][0-9]|[89][0-9]|[0-2][0-9])\s*\.{2,}', r'\1/...', text.upper().strip())

        # 1. Open ended ranges: 2015/..., 15/..., 2015/...., 2015/
        open_matches = re.finditer(r'\b(19[89][0-9]|20[0-2][0-9]|[89][0-9]|[0-2][0-9])\s*/(?:\.{2,}|(?=\s|$))', norm_years_text)
        for m in open_matches:
            yr_str = m.group(1)
            start_yr = int(yr_str) if len(yr_str) == 4 else (1900 + int(yr_str) if int(yr_str) >= 80 else 2000 + int(yr_str))
            ranges.append((start_yr, None))

        clean_for_closed = re.sub(r'\b(19[89][0-9]|20[0-2][0-9]|[89][0-9]|[0-2][0-9])\s*/(?:\.{2,}|\.\.\.|\.\.|/|\b)', '', norm_years_text)

        # 2. Closed ranges: 2015 A 2021 or 2015 - 2021 or 2015/2021
        closed_matches = re.finditer(r'\b(19[89][0-9]|20[0-2][0-9])\s*(?:A|Á|-)\s*(19[89][0-9]|20[0-2][0-9])\b', clean_for_closed)
        for m in closed_matches:
            start_yr = int(m.group(1))
            end_yr = int(m.group(2))
            if start_yr <= end_yr:
                ranges.append((start_yr, end_yr))

        # 3. Discrete list of 4-digit years: 2015 2016 2017
        if not ranges:
            list_matches = re.findall(r'\b(19[89][0-9]|20[0-2][0-9])\b', raw_clean)
            if list_matches:
                years = [int(y) for y in list_matches]
                ranges.append((min(years), max(years)))

        return ranges

    @staticmethod
    def match_application(
        vehicle_info: Dict[str, Any],
        raw_application: Optional[str]
    ) -> Dict[str, Any]:
        """
        Evaluates vehicle compatibility against ERP product application text.
        vehicle_info requires:
          - make (e.g. 'JEEP')
          - model (e.g. 'RENEGADE')
          - model_year (e.g. 2016)
          - engine_displacement (e.g. '1.8', optional)
          - fuel (e.g. 'FLEX', optional)
          - transmission (e.g. 'Automático' or None)
          - drivetrain (e.g. '4X2' or None)
        """
        if not raw_application or not raw_application.strip():
            return {
                "compatibility": "REJECTED",
                "score": 0,
                "matched": [],
                "unknown": [],
                "conflicts": ["Application text is empty"]
            }

        target_model = normalize_text(vehicle_info.get("model", ""))
        target_make = normalize_text(vehicle_info.get("make", ""))
        target_year = vehicle_info.get("model_year") or vehicle_info.get("manufacture_year")
        target_disp = vehicle_info.get("engine_displacement")
        target_fuel = normalize_text(vehicle_info.get("fuel", "")) if vehicle_info.get("fuel") else None
        target_trans = vehicle_info.get("transmission") # 'Automático', 'Manual' or None
        target_drivetrain = vehicle_info.get("drivetrain") # '4X2', '4X4' or None

        # 1. Segment application text into vehicle blocks ('--', ';', ',')
        blocks = [b.strip() for b in re.split(r'--|;|,\s*(?=[A-Z]{3,})', raw_application.upper()) if b.strip()]

        best_block_match = None

        for block in blocks:
            clean_block = normalize_text(block)

            # Check if block mentions target model or make+model
            if target_model not in clean_block and "TODOS" not in clean_block and "TDS" not in clean_block:
                continue

            matched_rules = []
            conflicts = []
            unknowns = []

            # A. Model Match
            if target_model in clean_block or "TODOS" in clean_block:
                matched_rules.append(f"model={target_model}")

            # B. Year Range Match
            year_ranges = ApplicationMatcher.parse_year_ranges(clean_block)
            if year_ranges and target_year:
                year_matched = False
                for start_yr, end_yr in year_ranges:
                    if end_yr is None:
                        if target_year >= start_yr:
                            year_matched = True
                            break
                    else:
                        if start_yr <= target_year <= end_yr:
                            year_matched = True
                            break

                if year_matched:
                    matched_rules.append(f"year={target_year}")
                else:
                    conflicts.append(f"year expected {target_year} but application specifies {year_ranges}")

            # C. Engine Displacement Match
            # Check if block specifies engine like 1.8, 2.0, 2.4, 1.8L
            disp_matches = re.findall(r'\b([0-9]\.[0-9])L?\b', clean_block)
            if disp_matches and target_disp:
                if target_disp in disp_matches:
                    matched_rules.append(f"engine={target_disp}")
                else:
                    conflicts.append(f"engine expected {target_disp} but application specifies {disp_matches}")

            # D. Fuel Match
            # FLEX, DIESEL, GASOLINA, ALCOOL
            block_fuels = []
            if "FLEX" in clean_block: block_fuels.append("FLEX")
            if "DIESEL" in clean_block: block_fuels.append("DIESEL")
            if "GASOLINA" in clean_block: block_fuels.append("GASOLINA")
            if "ALCOOL" in clean_block: block_fuels.append("ALCOOL")

            if block_fuels and target_fuel:
                if target_fuel in block_fuels or ("FLEX" in block_fuels and target_fuel in ("FLEX", "GASOLINA", "ALCOOL")):
                    matched_rules.append(f"fuel={target_fuel}")
                else:
                    conflicts.append(f"fuel expected {target_fuel} but application specifies {block_fuels}")

            # E. Drivetrain Match (4X2/FWD vs 4X4/AWD)
            block_4x4 = bool(re.search(r'\b(4X4|AWD)\b', clean_block))
            block_4x2 = bool(re.search(r'\b(4X2|FWD)\b', clean_block))

            if block_4x4 and target_drivetrain == "4X2":
                conflicts.append("drivetrain expected 4X2 but application requires 4X4/AWD")
            elif block_4x2 and target_drivetrain == "4X4":
                conflicts.append("drivetrain expected 4X4 but application requires 4X2/FWD")
            elif (block_4x4 and target_drivetrain == "4X4") or (block_4x2 and target_drivetrain == "4X2"):
                matched_rules.append(f"drivetrain={target_drivetrain}")

            # F. Transmission Match (AUT/AUTOMATICO vs MEC/MANUAL)
            block_specs = parse_version_specs(clean_block)
            block_trans = block_specs.get("transmission")

            if block_trans:
                if target_trans:
                    if block_trans == target_trans:
                        matched_rules.append(f"transmission={target_trans}")
                    else:
                        conflicts.append(f"transmission expected {target_trans} but application requires {block_trans}")
                else:
                    unknowns.append(f"transmission required={block_trans}")

            # Evaluate Block Classification
            if conflicts:
                compat = "REJECTED"
                score = 0
            elif unknowns:
                compat = "CONDITIONAL"
                score = 75
            elif len(matched_rules) >= 3:
                compat = "EXACT"
                score = 95
            else:
                compat = "COMPATIBLE"
                score = 85

            block_res = {
                "compatibility": compat,
                "score": score,
                "matched": matched_rules,
                "unknown": unknowns,
                "conflicts": conflicts
            }

            if not best_block_match or score > best_block_match["score"]:
                best_block_match = block_res

        if best_block_match:
            return best_block_match

        return {
            "compatibility": "REJECTED",
            "score": 0,
            "matched": [],
            "unknown": [],
            "conflicts": [f"Vehicle model '{target_model}' not found in application string"]
        }
