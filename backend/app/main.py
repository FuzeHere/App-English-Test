from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
import app.models  # noqa: F401
from app.api.routes import router as api_router
from app.services.question_generation.seed_bank import ensure_seed_bank


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize tables and seed initial approved question bank on startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_seed_bank(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Private desktop preparation simulator inspired by the published CEST General construct.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
