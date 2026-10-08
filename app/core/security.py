"""Redact known secrets and database URL credentials before log formatting."""
import logging
import os
import re
import traceback
import secrets
from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from urllib.parse import quote, quote_plus, urlsplit, unquote

api_key = APIKeyHeader(name="X-API-Key", auto_error=False)


def cloud_api_access(request: Request, token: str = Security(api_key)):
    from app.core.config import settings
    if settings.DEPLOYMENT_MODE != "cloud" or request.url.path.endswith("/health"):
        return
    if not settings.API_ACCESS_TOKEN or not token or not secrets.compare_digest(token, settings.API_ACCESS_TOKEN):
        raise HTTPException(status_code=401, detail="API access token required")


def redact(value: object) -> str:
    message = str(value)
    secrets = []
    keys = ("DATABASE_URL", "MIGRATION_DATABASE_URL", "ERP_DB_PASSWORD", "VEHICLE_API_KEY",
            "FIPEPLACA_API_KEY", "PARTS_API_KEY", "API_ACCESS_TOKEN")
    for key in keys:
        secret = os.getenv(key, "")
        if secret:
            secrets.extend((secret, quote(secret, safe=""), quote_plus(secret)))
            if key.endswith("DATABASE_URL"):
                try:
                    password = unquote(urlsplit(secret).password or "")
                    if password:
                        secrets.extend((password, quote(password, safe=""), quote_plus(password)))
                except ValueError:
                    pass
    for secret in sorted(set(secrets), key=len, reverse=True):
        message = message.replace(secret, "[REDACTED]")
    message = re.sub(r"([a-z][a-z0-9+.-]*://)[^\s/@]+:[^\s@]+@", r"\1[REDACTED]@", message, flags=re.I)
    message = re.sub(r"(Bearer\s+)[^\s'\"]+", r"\1[REDACTED]", message, flags=re.I)
    return message


def install_log_redaction():
    factory = logging.getLogRecordFactory()
    if getattr(factory, "_redacts_secrets", False):
        return

    def safe_factory(*args, **kwargs):
        record = factory(*args, **kwargs)
        record.msg, record.args = redact(record.getMessage()), ()
        if record.exc_info:
            record.exc_text = redact("".join(traceback.format_exception(*record.exc_info)))
            record.exc_info = None
        return record

    safe_factory._redacts_secrets = True
    logging.setLogRecordFactory(safe_factory)
