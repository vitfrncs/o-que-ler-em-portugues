import html
import re
import unicodedata

import pandas as pd


def normalize_description(text: str | None) -> str:
    """Normaliza uma descrição sem modificar seu significado."""

    if pd.isna(text):
        return ""

    text = html.unescape(str(text))
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text