# Enterprise Copilot

Production-style RAG application scaffold with an API-first FastAPI backend.

## Current scope

This initial commit sets up:

- FastAPI backend skeleton
- Environment-backed settings
- Starter router registration
- Health and version endpoints
- CORS middleware configuration

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
│   └── requirements.txt
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

## Endpoints

- `GET /health` returns a basic service health payload.
- `GET /version` returns the API version payload.
- `GET /docs` opens the Swagger UI.

## Quick test

After the server is running, visit:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/version`
- `http://127.0.0.1:8000/docs`
