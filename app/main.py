from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.security import install_log_redaction
from app.health import readiness
install_log_redaction()
from app.db.database import init_db, get_db
from app.api.endpoints import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.DEPLOYMENT_MODE == "cloud" else ["*"],
    allow_credentials=settings.DEPLOYMENT_MODE != "cloud",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for Admin Panel
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Admin Dashboard
@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    if settings.DEPLOYMENT_MODE == "cloud":
        raise HTTPException(status_code=404, detail="Admin UI is local only")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Admin Dashboard Index File Not Found</h1>")

# Root Root Route
@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "health": "/api/v1/health",
        "docs": "/docs",
        "admin": "/admin"
    }

# Top-level Health check shortcut
@app.get("/health")
def health_redirect(db=Depends(get_db)):
    from app.api.endpoints import health_check
    return health_check(db=db)


@app.get("/health/live")
def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
def ready(db=Depends(get_db)):
    return readiness(db)
