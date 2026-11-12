import pandas as pd

from bookmatch.retrieval.semantic import build_book_text, compute_similarities, get_top_k_indices

import numpy as np

def test_build_book_text():
    # Arrange
    book = pd.Series({
        "title": "Livro A",
        "genre": "Romance",
        "description": "Uma história sobre amizade.",
    })

    # Act
    result = build_book_text(book)

    # Assert
    expected = (
        "Título: Livro A\n"
        "Gênero: Romance\n"
        "Descrição: Uma história sobre amizade."
    )

    assert result == expected

def test_compute_similarities():
    # Arrange
    query_embedding = np.array([1.0, 0.0])

    book_embeddings = np.array([
        [1.0, 0.0],
        [0.0, 1.0],
        [0.6, 0.8],
    ])

    # Act
    scores = compute_similarities(
        query_embedding,
        book_embeddings,
    )

    # Assert
    expected = np.array([1.0, 0.0, 0.6])

    np.testing.assert_allclose(scores, expected)

def test_get_top_k_indices():
    # Arrange
    scores = np.array([0.82, 0.31, 0.95, 0.67])

    # Act
    indices = get_top_k_indices(scores, top_k=2)

    # Assert
    np.testing.assert_array_equal(indices, [2, 0])

