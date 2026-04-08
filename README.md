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
- document upload endpoint with local filesystem storage
- document list, detail, and delete APIs
- text extraction pipeline for TXT, PDF, and DOCX
- semantic chunking pipeline with configurable overlap
- OpenAI-backed embedding provider support
- end-to-end ingestion pipeline for extract, chunk, and embed
- top-k semantic retrieval service with collection/document filters
- grounded answer generation with citation formatting and insufficient-evidence fallback
- single-call `/ask` endpoint for full retrieval and grounded answer flow
- versioned grounded-answer prompt templates and guardrails
- retrieval narrowing by document, tags, source type, upload date, and collection metadata

## Project structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   │   ├── routes
│   │   │   │   ├── collections.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── retrieval.py
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
│   │   ├── prompts
│   │   │   ├── __init__.py
│   │   │   └── grounded_answer.py
│   │   ├── schemas
│   │   │   ├── ask.py
│   │   │   ├── answers.py
│   │   │   ├── collections.py
│   │   │   ├── documents.py
│   │   │   └── retrieval.py
│   │   ├── services
│   │   │   ├── ask.py
│   │   │   ├── answer_generation.py
│   │   │   ├── chunking.py
│   │   │   ├── collection_service.py
│   │   │   ├── document_parsers.py
│   │   │   ├── document_service.py
│   │   │   ├── embeddings.py
│   │   │   ├── ingestion.py
│   │   │   ├── llm.py
│   │   │   ├── retrieval.py
│   │   │   ├── storage.py
│   │   │   ├── text_extraction.py
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

3. Create a `.env` file with at least:

   ```bash
   OPENAI_API_KEY=your_api_key_here
   EMBEDDING_PROVIDER=openai
   EMBEDDING_MODEL=text-embedding-3-small
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-5.4-mini
   ```

4. Start the API:

   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Docker setup

1. Create a `.env` file with your OpenAI and database settings.

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
- `POST /collections/{collection_id}/documents/upload` uploads a PDF, DOCX, or TXT file.
- `GET /collections/{collection_id}/documents` lists documents for a collection.
- `GET /documents/{document_id}` fetches a single document with collection and ingestion details.
- `DELETE /documents/{document_id}` removes a document and its stored file copy.
- `POST /documents/{document_id}/extract` runs temporary raw-text extraction for an uploaded document.
- `POST /documents/{document_id}/chunk` runs temporary chunk generation and stores chunk rows.
- `POST /documents/{document_id}/ingest` runs extraction, chunking, embedding, and indexing in one step.
- `POST /retrieve` embeds a question and returns top-k semantic chunk matches.
- `POST /answer` retrieves supporting chunks and returns a grounded answer with inline citations.
- `POST /ask` runs the full query embedding, retrieval, and grounded answer flow in one call.
- `POST /debug/vector-search/embeddings` returns deterministic mock embeddings for debug verification.
- `POST /debug/vector-search/seed` inserts mock chunk rows with fake embeddings.
- `POST /debug/vector-search/query` runs a temporary top-k similarity search.

Grounded answering now uses a centralized versioned prompt template with these guardrails:

- answer only from provided context
- explicitly say when evidence is insufficient
- use a concise enterprise tone
- return structured grounded-answer JSON internally for stable parsing

Retrieval requests can now be narrowed with:

- `collection_id`
- `document_id` or `document_ids`
- `tags`
- `uploaded_from` and `uploaded_to`
- `source_types`
- `collection_name_contains`
- `collection_description_contains`

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

To upload a document into a collection:

```bash
curl -X POST http://127.0.0.1:8000/collections/1/documents/upload \
  -F "file=@/path/to/sample.txt"
```

To extract raw text from an uploaded document:

```bash
curl -X POST http://127.0.0.1:8000/documents/1/extract
```

The backend currently creates these relational tables:

- `collections`
- `documents`
- `document_chunks`
- `ingestion_jobs`

`document_chunks.embedding` is stored as a `VECTOR(n)` column sized to the active embedding model.
Chunking defaults are driven by config: `chunk_size=800`, `chunk_overlap=150`, `chunk_min_length=120`.
Embedding generation is provider-driven via config and now defaults to `openai` with `text-embedding-3-small`.
Answer generation is provider-driven via config and now defaults to `openai` with `gpt-5.4-mini`.
Document statuses currently move through `uploaded`, `processing`, `indexed`, and `failed`.
If you change embedding models or dimensions, existing stored embeddings are cleared and affected documents are marked `uploaded` so they can be re-ingested.

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

## Extraction verification

Upload one TXT, one PDF, and one DOCX file, then call:

```bash
curl -X POST http://127.0.0.1:8000/documents/{document_id}/extract
```

The temporary response includes:

- `extracted_text`
- `parser_metadata`
- PDF page markers when available

## Chunking verification

After uploading a long document, call:

```bash
curl -X POST http://127.0.0.1:8000/documents/{document_id}/chunk
```

Each chunk row stores:

- `chunk_index`
- `text`
- `page_reference` when available
- `start_char`
- `end_char`
- `overlap_from_previous_chars`

## Embedding Verification

Call the debug endpoint with repeated text:

```bash
curl -X POST http://127.0.0.1:8000/debug/vector-search/embeddings \
  -H "Content-Type: application/json" \
  -d '{"texts":["same text","same text","different text"],"query_text":"same text"}'
```

For the configured provider:

- repeated input returns the same embedding values for deterministic providers
- different text returns a different vector
- vector length matches the configured embedding dimensions

## Ingestion Verification

After uploading a document, call:

```bash
curl -X POST http://127.0.0.1:8000/documents/{document_id}/ingest
```

Expected behavior:

- document status starts as `uploaded`
- ingestion sets status to `processing`
- chunk rows are created
- embeddings are saved on chunks
- final document status becomes `indexed`

## Retrieval Verification

After indexing a few topic-specific documents, call:

```bash
curl -X POST http://127.0.0.1:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{"question":"Which document talks about finance forecasting?","collection_id":1,"top_k":3}'
```

The response returns:

- ranked chunks
- `score`
- citation metadata including collection, document, chunk index, page reference, and offsets

To narrow retrieval scope, you can also call:

```bash
curl -X POST http://127.0.0.1:8000/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "question":"Which document talks about finance forecasting?",
    "collection_name_contains":"Finance",
    "source_types":["txt"],
    "top_k":3
  }'
```

## Answer Verification

After indexing a few topic-specific documents, call:

```bash
curl -X POST http://127.0.0.1:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"question":"How should finance teams forecast quarterly cash flow?","collection_id":1,"top_k":3}'
```

Expected behavior:

- the answer is grounded in retrieved chunk text
- inline citations such as `[1]` map to real chunk and document references
- partially answerable questions return supported facts and identify missing information
- irrelevant questions return an insufficient-evidence response

## Ask Verification

After indexing a document, call:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"How should finance teams forecast quarterly cash flow?","collection_id":1,"top_k":3}'
```

The response returns:

- `answer`
- `citations`
- `retrieved_chunks`
- latency fields under `latency_ms`
- provider metadata under `providers`

## Quick test

After the server is running, visit:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/version`
- `http://127.0.0.1:8000/docs`
