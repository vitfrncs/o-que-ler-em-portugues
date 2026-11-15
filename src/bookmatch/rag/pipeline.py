from langchain_core.messages import HumanMessage, SystemMessage

from bookmatch.rag.context_builder import build_context
from bookmatch.rag.prompts import build_messages
from bookmatch.rag.llm import create_llm
from bookmatch.rag.schemas import RecommendationResponse


def generate_recommendations(
    user_query: str,
    retrieved_books: list[dict],
) -> dict:
    """
    Gera recomendações fundamentadas nos livros recuperados.

    Args:
        user_query: Pedido original do usuário.
        retrieved_books: Livros retornados pelo SemanticRetriever.

    Returns:
        Dicionário contendo:
            - recommendations: livros recomendados e justificativas;
            - message: mensagem complementar do LLM;
            - other_books: livros recuperados não recomendados.
    """

    # 1. Validar as entradas
    if not isinstance(user_query, str) or not user_query.strip():
        raise ValueError("A consulta do usuário não pode estar vazia.")

    if not isinstance(retrieved_books, list):
        raise TypeError("Os livros recuperados devem formar uma lista.")

    if not retrieved_books:
        return {
            "recommendations": [],
            "message": "Nenhum livro foi encontrado no catálogo.",
            "other_books": [],
        }

    # 2. Criar um índice dos livros recuperados por ID
    books_by_id = {}

    for book in retrieved_books:
        if not isinstance(book, dict) or book.get("book_id") is None:
            raise ValueError("Os livros recuperados possuem formato inválido.")

        book_id = str(book["book_id"])

        if not book_id.strip() or book_id in books_by_id:
            raise ValueError("Identificador de livro inválido ou duplicado.")

        books_by_id[book_id] = book

    # 3. Construir o contexto
    context = build_context(retrieved_books)

    # 4. Construir as mensagens
    messages = build_messages(
        user_query=user_query,
        context=context,
    )

    langchain_messages = [
        SystemMessage(content=messages[0]["content"]),
        HumanMessage(content=messages[1]["content"]),
    ]

    # 5. Inicializar o LLM com saída estruturada
    llm = create_llm()

    structured_llm = llm.with_structured_output(
        RecommendationResponse,
        method="json_schema",
    )

    # 6. Gerar a resposta
    response = structured_llm.invoke(langchain_messages)

    if not isinstance(response, RecommendationResponse):
        raise ValueError("O LLM retornou uma resposta inesperada.")

    # 7. Validar os IDs e associar os metadados originais
    recommendations = []
    recommended_ids = set()

    for item in response.recommendations:
        book_id = item.book_id

        if book_id not in books_by_id:
            raise ValueError(
                f"O LLM recomendou um livro não recuperado: {book_id}"
            )

        if book_id in recommended_ids:
            raise ValueError(
                f"O LLM retornou uma recomendação duplicada: {book_id}"
            )

        if not item.reason.strip():
            raise ValueError("A justificativa não pode estar vazia.")

        recommended_ids.add(book_id)

        recommendations.append(
            {
                "book": books_by_id[book_id],
                "reason": item.reason.strip(),
            }
        )

    # 8. Separar os livros não recomendados
    other_books = [
        book
        for book in retrieved_books
        if str(book["book_id"]) not in recommended_ids
    ]

    # 9. Validar a mensagem complementar
    message = response.message.strip()

    if not recommendations and not message:
        raise ValueError(
            "O LLM deve explicar quando não houver recomendações."
        )

    # 10. Retornar o resultado
    return {
        "recommendations": recommendations,
        "message": message,
        "other_books": other_books,
    }