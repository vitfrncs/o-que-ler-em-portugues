from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from bookmatch.data.loader import load_catalog
from bookmatch.retrieval.semantic import build_book_text


ROOT_DIR = Path(__file__).resolve().parents[1]

CATALOG_PATH = ROOT_DIR / "data/processed/catalog_v0.csv"
INDEX_PATH = ROOT_DIR / "data/processed/semantic_index_e5.npz"

MODEL_NAME = "intfloat/multilingual-e5-small"


def main():
    catalog = load_catalog(CATALOG_PATH)
    texts = [
        f"passage: {build_book_text(book)}"
        for _, book in catalog.iterrows()
    ]

    model = SentenceTransformer(MODEL_NAME, device="cpu")

    embeddings = model.encode(texts, batch_size=8, convert_to_numpy=True, normalize_embeddings=True)

    book_ids = np.asarray(catalog["book_id"].astype(str).tolist(), dtype=str)

    np.savez_compressed(INDEX_PATH, embeddings=embeddings, book_ids=book_ids, model_name=np.array(MODEL_NAME))

    print("Índice semântico criado com sucesso!")
    print(f"Total de livros: {len(book_ids)}")
    print(f"Formato dos embeddings: {embeddings.shape}")
    print(f"Índice salvo em: {INDEX_PATH}")


if __name__ == "__main__":
    main()