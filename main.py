# backend/main.py — Updated for Day 2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from routers import users, tasks
from models import User, Task

load_dotenv()

app = FastAPI(
    title="AI Business OS",
    description="Your AI-powered business platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "AI Business OS is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
