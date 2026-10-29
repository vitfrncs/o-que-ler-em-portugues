from fastapi import FastAPI

from bookmatch.api.routes import router

# objeto da classe FastAPI
app = FastAPI(
    title="BookMatch AI",
    description="Hybrid Book Recommendation System",
    version="0.1.0",
)


app.include_router(router)