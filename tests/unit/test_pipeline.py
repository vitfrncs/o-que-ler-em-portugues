import pytest

from bookmatch.rag.pipeline import generate_recommendations
from bookmatch.rag.schemas import RecommendationResponse


BOOKS = [
    {
        "book_id": "123",
        "title": "Livro A",
        "authors": "Autora Fictícia",
        "genre": "Romance",
        "description": "Um romance sobre conflitos familiares.",
    },
    {
        "book_id": "456",
        "title": "Livro B",
        "authors": "Autor Fictício",
        "genre": "Poesia",
        "description": "Poemas sobre a natureza.",
    },
]


class FakeLLM:
    """Simula o comportamento do LLM sem utilizar uma API."""

    def __init__(self, response):
        self.response = response

    def with_structured_output(self, schema, method):
        assert schema is RecommendationResponse
        assert method == "json_schema"
        return self

    def invoke(self, messages):
        return self.response


def test_pipeline_returns_recommendations(monkeypatch):

    fake_response = RecommendationResponse(
        recommendations=[
            {
                "book_id": "123",
                "reason": "A obra aborda conflitos familiares.",
            }
        ],
        message="Encontrei uma correspondência.",
    )

    monkeypatch.setattr(
        "bookmatch.rag.pipeline.create_llm",
        lambda: FakeLLM(fake_response),
    )

    result = generate_recommendations(
        user_query="Quero um romance sobre conflitos familiares.",
        retrieved_books=BOOKS,
    )

    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["book"]["title"] == "Livro A"

    assert len(result["other_books"]) == 1
    assert result["other_books"][0]["title"] == "Livro B"


def test_pipeline_rejects_unknown_book(monkeypatch):

    fake_response = RecommendationResponse(
        recommendations=[
            {
                "book_id": "999",
                "reason": "Uma história interessante.",
            }
        ],
        message="Encontrei uma recomendação.",
    )

    monkeypatch.setattr(
        "bookmatch.rag.pipeline.create_llm",
        lambda: FakeLLM(fake_response),
    )

    with pytest.raises(ValueError, match="não recuperado"):
        generate_recommendations(
            user_query="Quero um romance.",
            retrieved_books=BOOKS,
        )


def test_pipeline_accepts_no_recommendations(monkeypatch):

    fake_response = RecommendationResponse(
        recommendations=[],
        message="Não encontrei correspondências suficientemente claras.",
    )

    monkeypatch.setattr(
        "bookmatch.rag.pipeline.create_llm",
        lambda: FakeLLM(fake_response),
    )

    result = generate_recommendations(
        user_query="Quero um romance sobrenatural.",
        retrieved_books=BOOKS,
    )

    assert result["recommendations"] == []
    assert len(result["other_books"]) == 2