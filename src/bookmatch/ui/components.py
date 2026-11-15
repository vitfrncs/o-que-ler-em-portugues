"""Componentes de apresentação reutilizáveis."""

from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st


STYLES_PATH = Path(__file__).with_name("styles.css")
REPOSITORY_URL = "https://github.com/vitfrncs/o-que-ler-em-portugues"


def _display_text(value: object, fallback: str = "Não informado") -> str:
    """Converte um campo opcional do catálogo em texto legível."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _valid_source_url(value: object) -> bool:
    """Aceita apenas URLs HTTP(S) com domínio identificável."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return False
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def apply_styles() -> None:
    """Aplica CSS estático criado pelo projeto (nunca conteúdo externo)."""
    css = STYLES_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_header() -> None:
    """Apresenta a marca e a navegação mínima."""
    brand_col, github_col = st.columns([4, 1])
    with brand_col:
        st.markdown(
            '<p class="bm-brand">o que ler em português<span>?</span></p>',
            unsafe_allow_html=True,
        )
    with github_col:
        st.link_button("código ↗", REPOSITORY_URL, key="github_header")
    st.divider()


def render_intro() -> None:
    """Introduz a proposta do site sem prometer funcionalidades futuras."""
    st.markdown(
        '<p class="bm-eyebrow">UM PEQUENO CATÁLOGO DE DESCOBERTAS</p>',
        unsafe_allow_html=True,
    )
    st.title("Que história você quer encontrar?")
    st.write(
        "Descubra obras originalmente escritas em português a partir "
        "dos temas, atmosferas e histórias de que você gosta."
    )
    st.caption(
        "Protótipo experimental · busca por similaridade semântica · "
        "recomendações opcionais com IA (não avaliadas sistematicamente)"
    )
    st.divider()


def _render_book_card(
    book: dict,
    *,
    position: int,
    button_key: str,
    reason: str | None = None,
) -> None:
    """Apresenta um livro sem confiar em HTML ou URLs de fontes externas."""
    title = _display_text(book.get("title"), "Título não informado")
    authors = _display_text(book.get("authors"), "Autoria não informada")
    genre = _display_text(book.get("genre"), "")
    description = _display_text(book.get("description"), "")
    source_url = book.get("source_url")

    with st.container():
        genre_suffix = f"  ·  {genre}" if genre else ""
        st.caption(f"{position:02d}  /  LITERATURA{genre_suffix}")
        st.subheader(title)
        st.write(authors)

        if reason:
            st.markdown("**Por que esta obra?**")
            st.write(reason)

        if description:
            with st.expander("Ler sinopse"):
                st.write(description)
        else:
            st.caption("Sinopse não disponível neste registro.")

        if _valid_source_url(source_url):
            st.link_button(
                "Página da obra ↗",
                str(source_url).strip(),
                key=button_key,
            )
        else:
            st.caption("Link da obra não disponível.")

    st.divider()


def display_books(
    books: list[dict],
    turn_index: int | str,
    *,
    other_results: bool = False,
) -> None:
    """Mostra candidatos na ordem devolvida pelo recuperador."""
    if not books:
        st.info("Não há livros para exibir nesta busca.")
        return

    label = (
        "OUTRAS OBRAS ENCONTRADAS"
        if other_results
        else "OBRAS ENCONTRADAS NO ACERVO"
    )
    st.caption(f"{len(books)} {label}")
    if other_results:
        st.write(
            "Estes livros também apareceram na busca, mas não foram selecionados "
            "pelo assistente como recomendações principais."
        )
    else:
        st.write(
            "Estes são os resultados mais próximos no índice. "
            "A proximidade semântica não garante que atendam a todos os critérios."
        )

    for position, book in enumerate(books, start=1):
        if not isinstance(book, dict):
            continue  # Defesa de apresentação; o contrato real é do recuperador.
        _render_book_card(
            book,
            position=position,
            button_key=f"source_{turn_index}_{position}",
        )


def display_rag_result(result: dict, turn_index: int) -> None:
    """Exibe a seleção fundamentada do LLM e os demais resultados da busca."""
    recommendations = result["recommendations"]

    st.markdown("#### Recomendações para você")
    if result["message"]:
        st.write(result["message"])

    if not recommendations:
        st.info("Não há recomendações com correspondência suficiente nesta busca.")
    else:
        for position, item in enumerate(recommendations, start=1):
            _render_book_card(
                item["book"],
                position=position,
                reason=item["reason"],
                button_key=f"rag_source_{turn_index}_{position}",
            )

    st.markdown("#### Explore também")
    display_books(
        result["other_books"],
        turn_index=f"{turn_index}_other",
        other_results=True,
    )


def render_footer() -> None:
    """Expõe limitações da versão em linguagem simples."""
    st.markdown(
        '<p class="bm-footer">feito para descobrir literatura, '
        'não para adivinhar livros. · versão experimental</p>',
        unsafe_allow_html=True,
    )
