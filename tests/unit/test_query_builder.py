import numpy as np
import pytest

from bookmatch.recommendation.query_builder import (
    build_reference_text,
    build_references_embedding,
)


BOOKS = [
    {
        "title": "Crepúsculo",
        "description": "<b>Romance</b> sobrenatural com vampiros.",
    },
    {
        "title": "Drácula",
        "description": "Uma história de terror sobre um vampiro.",
    },
    {
        "title": "Frankenstein",
        "description": "Uma história sobre ciência e criação.",
    },
]


class FakeModel:
    """Simula um modelo de embeddings sem carregar o E5."""

    def __init__(self, embeddings):
        self.embeddings = np.asarray(embeddings)
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return self.embeddings


def test_build_reference_text_removes_html():
    text = build_reference_text(BOOKS[0])

    assert text == (
        "Título: Crepúsculo\n"
        "Descrição: Romance sobrenatural com vampiros."
    )


@pytest.mark.parametrize("count", [1, 2, 3])
def test_build_references_embedding_accepts_one_to_three_books(count):
    model = FakeModel(np.eye(count, 3, dtype=np.float32))

    embedding = build_references_embedding(
        books=BOOKS[:count],
        model=model,
    )

    expected = np.mean(model.embeddings, axis=0)

    np.testing.assert_allclose(embedding, expected)
    assert embedding.shape == (3,)


def test_build_references_embedding_uses_correct_e5_prefix():
    model = FakeModel([[1.0, 0.0], [0.0, 1.0]])

    build_references_embedding(
        books=BOOKS[:2],
        model=model,
    )

    texts, kwargs = model.calls[0]

    assert texts == [
        (
            "query: Título: Crepúsculo\n"
            "Descrição: Romance sobrenatural com vampiros."
        ),
        (
            "query: Título: Drácula\n"
            "Descrição: Uma história de terror sobre um vampiro."
        ),
    ]

    assert kwargs["convert_to_numpy"] is True
    assert kwargs["normalize_embeddings"] is True

    # O modelo deve ser chamado uma única vez.
    assert len(model.calls) == 1


@pytest.mark.parametrize("books", [[], BOOKS * 2])
def test_build_references_embedding_rejects_invalid_quantity(books):
    model = FakeModel([[1.0, 0.0]])

    with pytest.raises(ValueError):
        build_references_embedding(books, model)


@pytest.mark.parametrize("books", [None, "Crepúsculo", {}])
def test_build_references_embedding_requires_list(books):
    model = FakeModel([[1.0, 0.0]])

    with pytest.raises(TypeError):
        build_references_embedding(books, model)


def test_build_references_embedding_rejects_missing_description():
    model = FakeModel([[1.0, 0.0]])

    with pytest.raises(ValueError):
        build_references_embedding(
            [{"title": "Crepúsculo", "description": None}],
            model,
        )


def test_build_references_embedding_rejects_invalid_shape():
    # Dois livros, mas o modelo retorna apenas um embedding.
    model = FakeModel([[1.0, 0.0]])

    with pytest.raises(ValueError, match="formato"):
        build_references_embedding(BOOKS[:2], model)


def test_build_references_embedding_rejects_nan():
    model = FakeModel([[float("nan"), 0.0]])

    with pytest.raises(ValueError):
        build_references_embedding(BOOKS[:1], model)