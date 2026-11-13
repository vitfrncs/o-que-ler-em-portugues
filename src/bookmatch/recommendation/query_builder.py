import re
from bs4 import BeautifulSoup
import numpy as np

def build_reference_text(book: dict) -> str:
    """
    Constrói a representação textual de um livro de referência.

    Retorna:
        Texto contendo título e descrição, preparado para
        a geração de embeddings.
    """
    if not isinstance(book, dict):
        raise TypeError("O livro deve ser representado por um dicionário.")

    title = book.get("title")
    description = book.get("description")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("O livro deve possuir um título válido.")

    if not isinstance(description, str) or not description.strip():
        raise ValueError("O livro deve possuir uma descrição válida.")

    # remover tags HTML da descrição
    description = BeautifulSoup(description, "html.parser").get_text(separator=" ", strip=True)

    # normalizar espaços em branco
    description = re.sub(r"\s+", " ", description).strip()

    if not description:
        raise ValueError("A descrição do livro está vazia após a limpeza.")

    title = title.strip()

    return f"Título: {title}\nDescrição: {description}"


def build_references_embedding(books: list[dict], model,) -> np.ndarray:
    """
    Gera um embedding de consulta a partir de até três livros de referência.

    Retorna:
        Vetor NumPy com a média dos embeddings das referências.
    """

    if not isinstance(books, list):
        raise TypeError("As referências devem ser fornecidas em uma lista.")

    if not 1 <= len(books) <= 3:
        raise ValueError("Informe entre um e três livros de referência.")

    # preparar os textos das referências
    texts = [
        f"query: {build_reference_text(book)}"
        for book in books
    ]

    # Gerar os embeddings em uma única chamada
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(embeddings)

    # valida o formato retornado pelo modelo
    if embeddings.ndim != 2 or embeddings.shape[0] != len(books):
        raise ValueError("O modelo retornou embeddings com formato inesperado.")

    if not np.issubdtype(embeddings.dtype, np.floating):
        raise ValueError("Os embeddings devem conter valores reais.")

    if not np.isfinite(embeddings).all():
        raise ValueError("Os embeddings contêm valores inválidos.")

    # calcular a média ao longo das referências
    mean_embedding = np.mean(embeddings, axis=0)

    return mean_embedding