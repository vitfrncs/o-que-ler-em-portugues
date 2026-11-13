import httpx
import pytest

from bookmatch.integrations.apple_books import search_books


API_URL = "https://itunes.apple.com/search"


def make_response(data, status_code=200):
    """Cria uma resposta HTTP simulada."""

    request = httpx.Request("GET", API_URL)

    return httpx.Response(
        status_code=status_code,
        json=data,
        request=request,
    )


def test_search_books_success(monkeypatch):
    """Verifica a pesquisa e a conversão dos metadados."""

    api_data = {
        "resultCount": 1,
        "results": [
            {
                "trackId": 123,
                "trackName": "Livro A",
                "artistName": "Autor A",
                "description": "Uma história fictícia.",
                "artworkUrl100": "https://example.com/cover.jpg",
                "trackViewUrl": "https://example.com/book",
            }
        ],
    }

    def fake_get(url, params, timeout):
        assert url == API_URL
        assert params["term"] == "Livro A"
        assert params["media"] == "ebook"
        assert params["entity"] == "ebook"
        assert params["country"] == "br"
        assert params["limit"] == 5
        assert timeout == 10.0

        return make_response(api_data)

    monkeypatch.setattr(httpx, "get", fake_get)

    books = search_books("  Livro A  ")

    assert len(books) == 1
    assert books[0] == {
        "id": "123",
        "title": "Livro A",
        "author": "Autor A",
        "description": "Uma história fictícia.",
        "cover_url": "https://example.com/cover.jpg",
        "source_url": "https://example.com/book",
    }


def test_search_books_empty_results(monkeypatch):
    """Verifica o comportamento quando nenhum livro é encontrado."""

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: make_response({
            "resultCount": 0,
            "results": [],
        }),
    )

    books = search_books("Livro inexistente")

    assert books == []


def test_search_books_optional_fields(monkeypatch):
    """Verifica se campos opcionais podem estar ausentes."""

    api_data = {
        "results": [
            {
                "trackId": 456,
                "trackName": "Livro B",
            }
        ]
    }

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: make_response(api_data),
    )

    books = search_books("Livro B")

    assert len(books) == 1
    assert books[0]["title"] == "Livro B"
    assert books[0]["author"] is None
    assert books[0]["description"] is None


def test_search_books_skips_invalid_records(monkeypatch):
    """Verifica se registros incompletos são ignorados."""

    api_data = {
        "results": [
            {"trackId": 1, "trackName": "Livro válido"},
            {"trackId": 2},
            {"trackName": "Livro sem identificador"},
            None,
        ]
    }

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: make_response(api_data),
    )

    books = search_books("Livro")

    assert len(books) == 1
    assert books[0]["title"] == "Livro válido"


@pytest.mark.parametrize("query", ["", "   ", None, 123])
def test_search_books_invalid_query(query):
    """Verifica se consultas inválidas são rejeitadas."""

    with pytest.raises(ValueError):
        search_books(query)


@pytest.mark.parametrize("limit", [0, -1, 201, True, 2.5])
def test_search_books_invalid_limit(limit):
    """Verifica os limites permitidos para a quantidade de resultados."""

    with pytest.raises(ValueError):
        search_books("Livro A", limit=limit)


def test_search_books_http_error(monkeypatch):
    """Verifica o tratamento de erros HTTP."""

    def fake_get(url, params, timeout):
        return make_response({}, status_code=503)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="Falha ao consultar"):
        search_books("Livro A")


def test_search_books_connection_error(monkeypatch):
    """Verifica o tratamento de falhas de conexão."""

    def fake_get(url, params, timeout):
        request = httpx.Request("GET", url)
        raise httpx.ConnectError(
            "Falha de conexão simulada",
            request=request,
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="Falha ao consultar"):
        search_books("Livro A")


def test_search_books_invalid_json(monkeypatch):
    """Verifica o tratamento de respostas que não contêm JSON válido."""

    def fake_get(url, params, timeout):
        return httpx.Response(
            200,
            text="Isto não é JSON",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="JSON inválido"):
        search_books("Livro A")


def test_search_books_unexpected_response(monkeypatch):
    """Verifica se estruturas inesperadas são rejeitadas."""

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: make_response({
            "books": []
        }),
    )

    with pytest.raises(ValueError, match="Formato de resposta inesperado"):
        search_books("Livro A")