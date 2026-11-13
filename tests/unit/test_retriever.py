import numpy as np
import pandas as pd
import pytest

from bookmatch.retrieval.retriever import SemanticRetriever


@pytest.fixture
def retriever():
    """Cria um recuperador com dados fictícios, sem carregar o modelo E5."""

    catalog = pd.DataFrame({
        "book_id": ["1", "2", "3"],
        "title": ["Livro A", "Livro B", "Livro C"],
        "authors": ["Autor A", "Autor B", "Autor C"],
        "genre": ["Romance", "Conto", "Poesia"],
        "description": [
            "Uma história sobre amizade.",
            "Uma narrativa sobre aventuras.",
            "Uma história sobre conflitos familiares.",
        ],
    })

    # A ordem dos embeddings é propositalmente diferente da ordem dos livros no catálogo.
    book_ids = np.array(["3", "1", "2"])

    book_embeddings = np.array([
        [0.0, 1.0],    # Livro C
        [1.0, 0.0],    # Livro A
        [-1.0, 0.0],   # Livro B
    ])

    # cria a instância sem executar o __init__.
    retriever = SemanticRetriever.__new__(SemanticRetriever)

    retriever.catalog = catalog.set_index("book_id", drop=False)
    retriever.book_ids = book_ids
    retriever.book_embeddings = book_embeddings

    return retriever


def test_search_by_vector_ranking(retriever):
    """Verifica se os livros são ordenados pela similaridade."""

    query_embedding = np.array([1.0, 2.0])

    results = retriever.search_by_vector(
        query_embedding,
        top_k=3,
    )

    titles = [book["title"] for book in results]

    assert titles == ["Livro C", "Livro A", "Livro B"]
    assert results[0]["book_id"] == "3"

    assert results[0]["score"] > results[1]["score"]
    assert results[1]["score"] > results[2]["score"]


def test_search_by_vector_top_k(retriever):
    """Verifica se a quantidade de resultados respeita top_k."""

    query_embedding = np.array([1.0, 2.0])

    results = retriever.search_by_vector(
        query_embedding,
        top_k=2,
    )

    assert len(results) == 2


def test_search_by_vector_invalid_dimension(retriever):
    """Verifica se vetores com dimensões incompatíveis são rejeitados."""

    query_embedding = np.array([1.0, 2.0, 3.0])

    with pytest.raises(ValueError):
        retriever.search_by_vector(query_embedding)


def test_search_by_vector_invalid_shape(retriever):
    """Verifica se o método rejeita matrizes em vez de vetores."""

    query_embedding = np.array([[1.0, 2.0]])

    with pytest.raises(ValueError):
        retriever.search_by_vector(query_embedding)


@pytest.mark.parametrize(
    "query_embedding",
    [
        np.array([np.nan, 1.0]),
        np.array([np.inf, 1.0]),
    ],
)
def test_search_by_vector_invalid_values(retriever, query_embedding):
    """Verifica se valores NaN e infinitos são rejeitados."""

    with pytest.raises(ValueError):
        retriever.search_by_vector(query_embedding)


def test_search_by_vector_non_numeric(retriever):
    """Verifica se valores não numéricos são rejeitados."""

    query_embedding = np.array(["texto", "outro"])

    with pytest.raises(ValueError):
        retriever.search_by_vector(query_embedding)


def test_search_by_vector_zero_vector(retriever):
    """Verifica se vetores nulos são rejeitados."""

    query_embedding = np.array([0.0, 0.0])

    with pytest.raises(ValueError):
        retriever.search_by_vector(query_embedding)


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_by_vector_invalid_top_k(retriever, top_k):
    """Verifica se top_k precisa ser maior que zero."""

    query_embedding = np.array([1.0, 2.0])

    with pytest.raises(ValueError):
        retriever.search_by_vector(query_embedding, top_k=top_k)


@pytest.mark.parametrize("query", ["", "   ", None])
def test_search_empty_query(retriever, query):
    """Verifica se consultas textuais vazias são rejeitadas."""

    with pytest.raises(ValueError):
        retriever.search(query)


def test_search_uses_query_prefix(retriever):
    """Verifica a preparação da consulta para o modelo E5."""

    class FakeModel:
        def __init__(self):
            self.last_text = None
            self.last_kwargs = None

        def encode(self, text, **kwargs):
            self.last_text = text
            self.last_kwargs = kwargs

            # Embedding fictício da consulta.
            return np.array([0.0, 2.0])

    fake_model = FakeModel()
    retriever.model = fake_model

    results = retriever.search(
        "  Quero um romance sombrio  ",
        top_k=1,
    )

    assert fake_model.last_text == "query: Quero um romance sombrio"

    assert fake_model.last_kwargs["convert_to_numpy"] is True
    assert fake_model.last_kwargs["normalize_embeddings"] is True

    assert len(results) == 1
    assert results[0]["title"] == "Livro C"