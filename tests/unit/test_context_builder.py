import pytest

from bookmatch.rag.context_builder import build_context


@pytest.fixture
def sample_books():
    return [
        {
            "book_id": "1",
            "title": "A cabeça do santo",
            "authors": "Socorro Acioli",
            "genre": "Romance",
            "description": "Um jovem descobre um dom extraordinário.",
            "source_url": "https://example.com/book/1",
        },
        {
            "book_id": "2",
            "title": "Com armas sonolentas",
            "authors": "Carola Saavedra",
            "genre": "Romance",
            "description": "Uma narrativa sobre identidade e abandono.",
            "source_url": None,
        },
    ]


def test_build_context_contains_book_information(sample_books):
    context = build_context(sample_books)

    assert "A cabeça do santo" in context
    assert "Socorro Acioli" in context
    assert "Um jovem descobre um dom extraordinário." in context
    assert "https://example.com/book/1" in context


def test_build_context_preserves_ranking_order(sample_books):
    context = build_context(sample_books)

    assert context.index("A cabeça do santo") < context.index(
        "Com armas sonolentas"
    )


def test_build_context_handles_missing_optional_fields():
    books = [
        {
            "book_id": "1",
            "title": "Livro de teste",
            "authors": "Autor de teste",
            "description": "Descrição de teste.",
        }
    ]

    context = build_context(books)

    assert "Livro de teste" in context
    assert "Descrição de teste." in context


def test_build_context_handles_empty_list():
    assert build_context([]) == "Nenhum livro foi recuperado."


def test_build_context_rejects_invalid_input():
    with pytest.raises(TypeError):
        build_context("não é uma lista")


def test_build_context_rejects_invalid_book():
    with pytest.raises(TypeError):
        build_context(["não é um dicionário"])