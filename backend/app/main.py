import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import get_settings
from app.core.database import init_db, lifespan_db
from app.api import auth, projects, documents, reports, jobs, admin, corpus

settings = get_settings()

# In-memory fallback rate-limit window for auth anti-spam when Redis is unavailable
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_AUTH_RATE_LIMIT_PATHS = {
    "/api/auth/register",
    "/api/auth/forgot-password",
    "/api/auth/jwt/login",
}
_AUTH_RATE_LIMIT_MAX = 20
_AUTH_RATE_LIMIT_WINDOW_SEC = 60


def _cors_origins() -> list[str]:
    origins = [settings.frontend_url.rstrip("/")]
    if settings.allowed_origins:
        for origin in settings.allowed_origins.split(","):
            cleaned = origin.strip().rstrip("/")
            if cleaned and cleaned not in origins:
                origins.append(cleaned)
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    # Run seeds
    from app.seed.legal_corpus import run_all_seeds
    await run_all_seeds()
    yield
    # Shutdown handled by lifespan_db


app = FastAPI(
    title="ECO-Compliance Engine API",
    description="API for sovereign B2B compliance audit platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Optional strict HTTPS enforcement behind reverse proxy in production
    if settings.force_https and request.url.path != "/health":
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).lower()
        if proto == "http":
            https_url = str(request.url.replace(scheme="https"))
            return RedirectResponse(url=https_url, status_code=307)

    # 2. Anti-spam rate limiting on unauthenticated public auth endpoints
    if request.method == "POST" and request.url.path in _AUTH_RATE_LIMIT_PATHS:
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        key = f"{client_ip}:{request.url.path}"
        now = time.monotonic()
        bucket = _RATE_LIMIT_BUCKETS[key]
        while bucket and now - bucket[0] > _AUTH_RATE_LIMIT_WINDOW_SEC:
            bucket.popleft()
        if len(bucket) >= _AUTH_RATE_LIMIT_MAX:
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de tentatives. Veuillez réessayer dans une minute."},
            )
        bucket.append(now)

    response = await call_next(request)

    # 3. Standard production security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.force_https or settings.environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
# Reports are part of the core upload-to-audit journey.
app.include_router(reports.router, prefix="/api")
# app.include_router(jobs.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(corpus.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ece-api"}


@app.get("/")
async def root():
    return {"message": "ECO-Compliance Engine API", "docs": "/docs"}
