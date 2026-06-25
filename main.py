from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from sqlalchemy import text

# Load variables from .env file
load_dotenv()

# Import database engine and Base
from database import engine, Base

# Import all models so Base.metadata knows about them
import models  # noqa: F401
from models.user import User  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown lifecycle.
    On startup: create all tables that don't exist yet.
    """
    print("🔌 Connecting to PostgreSQL...")
    try:
        # Create tables defined by Base subclasses
        Base.metadata.create_all(bind=engine)
        # Quick connection check
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connected & tables ready!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise
    yield
    # Shutdown: dispose of the connection pool
    engine.dispose()
    print("🔒 Database connection pool closed.")


# Create the FastAPI app
app = FastAPI(
    title="AI Business OS",
    description="Your AI-powered business platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Route 1: Home — visit http://localhost:8000/
@app.get("/")
async def root():
    return {
        "message": "AI Business OS is running!",
        "status": "healthy",
        "version": "1.0.0"
    }


# Route 2: Health check — visit http://localhost:8000/health
@app.get("/health")
async def health_check():
    """Check both app and database health."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "database": db_status,
    }


# Route 3: Test endpoint — visit http://localhost:8000/test
@app.get("/test")
async def test_endpoint():
    debug = os.getenv("DEBUG", "False")
    return {
        "message": "Day 1 complete! FastAPI is working.",
        "debug_mode": debug
    }
