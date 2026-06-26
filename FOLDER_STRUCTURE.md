# Backend Folder Structure

This document outlines the current directory structure of our AI Multi-Agent Business OS backend (FastAPI) up to Day 3. 

```text
backend/
│
├── alembic/                    # Database migrations directory (created by Alembic)
│   ├── versions/               # Contains all generated migration scripts (e.g., create tables)
│   ├── env.py                  # Alembic environment setup (connects to our metadata)
│   └── script.py.mako          # Template used when generating new migrations
│
├── core/                       # Core application utilities and settings
│   ├── __init__.py
│   ├── dependencies.py         # FastAPI dependencies (e.g., get_current_active_user)
│   └── security.py             # Security functions (password hashing, JWT token creation)
│
├── models/                     # SQLAlchemy Database Models (Tables)
│   ├── __init__.py             # Exports all models so Alembic can find them
│   ├── user.py                 # User table schema (id, email, hashed_password, etc.)
│   └── task.py                 # Task table schema (id, user_id, prompt, etc.)
│
├── routers/                    # API Endpoints organized by domain
│   ├── __init__.py
│   ├── auth.py                 # Authentication routes (/register, /login, /logout)
│   ├── users.py                # User profile routes (/users/me)
│   └── tasks.py                # Task management routes (/tasks/)
│
├── agents/                     # Placeholder for AI Agent logic (for upcoming days)
├── services/                   # Placeholder for external services/business logic
├── tests/                      # Directory for pytest test files
├── tools/                      # Placeholder for custom agent tools
│
├── .env                        # Environment variables (Database URL, JWT Secret Key)
├── alembic.ini                 # Alembic configuration file
├── database.py                 # Database connection setup and session maker
├── main.py                     # Entry point for the FastAPI application (registers routers)
├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, passlib, etc.)
├── schemas.py                  # Pydantic models for data validation (Input/Output shapes)
└── venv/                       # Python Virtual Environment (Dependencies are installed here)
```

## Directory Responsibilities

- **`core/`**: Handles application-wide utilities that don't belong to a specific feature. Authentication logic, security, and shared dependencies live here.
- **`models/`**: Defines the physical structure of your database tables using SQLAlchemy ORM.
- **`schemas.py`**: Defines the shape of the data entering and leaving your API (Data Transfer Objects) using Pydantic. It strictly validates incoming request bodies and outgoing responses.
- **`routers/`**: Contains the actual API endpoints. By splitting them into multiple files (auth, users, tasks), we keep the code modular and clean rather than putting everything into `main.py`.
- **`alembic/`**: Keeps track of every change made to the database schema over time, allowing you to easily upgrade or rollback the database structure.
