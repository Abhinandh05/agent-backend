# Day 2: Database Setup (FastAPI + PostgreSQL)

This document provides a detailed explanation of the steps completed during the Day 2 setup, how the different components work together, and instructions on how to test the application.

---

## 1. What Was Done

We successfully integrated a robust PostgreSQL database layer into the FastAPI application using SQLAlchemy and Alembic. The key steps included:

1. **Installed Dependencies:** Added `sqlalchemy` (for database interaction), `alembic` (for database migrations), `psycopg2-binary` (the PostgreSQL driver), and `pydantic[email]` (for email validation).
2. **Database Connection Setup (`database.py`):** Configured the SQLAlchemy engine and session factory to connect to the local PostgreSQL database (`ai_business_os`).
3. **Database Models (`models/`):** 
   - Created a `User` model (`users` table) to store user credentials and profile data.
   - Created a `Task` model (`tasks` table) to track AI agent tasks linked to specific users via a Foreign Key.
4. **Data Validation (`schemas.py`):** Set up Pydantic models (Schemas) to define the structure of data coming into the API (Requests) and going out of the API (Responses).
5. **Alembic Migrations (`alembic/` & `alembic.ini`):** Initialized Alembic to track changes to the database schema. We successfully generated and applied the first migration to create the tables in PostgreSQL.
6. **API Routers (`routers/`):** Built modular endpoints for users and tasks using FastAPI's `APIRouter`.
7. **App Integration (`main.py`):** Registered the routers into the main FastAPI application and set up basic CORS middleware.

---

## 2. Detailed Explanation of Components

### `database.py`
This file is the bridge between the FastAPI app and the PostgreSQL database. 
- It uses `create_engine` to establish a connection pool.
- `SessionLocal` generates isolated database sessions for each request.
- The `get_db()` dependency yields a database session and ensures it is safely closed after the request is finished.

### `models/` (SQLAlchemy Models)
These files represent the actual tables in the PostgreSQL database.
- They inherit from the declarative `Base` class.
- SQLAlchemy automatically translates these Python classes into SQL `CREATE TABLE` commands (managed by Alembic).
- We established a **One-to-Many relationship** where one `User` can have multiple `Task`s.

### `schemas.py` (Pydantic Models)
While SQLAlchemy models handle the database, Pydantic schemas handle data validation and serialization for the API.
- For example, `UserCreate` ensures that when someone registers, they provide a valid `EmailStr` and password.
- `UserResponse` automatically formats the database output, hiding sensitive information (like passwords) before sending it to the client.

### Alembic Migrations
Alembic is a version control system for your database schema.
- Instead of manually writing SQL queries to create or update tables, Alembic looks at your `models/` and figures out what changed.
- `alembic revision --autogenerate` creates a Python script with instructions to apply or revert changes.
- `alembic upgrade head` applies those changes to the actual PostgreSQL database.

---

## 3. How to Run the Application

To start the FastAPI server, follow these steps:

1. **Activate the Virtual Environment** (if not already active):
   ```bash
   source venv/bin/activate
   ```
2. **Run the Uvicorn Server:**
   ```bash
   uvicorn main:app --reload
   ```
   *(The `--reload` flag ensures the server automatically restarts when you make changes to your code).*

The server will start running at `http://localhost:8000`.

---

## 4. How to Test the API

FastAPI automatically generates a beautiful, interactive testing interface (Swagger UI). 

1. Open your web browser and go to: **[http://localhost:8000/docs](http://localhost:8000/docs)**
2. You will see a list of all your API endpoints categorized by "Users" and "Tasks".

### Testing Flow (Step-by-Step)

**Step A: Create a User**
1. Click on the `POST /api/v1/users/` endpoint to expand it.
2. Click the **"Try it out"** button.
3. Edit the Request Body JSON to include your details:
   ```json
   {
     "name": "Alice Smith",
     "email": "alice@example.com",
     "password": "test123"
   }
   ```
4. Click **"Execute"**. You should receive a `200 OK` response with the new user's ID (e.g., `id: 1`).

**Step B: Verify the User**
1. Expand `GET /api/v1/users/`.
2. Click **"Try it out"** and then **"Execute"**. 
3. You will see a list of all registered users in the database.

**Step C: Create a Task for the User**
1. Expand `POST /api/v1/tasks/`.
2. Click **"Try it out"**.
3. In the `user_id` query parameter field, enter `1` (or the ID of the user you just created).
4. Edit the Request Body JSON:
   ```json
   {
     "agent_type": "research",
     "prompt": "Tell me about the future of AI."
   }
   ```
5. Click **"Execute"**. The task will be saved to the database with a "pending" status.

**Step D: View the User's Tasks**
1. Expand `GET /api/v1/tasks/`.
2. Click **"Try it out"**, enter `1` for the `user_id`, and click **"Execute"**.
3. You will receive a list of all tasks associated with that specific user.
