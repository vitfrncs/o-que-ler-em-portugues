import pandas as pd

from bookmatch.data.cleaning import normalize_description


def test_normalize_whitespace():
    text = "Uma   história\nsobre  fantasia."

    result = normalize_description(text)

    assert result == "Uma história sobre fantasia."


def test_normalize_html():
    text = "Fantasia &amp; aventura"

    result = normalize_description(text)

    assert result == "Fantasia & aventura"


def test_missing_description():
    assert normalize_description(None) == ""
    assert normalize_description(pd.NA) == ""


def test_preserve_original_content():
    text = "Você destruiria seu mundo?A resposta..."

    result = normalize_description(text)

    assert result == text