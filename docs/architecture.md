# Architecture

BookMatch is being developed as a book recommendation system that combines traditional recommendation methods with semantic search and LLM-generated explanations.

The project is organized as a Python package under `src/bookmatch`. The idea is to keep the recommendation logic independent from the API and the language model, so that different approaches can be implemented and evaluated separately.

## Project structure

The main components are organized as follows:

```text
src/bookmatch/
├── api/              # HTTP endpoints
├── catalog/          # Book data loading and validation
├── retrieval/        # TF-IDF and semantic search
├── recommendation/   # Collaborative and hybrid recommendation
├── rag/              # Context construction and RAG pipeline
├── llm/              # Local LLM integration
└── evaluation/       # Evaluation metrics
```

Most of these modules are still empty. They will be implemented incrementally as the project develops.

## API

The backend uses FastAPI, running with Uvicorn.

Currently, the API contains a single endpoint:

`GET /health`

It returns a JSON response indicating that the application is running.

The API code is split into two files:

- `main.py` creates the FastAPI application and registers the router.
- `routes.py` contains the endpoint definitions.

This keeps the application setup separate from the routes as new endpoints are added.

## Recommendation pipeline

The planned recommendation flow is:

```text
User query
    |
    v
Retrieval (TF-IDF / Embeddings)
    |
    v
Ranked books
    |
    v
Context construction
    |
    v
LLM (Ollama?)
    |
    v
Recommendations with explanations
```

The retrieval methods will determine which books to recommend. The LLM will only generate explanations based on the retrieved book information.

This distinction is important because the recommendation system should still work when the LLM is unavailable.

## Testing

Tests are written with pytest and stored in `tests/`.

The first integration test uses FastAPI's `TestClient` to check the `/health` endpoint without starting a separate server.

Tests can be executed with:

```bash
python -m pytest -v
```

## Next steps

The next step is to prepare and validate the book catalog. Once the data is ready, the first retrieval method will be implemented using TF-IDF.

This document will be updated as new components are introduced :).