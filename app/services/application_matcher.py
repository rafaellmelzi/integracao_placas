import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.services.vehicle_contract import Compatibility, MatchingVehicle
from app.services.vehicle_normalizer import MAKE_ALIASES, normalize_text, remove_accents


def clean_application_text(text: str) -> str:
    text = remove_accents(text.strip().upper())
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9\s.\-/]", " ", text))


def result(status, matched=None, unknown=None, conflicts=None, reason=None):
    matched, unknown, conflicts = matched or [], unknown or [], conflicts or []
    score = 0 if status == Compatibility.INCOMPATIBLE else min(
        90 if status == Compatibility.CONDITIONAL else 95,
        (65 if status == Compatibility.CONDITIONAL else 80) + 5 * len(matched),
    )
    return dict(compatibility=status.value, score=score, matched=matched,
                unknown=unknown, conflicts=conflicts, reason=reason)


class ApplicationMatcher:
    """Evaluate independent catalog alternatives without combining their attributes.

    COMPATIBLE requires explicit model and evidence without unresolved restrictions.
    CONDITIONAL requires confirmation of a restricted attribute or association.
    INCOMPATIBLE covers conflicts, invalid applications and missing model matches.
    A model name alone is insufficient evidence. Reasons distinguish invalid input
    from an actual attribute conflict. Missing catalog specs imply no restriction.
    """
    YEAR = r"(?:19\d{2}|20\d{2})"
    SHORT_YEAR = r"(?:19\d{2}|20\d{2}|\d{2})"
    ATTRIBUTE = (r"(?:ANOS?|GNV|FLEX|DIESEL|GASOLINA|ALCOOL|ETANOL|AUT\w*|"
                 r"MEC\w*|MANUAL|CVT|DCT|FWD|AWD|4X2|4X4|TODOS|TDS|"
                 r"MOTOR|CAMBIO|TRANSMISSAO|TURBO|TSI|TFSI|16V|8V|"
                 r"SPORT|LONGITUDE|LIMITED|TRAILHAWK)\b")

    @staticmethod
    def parse_year_ranges(text: str) -> List[Tuple[int, Optional[int]]]:
        text = remove_accents(text.upper())
        text = re.sub(r"\bANOS?:?\s*", "", text)
        text = re.sub(rf"\b({ApplicationMatcher.SHORT_YEAR})\s*\.(?:\.)+", r"\1/...", text)
        ranges = []

        def year(token):
            y = int(token)
            return y if len(token) == 4 else (1900 + y if y >= 80 else 2000 + y)

        def opened(match):
            ranges.append((year(match[1]), None))
            return " "

        text = re.sub(rf"\b({ApplicationMatcher.SHORT_YEAR})\s*/(?:\.+|(?=\s|$|[,)\-]))", opened, text)

        def closed(match):
            start, end = year(match[1]), year(match[2])
            if start > end:
                raise ValueError("Intervalo de anos invertido")
            ranges.append((start, end))
            return " "

        text = re.sub(rf"\b({ApplicationMatcher.SHORT_YEAR})\s*(?:A|ATE|-|/)\s*({ApplicationMatcher.SHORT_YEAR})\b", closed, text)
        # A discrete list is not a continuous interval.
        ranges.extend((int(y), int(y)) for y in re.findall(rf"\b({ApplicationMatcher.YEAR})\b", text))
        return ranges

    @staticmethod
    def segment_application_text(raw_application: str) -> List[str]:
        if not isinstance(raw_application, str):
            return []
        text = remove_accents(raw_application.upper())
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
        # A slash after an attribute and before a name separates vehicles;
        # model groups (RENEGADE/COMPASS) and engine lists (1.8/2.0) remain intact.
        blocks = re.split(r"[\r\n;]+|\s*-{2,}\s*|(?<=\d)/(?=[A-Z])", text)
        segments = []
        for block in blocks:
            # Split only when comma/spaced hyphen introduces a vehicle name.
            parts = re.split(
                rf"(?:,\s*|\s+-\s+)(?=[A-Z])(?!{ApplicationMatcher.ATTRIBUTE})", block)
            brand = ""
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if part in MAKE_ALIASES:
                    # Keep the brand in catalog notation such as JEEP - RENEGADE.
                    brand = part
                    continue
                segments.append((brand + " " + part).strip())
                brand = ""
        return segments

    @staticmethod
    def match_application(vehicle_info: Union[Dict[str, Any], MatchingVehicle],
                          raw_application: Optional[str]) -> Dict[str, Any]:
        if raw_application is None or (isinstance(raw_application, str) and not raw_application.strip()):
            return result(Compatibility.INCOMPATIBLE, conflicts=["Texto de aplicação vazio"], reason="EMPTY_APPLICATION")
        if not isinstance(raw_application, str) or not re.search(r"[A-Za-z]", raw_application):
            return result(Compatibility.INCOMPATIBLE, conflicts=["Texto de aplicação inválido"], reason="INVALID_APPLICATION")
        v = vehicle_info if isinstance(vehicle_info, MatchingVehicle) else MatchingVehicle.from_mapping(vehicle_info)
        if not v.model:
            return result(Compatibility.INCOMPATIBLE, conflicts=["Modelo do veículo desconhecido"], reason="MISSING_VEHICLE_MODEL")
        model_pattern = rf"(?<![A-Z0-9]){re.escape(v.model)}(?![A-Z0-9])"
        evaluated = []
        for segment in ApplicationMatcher.segment_application_text(raw_application):
            clean = clean_application_text(segment)
            # TODOS means all variants of a named model, not all vehicles.
            if not re.search(model_pattern, clean):
                continue
            matched, conflicts, unknown = [f"model={v.model}"], [], []
            brands = {normalize_text(canonical) for alias, canonical in MAKE_ALIASES.items()
                      if re.search(rf"\b{re.escape(alias)}\b", clean)}
            if brands and v.make:
                if v.make in brands:
                    matched.append(f"make={v.make}")
                else:
                    conflicts.append(f"make: vehicle={v.make} application={sorted(brands)}")
            elif brands:
                unknown.append("make=" + "/".join(sorted(brands)))

            versions = re.findall(r"\b(SPORT|LONGITUDE|LIMITED|TRAILHAWK)\b", clean)
            if versions and not re.search(r"\b(TODOS|TDS)\b", clean):
                if not v.version:
                    unknown.append("version=" + "/".join(sorted(set(versions))))
                elif any(re.search(rf"\b{version}\b", v.version) for version in versions):
                    matched.append(f"version={v.version}")
                else:
                    conflicts.append(f"version: vehicle={v.version} application={versions}")

            # Unlabelled catalog years refer to model year. Do not substitute
            # manufacture year for an unknown model year. Explicit manufacture
            # restrictions are evaluated independently, including mixed clauses.
            labels = list(re.finditer(r"\b(?:ANO\s*(?:DE\s*)?)?(MODELO|FABRICACAO)\s*:?[\s]*(?=\d)", clean))
            year_clauses = [("model_year", clean[:labels[0].start()] if labels else clean)]
            for index, label in enumerate(labels):
                end = labels[index + 1].start() if index + 1 < len(labels) else len(clean)
                year_clauses.append(("manufacture_year" if label[1] == "FABRICACAO" else "model_year", clean[label.end():end]))
            invalid_years = False
            for field, clause in year_clauses:
                try:
                    years = ApplicationMatcher.parse_year_ranges(clause)
                except ValueError as exc:
                    evaluated.append(result(Compatibility.INCOMPATIBLE, conflicts=[str(exc)], reason="INVALID_APPLICATION"))
                    invalid_years = True
                    break
                target_year = getattr(v, field)
                if years:
                    if target_year is None:
                        unknown.append(f"{field}={years}")
                    elif any(start <= target_year and (end is None or target_year <= end) for start, end in years):
                        matched.append(f"{'year' if field == 'model_year' else field}={target_year}")
                    else:
                        conflicts.append(f"ano ({field}): veiculo={target_year} aplicacao={years}")
            if invalid_years:
                continue

            engines = re.findall(r"\b([0-9]\.[0-9]|V6|V8|W12|V10)(?:L)?\b", clean)
            if engines:
                if not v.engine_displacement:
                    unknown.append(f"engine={engines}")
                elif v.engine_displacement in engines:
                    matched.append(f"engine={v.engine_displacement}")
                else:
                    conflicts.append(f"engine: vehicle={v.engine_displacement} application={engines}")

            fuels = re.findall(r"\b(FLEX|DIESEL|GNV|GASOLINA|ALCOOL|ETANOL|ELETRICO|HIBRIDO)\b", clean)
            fuels = ["ALCOOL" if f == "ETANOL" else f for f in fuels]
            if fuels:
                if not v.fuel:
                    unknown.append(f"fuel={fuels}")
                elif v.fuel in fuels:
                    matched.append(f"fuel={v.fuel}")
                else:
                    # Sharing an energy source does not establish interchangeability.
                    conflicts.append(f"fuel: vehicle={v.fuel} application={fuels}")

            transmissions = set()
            if re.search(r"\b(AUT|AUTOMATICO|AUTOMATICA)\b", clean):
                transmissions.add("Automático")
            if re.search(r"\b(MEC|MANUAL|MECANICO|MECANICA)\b", clean):
                transmissions.add("Manual")
            for name in ("CVT", "DCT"):
                if re.search(rf"\b{name}\b", clean):
                    transmissions.add(name)
            if transmissions:
                if not v.transmission:
                    unknown.append("transmission=" + "/".join(t.upper() for t in sorted(transmissions)))
                elif v.transmission in transmissions:
                    matched.append(f"transmission={v.transmission}")
                else:
                    conflicts.append(f"transmission: vehicle={v.transmission} application={sorted(transmissions)}")

            drivetrains = set()
            if re.search(r"\b(4X4|AWD)\b", clean):
                drivetrains.add("4X4")
            if re.search(r"\b(4X2|FWD)\b", clean):
                drivetrains.add("4X2")
            if drivetrains:
                if not v.drivetrain:
                    unknown.append("drivetrain=" + "/".join(sorted(drivetrains)))
                elif v.drivetrain in drivetrains:
                    matched.append(f"drivetrain={v.drivetrain}")
                else:
                    conflicts.append(f"drivetrain: vehicle={v.drivetrain} application={sorted(drivetrains)}")

            valves = {int(n) for n in re.findall(r"\b(8|12|16|20|24)V\b", clean)}
            if valves:
                if not v.valves:
                    unknown.append(f"valves={sorted(valves)}")
                elif v.valves in valves:
                    matched.append(f"valves={v.valves}")
                else:
                    conflicts.append(f"valves: vehicle={v.valves} application={sorted(valves)}")

            required_turbo = True if re.search(r"\b(TURBO|TSI|TFSI|TB)\b", clean) else False if "ASPIRADO" in clean else None
            if required_turbo is not None:
                if v.turbo is None:
                    unknown.append(f"turbo={required_turbo}")
                elif v.turbo == required_turbo:
                    matched.append(f"turbo={v.turbo}")
                else:
                    conflicts.append(f"turbo: vehicle={v.turbo} application={required_turbo}")

            # Inline lists with no delimiter need confirmation of associations.
            inline_models = re.search(r"\b\d(?:\.\d)?\b\s+([A-Z][A-Z0-9-]+)\s+\d\.\d\b", clean)
            if inline_models and not re.fullmatch(ApplicationMatcher.ATTRIBUTE, inline_models[1]):
                unknown.append("application=ambiguous_vehicle_attributes")
            engine_groups = list(re.finditer(r"\b[0-9]\.[0-9](?:L)?(?:\s*/\s*[0-9]\.[0-9](?:L)?)*\b", clean))
            if len(engine_groups) > 1 and any(
                    re.search(rf"\b{ApplicationMatcher.YEAR}\b", clean[left.end():right.start()])
                    for left, right in zip(engine_groups, engine_groups[1:])):
                unknown.append("application=ambiguous_engine_year_association")
            if re.search(r"\b(EXCETO|EXCLUI|NAO SE APLICA|NAO APLICA|NAO SERVE)\b", clean):
                # Never treat an excluded attribute as an allowed alternative.
                conflicts.append("application: exclusion syntax requires catalog review")
            if not any(m.startswith(("year=", "manufacture_year=", "engine=", "fuel=", "transmission=", "drivetrain=", "valves=")) for m in matched):
                unknown.append("application=insufficient_applicability_evidence")
            status = (Compatibility.INCOMPATIBLE if conflicts else
                      Compatibility.CONDITIONAL if unknown else Compatibility.COMPATIBLE)
            evaluated.append(result(status, matched, unknown, conflicts,
                                    "ATTRIBUTE_CONFLICT" if conflicts else "CONFIRMATION_REQUIRED" if unknown else "MATCHED"))

        if not evaluated:
            return result(Compatibility.INCOMPATIBLE, conflicts=[f"Modelo '{v.model}' não encontrado no texto de aplicação"], reason="MODEL_NOT_FOUND")
        for status in (Compatibility.COMPATIBLE, Compatibility.CONDITIONAL):
            matches = [r for r in evaluated if r["compatibility"] == status.value]
            if matches:
                return max(matches, key=lambda r: r["score"])
        return result(Compatibility.INCOMPATIBLE,
                      conflicts=sorted({c for r in evaluated for c in r["conflicts"]}),
                      matched=evaluated[0]["matched"], reason=evaluated[0]["reason"])
