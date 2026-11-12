import pandas as pd
import pytest
from bookmatch.data.loader import load_catalog


def test_load_valid_catalog(tmp_path):
    # Arrange: preparar os dados de teste
    data = pd.DataFrame({
        "book_id": ["1", "2"],
        "title": ["Livro A", "Livro B"],
        "authors": ["Autor A", "Autor B"],
        "genre": ["Romance", "Poesia"],
        "description": [
            "Uma história sobre amizade.",
            "Poemas sobre a natureza.",
        ],
    })

    path = tmp_path / "catalog.csv"
    data.to_csv(path, index=False)

    # Act: executar a função
    catalog = load_catalog(path)

    # Assert: verificar o resultado
    assert len(catalog) == 2
    assert catalog["title"].tolist() == ["Livro A", "Livro B"]

def test_missing_required_column(tmp_path):
    # Arrange: Tirei a colina genre

    data = pd.DataFrame({
            "book_id": ["1", "2"],
            "title": ["Livro A", "Livro B"],
            "authors": ["Autor A", "Autor B"],
            "description": [
                "Uma história sobre amizade.",
                "Poemas sobre a natureza.",
            ],
        })

    path = tmp_path / "catalog.csv"
    data.to_csv(path, index=False)

    # Act + Assert
    # está eseperando que a execução da linha 48 gere um ValueError
    with pytest.raises(ValueError, match="genre"):
        load_catalog(path)