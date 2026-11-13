import numpy as np 
from sentence_transformers import SentenceTransformer
from pathlib import Path
from bookmatch.data.loader import load_catalog
from bookmatch.retrieval.semantic import (
    compute_similarities,
    get_top_k_indices,
)

class SemanticRetriever:
    """Recupera livros por similaridade semântica."""

    def __init__(self, catalog_path: str | Path, index_path: str | Path):
        self.catalog = load_catalog(catalog_path)

        with np.load(index_path, allow_pickle=False) as index:
            self.book_embeddings = index["embeddings"]
            self.book_ids = index["book_ids"].astype(str)
            model_name = str(index["model_name"].item())

        # verifica a correspondência entre o índice e o catálogo
        self.catalog["book_id"] = self.catalog["book_id"].astype(str)

        if len(self.book_ids) != len(self.book_embeddings):
            raise ValueError("O número de embeddings e de IDs não corresponde.")

        if len(set(self.book_ids)) != len(self.book_ids):
            raise ValueError("Existem IDs duplicados no índice semântico.")

        if set(self.book_ids) != set(self.catalog["book_id"]):
            raise ValueError("O catálogo e o índice possuem livros diferentes.")

        # Para que o dataframe ise os valores da coluna book_id como indice
        # (Para facilitar a busca de livros pelo ID)
        self.catalog = self.catalog.set_index("book_id", drop=False)

        # Carregar o mesmo modelo utilizado na indexação
        self.model = SentenceTransformer(model_name, device="cpu")

    def search(self, query: str, top_k: int = 5):
        """Recupera livros semanticamente semelhantes a uma consulta textual."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("A consulta deve ser um texto não vazio.")
        
        query = query.strip()

        query_embedding = self.model.encode(f"query: {query}", convert_to_numpy=True, normalize_embeddings=True)

        return self.search_by_vector(query_embedding, top_k)


    def search_by_vector(self, query_embedding: np.ndarray, top_k: int = 5):
        """
            Recebe um embeddings de consulta e encontra os livros mais semalhantes no catálogo.
        
            Retorna:Lista de dicionários, cada um contendo informações sobre um livro
        """

        if query_embedding.ndim != 1:
            raise ValueError("O vetor de consulta deve possuir apenas uma dimensão.")

        if len(query_embedding) != self.book_embeddings.shape[1]:
            raise ValueError("O vetor de consulta possui dimensão diferente dos vetores catálogo.")

        if (not np.issubdtype(query_embedding.dtype, np.number) 
            or np.issubdtype(query_embedding.dtype, np.complexfloating)):
            raise ValueError("O vetor de consulta deve conter valores numéricos reais.")

        if not np.isfinite(query_embedding).all():
            raise ValueError("O vetor de consulta possui valores NaN ou infinitos.")

        if top_k <= 0:
            raise ValueError("O valor de top_k deve ser positivo e maior que zero.")

        norm = np.linalg.norm(query_embedding.astype(np.float64))

        if norm == 0:
            raise ValueError("O vetor de consulta não pode ser nulo.")

        query_embedding = query_embedding / norm

        scores = compute_similarities(query_embedding, self.book_embeddings)

        top_indices = get_top_k_indices(scores, top_k)

        results = []

        for index in top_indices:
            book_id = self.book_ids[index]
            book = self.catalog.loc[book_id]

            result = {
                "book_id": str(book_id),
                "title": book["title"],
                "authors": book["authors"],
                "genre": book["genre"],
                "description": book["description"],
                "source_url": book.get("source_url"),
                "score": float(scores[index]),
            }

            results.append(result)

        return results


