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
- SQLAlchemy ORM, session management, and initial relational models
- pgvector extension support and vector-ready chunk embeddings

## Project structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   │   ├── routes
│   │   │   │   ├── collections.py
│   │   │   │   ├── system.py
│   │   │   │   └── vector_debug.py
│   │   │   └── router.py
│   │   ├── core
│   │   │   └── config.py
│   │   ├── db
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models
│   │   │   ├── collection.py
│   │   │   ├── document.py
│   │   │   ├── document_chunk.py
│   │   │   └── ingestion_job.py
│   │   ├── services
│   │   │   └── vector_search.py
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── .dockerignore
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

On startup, the API creates the current SQLAlchemy tables automatically for local development.
It also enables the `vector` extension and ensures the `document_chunks.embedding` column exists.

To stop the stack:

```bash
docker compose down
```

## Endpoints

- `GET /health` returns a basic service health payload.
- `GET /version` returns the API version payload.
- `GET /docs` opens the Swagger UI.
- `POST /collections` creates a collection row in PostgreSQL.
- `GET /collections` lists existing collections.
- `GET /collections/{collection_id}` fetches a collection row back by id.
- `PATCH /collections/{collection_id}` updates a collection.
- `DELETE /collections/{collection_id}` deletes a collection.
- `POST /debug/vector-search/seed` inserts mock chunk rows with fake embeddings.
- `POST /debug/vector-search/query` runs a temporary top-k similarity search.

## Database verification

With the stack running, create a collection:

```bash
curl -X POST http://127.0.0.1:8000/collections \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Collection","description":"Temporary verification collection"}'
```

Then fetch it back:

```bash
curl http://127.0.0.1:8000/collections/1
```

The backend currently creates these relational tables:

- `collections`
- `documents`
- `document_chunks`
- `ingestion_jobs`

`document_chunks.embedding` is stored as a `VECTOR(8)` placeholder column for vector retrieval development.

## Vector verification

With the stack running, seed mock vectors:

```bash
curl -X POST http://127.0.0.1:8000/debug/vector-search/seed
```

Then query for similar chunks:

```bash
curl -X POST http://127.0.0.1:8000/debug/vector-search/query \
  -H "Content-Type: application/json" \
  -d '{"query_embedding":[1,0,0,0,0,0,0,0],"limit":2}'
```

## Quick test

After the server is running, visit:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/version`
- `http://127.0.0.1:8000/docs`
