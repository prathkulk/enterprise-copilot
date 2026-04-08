# Enterprise Copilot

Production-style RAG application scaffold with an API-first FastAPI backend.

## Current scope

This initial commit sets up:

- FastAPI backend skeleton
- Environment-backed settings
- Starter router registration
- Health and version endpoints
- CORS middleware configuration
- Docker-based local development stack
- PostgreSQL service for local development

## Project structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   │   ├── routes
│   │   │   │   └── system.py
│   │   │   └── router.py
│   │   ├── core
│   │   │   └── config.py
│   │   └── main.py
│   ├── .dockerignore
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

## Local setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

3. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

4. Start the API:

   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Docker setup

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Start the local stack:

   ```bash
   docker compose up --build
   ```

3. Visit the running API:

   ```text
   http://127.0.0.1:8000/health
   http://127.0.0.1:8000/version
   http://127.0.0.1:8000/docs
   ```

The compose stack includes:

- `backend` running FastAPI with source mounted for live local development
- `postgres` running PostgreSQL 16 with a persistent named volume

To stop the stack:

```bash
docker compose down
```

## Endpoints

- `GET /health` returns a basic service health payload.
- `GET /version` returns the API version payload.
- `GET /docs` opens the Swagger UI.

## Quick test

After the server is running, visit:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/version`
- `http://127.0.0.1:8000/docs`
