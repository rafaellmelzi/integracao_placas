import urllib.request
import urllib.error
import email.utils
import json
import time
import random
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("tabelafipe_provider")

TABELAFIPE_BASE_URL = "https://api.tabelafipe.info/api/v1"
HTTP_HEADERS = {"User-Agent": "AutoParts-TabelaFipeProvider/1.0"}

class TabelaFipeProvider:
    """
    Provider encapsulating public access to TabelaFIPE.info API.
    Rate Limit: 60 requests per minute per IP (1 req/sec).
    Supports: Reference month, makes, models by year, family versions & prices, fipe code lookup.
    """
    def __init__(self, delay_sec: float = 1.0):
        self.base_url = TABELAFIPE_BASE_URL
        self.delay_sec = delay_sec
        self.http_429_count = 0

    def _parse_retry_after(self, header_val: Optional[str]) -> Optional[float]:
        if not header_val or not header_val.strip():
            return None
        val_str = header_val.strip()
        if val_str.isdigit():
            sec = float(val_str)
            return sec if sec >= 0 else None
        try:
            dt = email.utils.parsedate_to_datetime(val_str)
            if dt:
                now = datetime.now(timezone.utc)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = (dt - now).total_seconds()
                return delta if delta > 0 else 0.0
        except Exception:
            pass
        return None

    def fetch_json(self, endpoint: str, max_retries: int = 5) -> Optional[Any]:
        url = f"{self.base_url}{endpoint}" if not endpoint.startswith("http") else endpoint
        backoff_schedule = [2.0, 5.0, 10.0, 20.0, 40.0, 60.0]

        for attempt in range(max_retries):
            req = urllib.request.Request(url, headers=HTTP_HEADERS)
            try:
                time.sleep(self.delay_sec)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        raw_body = resp.read().decode("utf-8")
                        return json.loads(raw_body)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    self.http_429_count += 1
                    retry_hdr = e.headers.get("Retry-After")
                    parsed_sec = self._parse_retry_after(retry_hdr)
                    base_wait = parsed_sec if (parsed_sec and parsed_sec > 0) else backoff_schedule[min(attempt, len(backoff_schedule)-1)]
                    wait_time = min(base_wait + random.uniform(0.5, 1.5), 60.0)
                    logger.warning(f"HTTP 429 Rate Limit on TabelaFIPE.info for {endpoint}. Waiting {wait_time:.1f}s (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                elif e.code in (400, 404):
                    logger.info(f"HTTP {e.code} for {endpoint}: Resource not found or bad request.")
                    return None
                else:
                    logger.warning(f"HTTP {e.code} error for {endpoint}: {e}")
                    time.sleep(2.0 + attempt)
            except Exception as e:
                logger.warning(f"Transient error fetching {endpoint} (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(2.0 + attempt)

        logger.error(f"Exhausted retries fetching {endpoint} from TabelaFIPE.info.")
        return None

    def get_reference_period(self) -> Optional[Dict[str, Any]]:
        """GET /referencia - Returns current active FIPE reference month and code."""
        return self.fetch_json("/referencia")

    def get_makes(self, vehicle_type: str = "carros") -> Optional[List[Dict[str, Any]]]:
        """GET /:tipo/marcas - Returns list of brands with slug, name, models count."""
        resp = self.fetch_json(f"/{vehicle_type}/marcas")
        if resp and "brands" in resp:
            return resp["brands"]
        return None

    def get_models_by_make(self, make_slug: str, year: Optional[int] = None, vehicle_type: str = "carros") -> Optional[Dict[str, Any]]:
        """GET /:tipo/:marca/modelos?ano= - Returns families and model versions for make."""
        query = f"?ano={year}" if year else ""
        return self.fetch_json(f"/{vehicle_type}/{make_slug}/modelos{query}")

    def get_family_prices(self, make_slug: str, family_slug: str, vehicle_type: str = "carros") -> Optional[Dict[str, Any]]:
        """GET /:tipo/:marca/familia/:familia/precos - Returns all versions, years, prices and FIPE codes for family."""
        return self.fetch_json(f"/{vehicle_type}/{make_slug}/familia/{family_slug}/precos")

    def get_fipe_details(self, fipe_code: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """GET /fipe/:codigo?ano= - Returns specification details and current price by FIPE code."""
        query = f"?ano={year}" if year else ""
        return self.fetch_json(f"/fipe/{fipe_code}{query}")
