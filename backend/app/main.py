from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db, lifespan_db
from app.api import auth, projects, documents, reports, jobs, admin

settings = get_settings()


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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
# app.include_router(reports.router, prefix="/api")
# app.include_router(jobs.router, prefix="/api")
# app.include_router(admin.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ece-api"}


@app.get("/")
async def root():
    return {"message": "ECO-Compliance Engine API", "docs": "/docs"}