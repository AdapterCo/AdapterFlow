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
    # startup
    yield
    # shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Exceção não tratada capturada em %s %s: %s", request.method, request.url.path, str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno do servidor: {str(exc)}"}
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
