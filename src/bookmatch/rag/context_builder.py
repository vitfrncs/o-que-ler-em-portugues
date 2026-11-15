def build_context(books: list[dict]) -> str:
    """
    Organiza os livros recuperados em um contexto textual para o LLM.

    Retorna:
        String contendo as informações dos livros recuperados.
    """
    if not isinstance(books, list):
        raise TypeError("Os livros devem ser fornecidos em uma lista.")

    if not books:
        return "Nenhum livro foi recuperado."

    sections = []

    for i, book in enumerate(books, start=1):
        if not isinstance(book, dict):
            raise TypeError("Cada livro deve ser um dicionário.")

        section = (
            f"[LIVRO {i}]\n"
            f"ID: {book.get('book_id', 'Não informado')}\n"
            f"Título: {book.get('title', 'Não informado')}\n"
            f"Autor(es): {book.get('authors', 'Não informado')}\n"
            f"Gênero: {book.get('genre', 'Não informado')}\n"
            f"Descrição: {book.get('description') or 'Não disponível'}"
        )

        if book.get("source_url"):
            section += f"\nFonte: {book['source_url']}"

        sections.append(section)

    return "\n\n".join(sections)