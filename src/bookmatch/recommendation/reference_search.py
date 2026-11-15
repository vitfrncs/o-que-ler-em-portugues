"""Operações de domínio para encontrar obras a partir de livros de referência."""

from bookmatch.recommendation.query_builder import (
    build_reference_text,
    build_references_embedding,
)


def filter_reference_candidates(books: list[dict]) -> list[dict]:
    """Mantém resultados Apple Books com ID, título e sinopse utilizável.

    Remove registros repetidos por ID. Não determina se a obra é a edição
    correta. Essa decisão permanece com quem está usando a interface.
    """
    if not isinstance(books, list):
        raise TypeError("Os resultados da busca devem ser uma lista.")

    candidates: list[dict] = []
    seen_ids: set[str] = set()

    for book in books:
        if not isinstance(book, dict):
            continue

        book_id = book.get("id")
        if book_id is None or isinstance(book_id, bool) or not str(book_id).strip():
            continue

        try:
            build_reference_text(book)
        except (ValueError, TypeError):
            # Sem uma sinopse utilizável não há representação semântica adequada.
            continue

        book_id = str(book_id).strip()
        if book_id in seen_ids:
            continue

        normalized = dict(book)
        normalized["id"] = book_id
        candidates.append(normalized)
        seen_ids.add(book_id)

    return candidates


def retrieve_by_references(
    retriever,
    books: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """Transforma de 1 a 3 referências em uma consulta ao índice existente."""
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k deve ser um inteiro positivo.")

    embedding = build_references_embedding(books=books, model=retriever.model)
    return retriever.search_by_vector(embedding, top_k=top_k)