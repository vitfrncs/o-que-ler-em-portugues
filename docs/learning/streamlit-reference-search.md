# Streamlit — busca por livros de referência

> Guia de revisão da implementação em `app.py` e `src/bookmatch/recommendation/reference_search.py`. Esta etapa **não** adiciona um LLM: os resultados são candidatos recuperados por embeddings E5, ainda sem avaliação automática de adequação.

## 1. O problema que estamos resolvendo

Queremos oferecer dois caminhos no mesmo site:

1. **Preferências:** a pessoa digita temas, atmosfera ou gênero; o `SemanticRetriever.search()` recupera obras.
2. **Livros favoritos:** a pessoa pesquisa uma obra na Apple Books, seleciona a edição correta, adiciona de uma a três referências e executa `search_by_vector()` após combinar seus embeddings.

Os dois caminhos terminam no **mesmo catálogo de obras originalmente escritas em português**. Um livro estrangeiro serve apenas de referência e não entra automaticamente nas recomendações.

```text
                   Streamlit (app.py)
                          │
              ┌───────────┴─────────────┐
              ▼                         ▼
      Busca por preferências    Busca por referências
              │                         │
       retriever.search()       Apple Books API
              │                         │
              │                   Escolha de edição
              │                         │
              │              build_references_embedding()
              │                         │
              │               retriever.search_by_vector()
              └────────────┬────────────┘
                           ▼
               Histórico e display_books()
```

## 2. Por que usamos `st.radio()`?

No `main()`, `st.radio()` seleciona o **modo de busca**. O widget determina qual formulário é mostrado. A interface muda, mas o recuperador semântico é o mesmo. O argumento `horizontal=True` apresenta as opções lado a lado.

Leia no `app.py`:

```python
mode = st.radio(
    "Como você gostaria de encontrar livros?",
    options=["Por preferências", "Por livros favoritos"],
    horizontal=True,
    key="search_mode",
)
```

**Experimento:** mude o modo e observe que suas referências selecionadas continuam guardadas. Por quê? Porque elas estão em `st.session_state`, não em uma variável local.

## 3. Por que usamos dois `st.form()`?

O formulário atrasa o envio dos valores até a pessoa clicar em `st.form_submit_button()`. Assim:

- pesquisar uma edição **não faz uma requisição HTTP a cada letra digitada**;
- uma busca por preferências só executa quando a consulta é enviada;
- o fluxo é previsível e fácil de testar.

No Streamlit, widgets dentro de um formulário são enviados em conjunto; botões comuns (`st.button`) não podem ficar dentro de `st.form`.

**Leia:** `render_preference_form()` e `render_reference_form()`.

## 4. Os três estados necessários para a Apple Books

É importante separar **resultados pesquisados** de **livros selecionados**:

| Chave do estado | Tipo | Significado |
|---|---|---|
| `reference_results` | `list[dict]` | Edições encontradas na última consulta à Apple Books |
| `selected_references` | `list[dict]` | Até três edições que a pessoa confirmou |
| `reference_lookup_count` | `int` | Gera uma nova chave para o seletor quando os resultados mudam |

Também temos `reference_has_searched`, para distinguir **nenhuma busca feita** de **busca que não encontrou edições utilizáveis**, e `search_history`, que guarda buscas já executadas no catálogo.

### Por que uma nova chave no seletor?

O `st.selectbox()` usa `key` para identificar seu estado. Se o conjunto de edições muda, não queremos que ele preserve acidentalmente uma escolha antiga. Por isso o código usa `key=f"reference_choice_{...}"` após cada nova pesquisa.

### Por que não escolher automaticamente o primeiro resultado?

A Apple Books pode retornar a obra original, traduções, coletâneas ou outra edição. A pessoa verifica **título, autoria, ID e prévia da sinopse** antes de adicionar uma referência. Não tratamos `country="br"` como filtro garantido de idioma.

## 5. `st.selectbox()` e `format_func`

O seletor utiliza como opções os índices `0, 1, 2...` dos resultados encontrados. O `format_func` converte cada índice em uma descrição legível:

```python
format_func=lambda i: (
    f"{candidates[i]['title']} — "
    f"{candidates[i].get('author') or 'Autoria não informada'} "
    f"(ID {candidates[i]['id']})"
)
```

O valor **retornado** continua sendo o índice. A formatação só altera a apresentação. O argumento `index=None` exige que a pessoa escolha um item explicitamente, em vez de selecionar o primeiro por padrão.

## 6. Como impedimos referências duplicadas?

A função `add_reference()` consulta `selected_references` e verifica o ID antes de adicionar. Ela também impede escolher mais de três referências.

A função `remove_reference()` remove apenas a edição indicada pelo ID. Não é necessário chamar a Apple Books novamente, pois os dados da seleção já estão guardados na sessão.

**Exercício:** identifique a condição que impede adicionar o mesmo `id` duas vezes. O que ocorreria se comparássemos apenas o título?

## 7. A função de domínio não depende de Streamlit

Criamos `src/bookmatch/recommendation/reference_search.py` com duas funções:

- `filter_reference_candidates()` filtra registros incompletos, sem sinopse ou duplicados;
- `retrieve_by_references()` gera o embedding combinado com a função que já tínhamos e chama o `SemanticRetriever`.

Essa separação permite usar exatamente as mesmas operações em um script Python, em testes ou futuramente em uma API, sem importar Streamlit.

Observe o fluxo:

```python
embedding = build_references_embedding(books=books, model=retriever.model)
return retriever.search_by_vector(embedding, top_k=top_k)
```

O recuperador é passado pronto para a função: **não carregamos um segundo E5**. O modelo e o índice são reutilizados pelo cache do Streamlit.

## 8. O que acontece quando o usuário clica no botão final?

1. `run_reference_search()` verifica se existem de 1 a 3 referências.
2. Confere se o catálogo e o índice estão disponíveis.
3. Usa o recuperador existente para gerar um vetor médio e encontrar 5 candidatos.
4. `save_search()` registra a busca com `mode="references"`.
5. `st.rerun()` reexecuta o script e `render_history()` mostra os resultados usando `display_books()`.

Cada busca por referências é uma operação independente: **ainda não existe uma conversa contextual com LLM**.

## 9. Tratamento de erros e limitações

- Se a Apple Books falhar, a interface mostra um erro e preserva as referências já selecionadas.
- Se a edição não tem descrição útil, ela não é oferecida nesta versão. Assim, não geramos embeddings a partir de títulos isolados.
- As descrições podem vir em outro idioma e podem sofrer truncamento no modelo de embeddings.
- A média de até três embeddings é um baseline experimental, não uma técnica comprovadamente melhor.
- A busca retorna os vizinhos mais próximos do catálogo, mesmo quando não há correspondência temática satisfatória.
- Resultados de busca **não são recomendações validadas por um LLM**.
- Os arquivos de dados usados localmente ainda precisam de uma estratégia de disponibilização compatível com suas condições de reutilização antes da hospedagem pública.

## 10. Exercícios de revisão

1. Desenhe o caminho de um clique em **Pesquisar edições →** até os resultados aparecerem na tela. Onde a chamada HTTP acontece?
2. Explique a diferença entre `reference_results` e `selected_references`.
3. Por que o primeiro resultado da Apple Books não é selecionado automaticamente?
4. Por que o resultado da busca aparece no histórico, em vez de ser mostrado diretamente dentro de `run_reference_search()`?
5. O que `@st.cache_resource` economiza? Em que situação seria perigoso compartilhar um objeto mutable globalmente?
6. Qual parte do código você testaria sem Streamlit? Por quê?
7. Qual é a diferença entre **um candidato recuperado** e **uma recomendação fundamentada**?

## 11. Testes e execução

Na raiz do repositório, com `.venv` ativado:

```bash
python -m pytest tests/unit/test_reference_search.py -v
python -m pytest tests/ -v
python -m streamlit run app.py
```

Fluxos manuais úteis:

- Pesquisar uma preferência em linguagem natural e conferir os livros.
- Pesquisar `Crepúsculo Stephenie Meyer`, verificar a sinopse e selecionar a edição esperada.
- Pesquisar `Drácula Bram Stoker`, conferir a edição, adicionar a segunda referência e realizar a busca.
- Adicionar e remover uma referência; tentar selecionar uma repetida.
- Alternar os modos de busca e verificar que as referências continuam selecionadas.
- Conferir que o histórico distingue `PREFERÊNCIAS` e `REFERÊNCIAS`.

**Critério de conclusão:** os dois modos devem funcionar localmente e produzir resultados do mesmo catálogo, sem depender de um LLM.
