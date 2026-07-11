# backend/main.py — Updated for Day 3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Import all routers
from routers import auth, users, tasks, agents

# Import models so SQLAlchemy is aware of them
from models import User, Task

load_dotenv()

app = FastAPI(
    title="AI Business OS",
    description="AI-powered multi-agent business platform",
    version="1.0.0",
    # These show up on the /docs page
    contact={"name": "AI Business OS"},
    license_info={"name": "Private"},
)

# CORS — allows the React frontend at localhost:3000 to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers — all routes get the /api/v1 prefix
app.include_router(auth.router,  prefix="/api/v1")   # /api/v1/auth/...
app.include_router(users.router, prefix="/api/v1")   # /api/v1/users/...
app.include_router(tasks.router, prefix="/api/v1")   # /api/v1/tasks/...
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "AI Business OS is running!", "status": "healthy", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
