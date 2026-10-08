from fastapi.responses import JSONResponse
from sqlalchemy import text
from alembic.config import Config
from alembic.script import ScriptDirectory


def readiness(db):
    try:
        db.execute(text("SELECT 1"))
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        if revision != head:
            return JSONResponse({"status": "not_ready", "database": "migration_required"}, status_code=503)
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return JSONResponse({"status": "not_ready", "database": "unavailable"}, status_code=503)
