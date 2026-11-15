from pydantic import BaseModel, Field


class BookRecommendation(BaseModel):
    """Representa uma recomendação produzida pelo LLM."""

    book_id: str = Field(description="ID de um livro presente no contexto recuperado.")

    reason: str = Field(description="Justificativa baseada na descrição do livro.")


class RecommendationResponse(BaseModel):
    """Representa a resposta estruturada do RAG."""

    recommendations: list[BookRecommendation] = Field(
        description="Lista com até três livros recomendados.",
        max_length=3,
    )

    message: str = Field(
        description="Mensagem complementar ao usuário."
    )