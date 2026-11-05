import pandas as pd


REQUIRED_COLUMNS = [
    "title",
    "authors",
    "description_clean",
    "language",
    "source_name",
    "source_url",
    "author_verified",
    "description_usage_status",
    "review_status",
]


def validate_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Verifica quais candidatos estão aptos a entrar no catálogo."""

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Colunas ausentes: {sorted(missing_columns)}"
        )

    result = df.copy()

    # Verifica presença de metadados essenciais
    text_columns = [
        "title",
        "authors",
        "description_clean",
        "language",
        "source_name",
        "source_url",
    ]

    result["metadata_complete"] = (
        result[text_columns]
        .fillna("")
        .astype(str)
        .apply(lambda col: col.str.strip().ne(""))
        .all(axis=1)
    )

    # Verifica autoria brasileira
    result["author_valid"] = (
        result["author_verified"].eq(True).fillna(False)
    )

    # Verifica se a reutilização da descrição foi aprovada
    result["usage_valid"] = (
        result["description_usage_status"]
        .eq("approved")
        .fillna(False)
    )

    # Resultado da validação
    result["is_valid"] = (
        result["metadata_complete"]
        & result["author_valid"]
        & result["usage_valid"]
        & result["review_status"].eq("approved").fillna(False)
    )

    return result