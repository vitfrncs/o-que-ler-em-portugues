import httpx

def search_books(query: str, limit: int = 5) -> list[dict]:

    if not isinstance(query, str) or not query.strip():
        raise ValueError("A consulta deve ser um texto não vazio.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("limit deve ser um inteiro entre 1 e 200.")

    params = {
        "term": query.strip(),
        "media": "ebook",
        "entity": "ebook",
        "country": "br",
        "limit": limit,
    }

    try:
        response = httpx.get("https://itunes.apple.com/search", params=params, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("Falha ao consultar a API de livros.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("A API retornou um JSON inválido.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Formato de resposta inesperado.")

    books = []
    for item in data["results"]:
        if not isinstance(item, dict):
            continue
        if item.get("trackId") is None or not item.get("trackName"):
            continue
        books.append({
            "id": str(item["trackId"]),
            "title": item["trackName"],
            "author": item.get("artistName"),
            "description": item.get("description"),
            "cover_url": item.get("artworkUrl100"),
            "source_url": item.get("trackViewUrl"),
        })

    return books
