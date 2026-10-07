import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.services.vehicle_normalizer import normalize_text, remove_accents

logger = logging.getLogger("application_matcher")

def clean_application_text(text: str) -> str:
    """Normalizes accents and whitespace while preserving slashes and hyphens needed for specs."""
    if not text:
        return ""
    res = remove_accents(text.strip().upper())
    res = re.sub(r'[^A-Z0-9\s\.\-/]', '', res)
    res = re.sub(r'\s+', ' ', res)
    return res

class ApplicationMatcher:
    """
    Intelligent & Conservative Parser/Matcher for Brazilian Auto Parts Application Text.
    Segments multi-vehicle strings and evaluates compatibility between a normalized vehicle
    (e.g. Jeep Renegade 1.8 Flex 2016 4x2 Aut.) and ERP application text (ITE_APLICA).
    """

    @staticmethod
    def parse_year_ranges(text: str) -> List[Tuple[int, Optional[int]]]:
        """
        Parses Brazilian catalog year expressions:
        '2015/...', '15/...', '2015 A 2021', '2015 Á 2021', '2015-2021', '2015 2016 2017', 'ANO: 15/...'
        Returns list of (start_year, end_year) ranges.
        """
        ranges = []
        upper_text = text.upper().strip()

        # Remove prefixes like ANO: or ANOS:
        cleaned_prefix = re.sub(r'\bANOS?:\s*', '', upper_text)

        raw_clean = re.sub(r'[^A-Z0-9\s\.\-/]', '', cleaned_prefix)
        raw_clean = re.sub(r'\s+', ' ', raw_clean)

        # Normalize slashes with dots (e.g. 2015... or 15... -> 2015/...)
        norm_years_text = re.sub(r'\b(19[89][0-9]|20[0-2][0-9]|[89][0-9]|[0-2][0-9])\s*\.{2,}', r'\1/...', cleaned_prefix)

        # 1. Open ended ranges: 2015/..., 15/..., 2015/...., 2015/
        open_matches = re.finditer(r'\b(19[89][0-9]|20[0-2][0-9]|[89][0-9]|[0-2][0-9])\s*/(?:\.{2,}|(?=\s|$|[\.\-,\(\)]))', norm_years_text)
        for m in open_matches:
            yr_str = m.group(1)
            start_yr = int(yr_str) if len(yr_str) == 4 else (1900 + int(yr_str) if int(yr_str) >= 80 else 2000 + int(yr_str))
            ranges.append((start_yr, None))

        clean_for_closed = re.sub(r'\b(19[89][0-9]|20[0-2][0-9]|[89][0-9]|[0-2][0-9])\s*/(?:\.{2,}|\.\.\.|\.\.|/|\b)', '', norm_years_text)

        # 2. Closed ranges: 2015 A 2021 or 2015 - 2021 or 2015/2021
        closed_matches = re.finditer(r'\b(19[89][0-9]|20[0-2][0-9])\s*(?:A|Á|-|/)\s*(19[89][0-9]|20[0-2][0-9])\b', clean_for_closed)
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
    def segment_application_text(raw_application: str) -> List[str]:
        """
        Splits multi-vehicle application text into distinct vehicle segments.
        Delimiters: newlines, '--', ';', ' - ', or commas when followed by brand/model.
        Preserves expressions like '1.8/2.0', '2015/2021', '15/...'
        """
        if not raw_application:
            return []

        text = raw_application.strip()
        text = re.sub(r'[\r\n]+', ' -- ', text)
        text = re.sub(r'\s+--+\s+', ' -- ', text)
        text = re.sub(r'\s*;\s*', ' -- ', text)

        raw_parts = [p.strip() for p in text.split(' -- ') if p.strip()]

        segments = []
        for part in raw_parts:
            sub_parts = re.split(r'\s+-\s+(?![0-9]|\.{2,}|ANO|ANOS|GNV|FLEX|DIESEL|AUT|MEC|4X2|4X4)', part, flags=re.IGNORECASE)
            for sp in sub_parts:
                sp_clean = sp.strip()
                if sp_clean:
                    segments.append(sp_clean)

        return segments

    @staticmethod
    def match_application(
        vehicle_info: Dict[str, Any],
        raw_application: Optional[str]
    ) -> Dict[str, Any]:
        """
        Evaluates vehicle compatibility against ERP product application text.
        """
        if not raw_application or not raw_application.strip():
            return {
                "compatibility": "REJECTED",
                "score": 0,
                "matched": [],
                "unknown": [],
                "conflicts": ["Texto de aplicação vazio"]
            }

        target_model = normalize_text(vehicle_info.get("model", ""))
        target_make = normalize_text(vehicle_info.get("make", ""))
        target_year = vehicle_info.get("model_year") or vehicle_info.get("manufacture_year")
        target_disp = vehicle_info.get("engine_displacement")

        raw_fuel = vehicle_info.get("fuel")
        target_fuel = normalize_text(raw_fuel) if raw_fuel else None

        target_trans = vehicle_info.get("transmission")
        target_drivetrain = vehicle_info.get("drivetrain")

        segments = ApplicationMatcher.segment_application_text(raw_application)

        all_norm_text = clean_application_text(raw_application)
        if target_model not in all_norm_text and "TODOS" not in all_norm_text and "TDS" not in all_norm_text:
            return {
                "compatibility": "REJECTED",
                "score": 0,
                "matched": [],
                "unknown": [],
                "conflicts": [f"Modelo '{target_model}' não encontrado no texto de aplicação"]
            }

        target_segments = []
        for seg in segments:
            norm_seg = clean_application_text(seg)
            if target_model in norm_seg or "TODOS" in norm_seg or "TDS" in norm_seg:
                target_segments.append(seg)

        if not target_segments:
            target_segments = [raw_application]

        evaluated_matches = []

        for seg in target_segments:
            clean_seg = clean_application_text(seg)
            matched_rules = []
            conflicts = []
            unknowns = []

            # A. Model Match
            if target_model in clean_seg or "TODOS" in clean_seg or "TDS" in clean_seg:
                matched_rules.append(f"model={target_model}")

            # B. Year Range Match
            year_ranges = ApplicationMatcher.parse_year_ranges(seg)
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
                    conflicts.append(f"ano: veiculo={target_year} aplicacao={year_ranges}")

            # C. Engine Displacement Match
            disp_combos = re.findall(r'\b([0-9]\.[0-9](?:\s*/\s*[0-9]\.[0-9])*)\s*L?\b', clean_seg)
            extracted_disps = []
            for dc in disp_combos:
                for d in dc.split('/'):
                    d_clean = d.strip()
                    if d_clean and d_clean not in extracted_disps:
                        extracted_disps.append(d_clean)

            if extracted_disps and target_disp:
                if target_disp in extracted_disps:
                    matched_rules.append(f"engine={target_disp}")
                else:
                    conflicts.append(f"engine: vehicle={target_disp} application={extracted_disps}")

            # D. Fuel Match
            seg_fuels = []
            if "FLEX" in clean_seg: seg_fuels.append("FLEX")
            if "DIESEL" in clean_seg: seg_fuels.append("DIESEL")
            if "GNV" in clean_seg: seg_fuels.append("GNV")
            if "GASOLINA" in clean_seg: seg_fuels.append("GASOLINA")
            if "ALCOOL" in clean_seg: seg_fuels.append("ALCOOL")

            if seg_fuels and target_fuel:
                is_fuel_compat = False
                if target_fuel in seg_fuels:
                    is_fuel_compat = True
                elif target_fuel == "FLEX" and any(f in ("FLEX", "GASOLINA", "ALCOOL") for f in seg_fuels) and not any(f in ("DIESEL", "GNV") for f in seg_fuels):
                    is_fuel_compat = True

                if is_fuel_compat:
                    matched_rules.append(f"fuel={target_fuel}")
                else:
                    conflicts.append(f"fuel: vehicle={target_fuel} application={seg_fuels}")

            # E. Transmission Match
            req_trans = None
            if re.search(r'\b(AUT|AUTOMATICO|AUTOMATICA)\b', clean_seg):
                req_trans = "Automático"
            elif re.search(r'\b(MEC|MANUAL|MECANICO|MECANICA)\b', clean_seg):
                req_trans = "Manual"

            if req_trans:
                if target_trans:
                    if target_trans == req_trans or (target_trans == "Automático" and req_trans == "Automático") or (target_trans == "Manual" and req_trans == "Manual"):
                        matched_rules.append(f"transmission={target_trans}")
                    else:
                        conflicts.append(f"transmission: vehicle={target_trans} application={req_trans}")
                else:
                    unknowns.append(f"transmission={req_trans.upper()}")

            # F. Drivetrain Match
            req_dt = None
            if re.search(r'\b(4X4|AWD)\b', clean_seg):
                req_dt = "4X4"
            elif re.search(r'\b(4X2|FWD)\b', clean_seg):
                req_dt = "4X2"

            if req_dt:
                if target_drivetrain:
                    if target_drivetrain == req_dt:
                        matched_rules.append(f"drivetrain={target_drivetrain}")
                    else:
                        conflicts.append(f"drivetrain: vehicle={target_drivetrain} application={req_dt}")

            # Calculate Segment Status & Score
            if conflicts:
                seg_status = "INCOMPATIBLE"
                seg_score = 0
            elif unknowns:
                seg_status = "CONDITIONAL"
                seg_score = 70 + (len(matched_rules) * 5)
            elif len(matched_rules) >= 3:
                seg_status = "EXACT"
                seg_score = 95
            else:
                seg_status = "COMPATIBLE"
                seg_score = 80 + (len(matched_rules) * 5)

            evaluated_matches.append({
                "compatibility": seg_status,
                "score": seg_score,
                "matched": matched_rules,
                "unknown": unknowns,
                "conflicts": conflicts
            })

        compatible_matches = [m for m in evaluated_matches if m["compatibility"] in ("EXACT", "COMPATIBLE")]
        if compatible_matches:
            best = max(compatible_matches, key=lambda x: x["score"])
            return {
                "compatibility": "COMPATIBLE",
                "score": best["score"],
                "matched": best["matched"],
                "unknown": best["unknown"],
                "conflicts": []
            }

        conditional_matches = [m for m in evaluated_matches if m["compatibility"] == "CONDITIONAL"]
        if conditional_matches:
            best = max(conditional_matches, key=lambda x: x["score"])
            return {
                "compatibility": "CONDITIONAL",
                "score": best["score"],
                "matched": best["matched"],
                "unknown": best["unknown"],
                "conflicts": []
            }

        all_conflicts = []
        for m in evaluated_matches:
            all_conflicts.extend(m["conflicts"])

        return {
            "compatibility": "INCOMPATIBLE",
            "score": 0,
            "matched": evaluated_matches[0]["matched"] if evaluated_matches else [],
            "unknown": [],
            "conflicts": list(set(all_conflicts))
        }
