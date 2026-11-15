from langchain_google_genai import ChatGoogleGenerativeAI


def create_llm():
    """Inicializa o modelo de linguagem utilizado pelo RAG."""

    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        temperature=0,
        max_retries=2,
    )