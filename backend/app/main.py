import re
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        from app.api.v1.marketplaces import service
        await service.client.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from uuid import uuid4
    incident = str(uuid4())
    logger.error("Falha interna incidente=%s tipo=%s", incident, type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor.", "incident_id": incident}
    )

@app.middleware("http")
async def sanitize_redirect_location(request: Request, call_next):
    response = await call_next(request)
    if 300 <= response.status_code < 400 and "location" in response.headers:
        loc = response.headers["location"]
        # Convert any absolute URL containing backend or localhost to a relative path
        loc = re.sub(r"^https?://(?:backend|localhost|127\.0\.0\.1)(?::\d+)?", "", loc)
        response.headers["location"] = loc
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {"name": "AdapterFlow API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/ready", dependencies=[])
async def readiness():
    from sqlalchemy import text
    from app.core.database import async_session_maker
    from pathlib import Path
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        if not Path(settings.STORAGE_PATH).is_dir():
            return JSONResponse(status_code=503, content={"status": "storage_unavailable"})
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Conflito ou dado incompatível com as regras do cadastro."})

@app.exception_handler(ValidationError)
async def invalid_business_data(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": "Dados de cadastro inválidos. Verifique campos obrigatórios, limites e regras relacionadas."})
