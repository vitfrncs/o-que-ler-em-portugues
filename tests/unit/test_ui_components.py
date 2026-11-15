"""Testes dos auxiliares puros da interface (sem abrir um navegador)."""

import pytest

from bookmatch.ui.components import _display_text, _valid_source_url


@pytest.mark.parametrize(
    "value, expected",
    [
        ("  Ana  ", "Ana"),
        (None, "Não informado"),
        ("   ", "Não informado"),
        (42, "Não informado"),
    ],
)
def test_display_text(value, expected):
    assert _display_text(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("https://example.com/book", True),
        ("http://example.com", True),
        ("javascript:alert(1)", False),
        ("file:///tmp/book", False),
        ("https://", False),
        ("https://[", False),
        (None, False),
        ("", False),
    ],
)
def test_valid_source_url(value, expected):
    assert _valid_source_url(value) is expected