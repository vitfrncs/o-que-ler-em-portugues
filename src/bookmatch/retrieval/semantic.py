import pandas as pd
import numpy as np

def build_book_text(book: pd.Series) -> str:
    book_text = (
        f"Título: {book['title']}\n"
        f"Gênero: {book['genre']}\n"
        f"Descrição: {book['description']}"
    )
    return book_text       

def compute_similarities(query_embedding: np.ndarray, book_embeddings: np.ndarray,
) -> np.ndarray:
    """Calcula a similaridade de cosseno entre embeddings normalizados."""

    scores = book_embeddings @ query_embedding

    return scores

def get_top_k_indices(scores: np.ndarray, top_k: int = 5) -> np.ndarray:
    """Retorna os índices dos k maiores scores, em ordem decrescente."""

    if top_k < 1:
        raise ValueError("top_k deve ser maior que zero.")

    # argsort retorna os índices que colocariam os valores em ordem crescente.
    return np.argsort(scores)[::-1][:top_k]