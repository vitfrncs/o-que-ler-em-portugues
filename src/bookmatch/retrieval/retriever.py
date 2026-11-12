import numpy as np 
from sentence_transformers import SentenceTransformer

from bookmatch.data.loader import load_catalog
from bookmatch.retrieval.semantic import (
    compute_similarities,
    get_top_k_indices,
)

class SemanticRetriever:
    """Recupera livros por similaridade semântica."""

    