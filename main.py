from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Create the FastAPI app
app = FastAPI(
    title="AI Business OS",
    description="Your AI-powered business platform",
    version="1.0.0"
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
    return {"status": "ok"}


# Route 3: Test endpoint — visit http://localhost:8000/test
@app.get("/test")
async def test_endpoint():
    debug = os.getenv("DEBUG", "False")
    return {
        "message": "Day 1 complete! FastAPI is working.",
        "debug_mode": debug
    }
