from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "book_id",
    "title",
    "authors",
    "genre",
    "description",
]


def load_catalog(path: str | Path) -> pd.DataFrame:
    """
    Load and validate the processed book catalog.

    Args:
        path: Path to the catalog CSV file.

    Returns:
        DataFrame containing the validated catalog.

    Raises:
        FileNotFoundError: If the catalog file does not exist.
        ValueError: If the catalog contains invalid data.
    """

    if not Path(path).exists():
        raise FileNotFoundError (f"O catálogo de livros não foi encontrado: {path}")

    catalog = pd.read_csv(path)

    missing_columns = set(REQUIRED_COLUMNS) - set(catalog.columns)

    if missing_columns:
        raise ValueError(f"Colunas aussentes {missing_columns}")

    if catalog.empty:
        raise ValueError("O catalogo está vazio.")

    # substituindo valores ausentes por str vazias
    required_data = catalog[REQUIRED_COLUMNS].fillna("").astype(str)

    # remove espaços e verifica se o conteúdo ficou vazio
    empty_values = required_data.apply(lambda col: col.str.strip().eq(""))

    if empty_values.any().any():
        raise ValueError("O catálogo contém valores ausentes ou vazios em colunas obrigatórias.")

    book_ids = catalog["book_id"].astype(str).str.strip()

    if book_ids.duplicated().any():
        raise ValueError("O catálogo contém identificadores de livros duplicados.")

    return catalog