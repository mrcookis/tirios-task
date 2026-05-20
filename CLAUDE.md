# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Recruitment task project built with FastAPI, SQLAlchemy (async), and PostgreSQL. Environment managed by `uv`.

## Environment Setup

```bash
# Create virtual environment (Python 3.11)
uv venv --python 3.11

# Install all dependencies (runtime + dev)
uv sync --dev

# Copy and fill in environment variables
cp .env.example .env
```

## Development Commands

### Run the development server
```bash
uv run uvicorn main:app --reload
```

### Run tests
```bash
uv run pytest
uv run pytest tests/test_health.py::test_health_check -v
```

### Database migrations (Alembic)
```bash
# Generate a new migration (after changing models)
uv run alembic revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic upgrade head

# Rollback one step
uv run alembic downgrade -1
```

### Add a dependency
```bash
uv add <package>          # runtime
uv add --dev <package>    # dev only
```

## Code Structure

```
tirios-task/
├── main.py               # FastAPI app entry point
├── app/
│   ├── core/
│   │   └── config.py     # Pydantic Settings (reads from .env)
│   └── api/
│       └── routes/
│           └── health.py # Example route
├── alembic/              # Database migrations
├── tests/
│   ├── conftest.py       # Shared fixtures (async HTTP client)
│   └── test_health.py
├── pyproject.toml        # Project metadata and dependencies
├── alembic.ini           # Alembic configuration
├── .env                  # Local environment variables (not committed)
└── .env.example          # Template for .env
```

## Common Development Patterns

- Add new routes in `app/api/routes/`, include the router in `main.py`
- Define SQLAlchemy models, then run `alembic revision --autogenerate` to create migrations
- Access settings via `from app.core.config import settings`
- Tests use an `AsyncClient` fixture from `tests/conftest.py`
