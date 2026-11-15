"""Interface Streamlit do O Que Ler em Português?.

MVP: busca por descrição e por 1–3 livros de referência (Apple Books).
"""

import logging
from pathlib import Path

import streamlit as st

from bookmatch.integrations.apple_books import search_books
from bookmatch.recommendation.reference_search import (
    filter_reference_candidates,
    retrieve_by_references,
)
from bookmatch.recommendation.query_builder import build_reference_text
from bookmatch.rag.pipeline import generate_recommendations
from bookmatch.retrieval.retriever import SemanticRetriever
from bookmatch.ui.components import (
    apply_styles,
    display_books,
    display_rag_result,
    render_footer,
    render_header,
    render_intro,
)


ROOT_DIR = Path(__file__).resolve().parent
CATALOG_PATH = ROOT_DIR / "data" / "processed" / "catalog_v0.csv"
INDEX_PATH = ROOT_DIR / "data" / "processed" / "semantic_index_e5.npz"
MAX_HISTORY = 10
MAX_REFERENCES = 3
LOGGER = logging.getLogger(__name__)


@st.cache_resource(show_spinner="Carregando o modelo e o catálogo...")
def load_retriever() -> SemanticRetriever:
    """Reutiliza o modelo E5 e o índice entre as interações."""
    return SemanticRetriever(
        catalog_path=str(CATALOG_PATH),
        index_path=str(INDEX_PATH),
    )


def initialize_session() -> None:
    """Prepara o estado da sessão; não sobrescreve dados já existentes."""
    defaults = {
        "search_history": [],
        "reference_results": [],
        "selected_references": [],
        "reference_lookup_count": 0,
        "reference_has_searched": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_history() -> None:
    """Limpa apenas as buscas já realizadas."""
    st.session_state.search_history = []


def check_index_files() -> bool:
    """Informa quando os arquivos locais do catálogo ainda não estão presentes."""
    if CATALOG_PATH.is_file() and INDEX_PATH.is_file():
        return True
    st.error(
        "Não encontrei o catálogo ou o índice semântico. "
        "Confira os arquivos em data/processed/."
    )
    return False


def save_search(
    query: str,
    books: list[dict],
    mode: str,
    *,
    rag_query: str | None = None,
) -> None:
    """Guarda a busca e um contexto de geração independente do formulário."""
    st.session_state.search_history.append({
        "query": query,
        "books": books,
        "mode": mode,
        "rag_query": rag_query if rag_query is not None else query,
        "rag_result": None,
    })
    st.session_state.search_history = st.session_state.search_history[-MAX_HISTORY:]
    st.rerun()


def run_preference_search(query: str) -> None:
    """Busca no catálogo a partir de um texto escrito pelo usuário."""
    query = query.strip()
    if not query:
        st.warning("Descreva o tipo de livro que você procura.")
        return
    if not check_index_files():
        return

    with st.spinner("Procurando histórias no acervo..."):
        try:
            books = load_retriever().search(query, top_k=5)
        except (ValueError, OSError, RuntimeError) as exc:
            st.error("Não foi possível realizar a busca semântica.")
            st.caption(f"Detalhe técnico: {exc}")
            return

    save_search(query=query, books=books, mode="preferences")


def lookup_reference_books(query: str) -> None:
    """Consulta Apple Books apenas após o envio do formulário."""
    query = query.strip()
    if not query:
        st.warning("Digite o nome de um livro ou autor.")
        return

    with st.spinner("Consultando o catálogo da Apple Books..."):
        try:
            raw_results = search_books(query, limit=20)
            candidates = filter_reference_candidates(raw_results)
        except (ValueError, RuntimeError, TypeError) as exc:
            st.error("Não foi possível consultar a Apple Books.")
            st.caption(f"Detalhe técnico: {exc}")
            return

    st.session_state.reference_results = candidates
    st.session_state.reference_has_searched = True
    st.session_state.reference_lookup_count += 1
    st.rerun()


def add_reference(book: dict) -> None:
    """Adiciona uma edição selecionada, evitando duplicatas e excesso."""
    selected = st.session_state.selected_references
    if len(selected) >= MAX_REFERENCES:
        st.warning("Você pode escolher no máximo três livros.")
        return
    if any(item["id"] == book["id"] for item in selected):
        st.warning("Essa edição já foi adicionada.")
        return
    selected.append(book)
    st.rerun()


def remove_reference(book_id: str) -> None:
    """Remove uma obra sem apagar as demais referências."""
    st.session_state.selected_references = [
        book for book in st.session_state.selected_references
        if book["id"] != book_id
    ]
    st.rerun()


def build_reference_rag_query(references: list[dict]) -> str:
    """Prepara a comparação com as obras de referência selecionadas.

    O conteúdo só será enviado ao LLM após um clique explícito no botão.
    Verifique antes as condições de uso das descrições da Apple Books.
    """
    sections = [
        "Quero encontrar livros originalmente escritos em português com temas, "
        "atmosferas ou conflitos semelhantes aos das obras de referência abaixo. "
        "Baseie as semelhanças apenas nas descrições fornecidas; se uma "
        "correspondência for parcial ou não demonstrável, informe isso."
    ]
    for position, book in enumerate(references, start=1):
        author = book.get("author") or "Autoria não informada"
        sections.append(
            f"[REFERÊNCIA {position}]\n"
            f"Autor(a): {author}\n"
            f"{build_reference_text(book)}"
        )
    return "\n\n".join(sections)


def run_reference_search() -> None:
    """Recupera livros a partir da combinação das referências escolhidas."""
    references = st.session_state.selected_references
    if not 1 <= len(references) <= MAX_REFERENCES:
        st.warning("Selecione de um a três livros de referência.")
        return
    if not check_index_files():
        return

    with st.spinner("Buscando obras semelhantes no acervo..."):
        try:
            books = retrieve_by_references(
                load_retriever(), references, top_k=5
            )
        except (ValueError, OSError, RuntimeError, TypeError) as exc:
            st.error("Não foi possível buscar pelos livros de referência.")
            st.caption(f"Detalhe técnico: {exc}")
            return

    reference_titles = "; ".join(
        f"{book['title']} — {book.get('author') or 'Autoria não informada'}"
        for book in references
    )
    save_search(
        query=f"Livros de referência: {reference_titles}",
        books=books,
        mode="references",
        rag_query=build_reference_rag_query(references),
    )


def render_preference_form() -> None:
    """Apresenta a busca por preferências, sem chamadas durante a digitação."""
    st.write("Conte que tipo de história você procura.")
    with st.form("preference_search_form", clear_on_submit=True):
        query = st.text_input(
            "Sua busca",
            placeholder="Um romance sobre memórias de família...",
        )
        submitted = st.form_submit_button("Descobrir livros →")

    if submitted:
        run_preference_search(query)


def render_reference_form() -> None:
    """Apresenta a seleção de edições e a busca por múltiplas referências."""
    st.write(
        "Procure um livro de que você gosta, confira a edição e adicione "
        "até três referências. Elas podem ter sido escritas em outros idiomas."
    )

    with st.form("apple_books_lookup_form"):
        query = st.text_input(
            "Pesquisar na Apple Books",
            placeholder="Crepúsculo Stephenie Meyer",
        )
        submitted = st.form_submit_button("Pesquisar edições →")

    if submitted:
        lookup_reference_books(query)

    candidates = st.session_state.reference_results
    if candidates:
        st.markdown("#### Escolha a edição correta")
        st.caption(
            "A busca pode retornar traduções, coletâneas e outras edições. "
            "Confira o título, a autoria e a sinopse antes de adicionar. "
            "Exibimos somente registros com descrição disponível."
        )

        choice = st.selectbox(
            "Edição encontrada",
            options=list(range(len(candidates))),
            index=None,
            placeholder="Selecione uma edição...",
            format_func=lambda i: (
                f"{candidates[i]['title']} — "
                f"{candidates[i].get('author') or 'Autoria não informada'} "
                f"(ID {candidates[i]['id']})"
            ),
            key=f"reference_choice_{st.session_state.reference_lookup_count}",
        )
        if choice is not None:
            selected = candidates[choice]
            clean_text = build_reference_text(selected)
            description = clean_text.partition("Descrição: ")[2]
            with st.expander("Conferir sinopse da edição", expanded=True):
                st.write(description[:700] + ("…" if len(description) > 700 else ""))
                st.caption(f"ID Apple Books: {selected['id']}")

            if st.button(
                "Adicionar às minhas referências +",
                disabled=len(st.session_state.selected_references) >= MAX_REFERENCES,
                key="add_reference_button",
            ):
                add_reference(selected)
    elif st.session_state.reference_has_searched:
        st.info(
            "Nenhuma edição com sinopse utilizável foi encontrada nesta busca. "
            "Experimente pesquisar pelo título e pelo nome do autor."
        )

    st.markdown("#### Seus livros favoritos")
    references = st.session_state.selected_references
    if not references:
        st.caption("Nenhuma referência selecionada por enquanto.")
    else:
        st.caption(f"{len(references)} de {MAX_REFERENCES} referências selecionadas")
        for position, book in enumerate(references, start=1):
            title_col, remove_col = st.columns([4, 1])
            with title_col:
                st.write(
                    f"**{position:02d}. {book['title']}** — "
                    f"{book.get('author') or 'Autoria não informada'}"
                )
            with remove_col:
                if st.button("Remover", key=f"remove_reference_{book['id']}"):
                    remove_reference(book["id"])

    if st.button(
        "Encontrar livros semelhantes →",
        type="primary",
        disabled=not references,
        key="search_by_selected_references",
    ):
        run_reference_search()


def generate_rag_for_search(history_index: int) -> None:
    """Gera uma vez por clique, mantendo os resultados semânticos no histórico."""
    search = st.session_state.search_history[history_index]
    if search.get("rag_result") is not None or not search["books"]:
        return
    if search.get("mode") == "references" and not search.get("rag_query"):
        st.warning("Refaça esta busca por referências para gerar recomendações com IA.")
        return

    with st.spinner("Preparando recomendações fundamentadas..."):
        try:
            result = generate_recommendations(
                user_query=search.get("rag_query") or search["query"],
                retrieved_books=search["books"],
            )
        except Exception:
            # A falha do provedor não deve impedir o uso da busca semântica.
            LOGGER.exception("Falha na geração de recomendações")
            st.error("Não foi possível gerar recomendações com IA nesta tentativa.")
            st.info("Os resultados da busca semântica continuam disponíveis.")
            return

    search["rag_result"] = result
    st.rerun()


def render_history() -> None:
    """Exibe buscas salvas; só chama o Gemini após clique explícito."""
    if not st.session_state.search_history:
        st.divider()
        st.markdown("#### Para começar")
        st.write(
            "Experimente: *um romance sobre memórias de família* "
            "ou use uma obra de que você gostou como referência."
        )
        return

    st.divider()
    left, right = st.columns([3, 1])
    with left:
        st.markdown("### Suas descobertas")
    with right:
        st.button(
            "Limpar buscas",
            key="clear_searches",
            on_click=clear_history,
        )

    for index, item in enumerate(st.session_state.search_history, start=1):
        source = "REFERÊNCIAS" if item.get("mode") == "references" else "PREFERÊNCIAS"
        st.caption(f"BUSCA {index:02d} · {source}")
        st.write(item["query"])

        if item.get("rag_result") is not None:
            display_rag_result(item["rag_result"], turn_index=index)
            continue

        if item["books"]:
            st.caption(
                "Ao gerar recomendações com IA, sua consulta, as sinopses "
                "recuperadas e, na busca por referências, as descrições das "
                "obras selecionadas serão enviadas ao Gemini. "
                "Use somente conteúdo cujo envio seja permitido."
            )
            if st.button(
                "Gerar recomendações com IA ✨",
                key=f"generate_rag_{index}",
            ):
                generate_rag_for_search(index - 1)
        display_books(item["books"], turn_index=index)


def main() -> None:
    st.set_page_config(
        page_title="O Que Ler em Português?",
        page_icon="📖",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    apply_styles()
    initialize_session()

    render_header()
    render_intro()

    mode = st.radio(
        "Como você gostaria de encontrar livros?",
        options=["Por preferências", "Por livros favoritos"],
        horizontal=True,
        key="search_mode",
    )
    if mode == "Por preferências":
        render_preference_form()
    else:
        render_reference_form()

    render_history()
    render_footer()


if __name__ == "__main__":
    main()