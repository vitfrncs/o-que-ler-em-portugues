# Streamlit na prática — a interface do *O Que Ler em Português?*

> Material de aprendizagem vinculado à implementação. Leia com o editor aberto em `app.py`, `src/bookmatch/ui/components.py`, `src/bookmatch/ui/styles.css` e `.streamlit/config.toml`.
>
> **Escopo desta versão:** busca por preferências em linguagem natural com `SemanticRetriever`, histórico de buscas e visualização de resultados. A busca por referências na interface, o RAG, a interpretação de perguntas de acompanhamento e a hospedagem pública **ainda não foram implementados** nesta etapa.

## 1. Objetivo da etapa

Queremos uma aplicação que seja, ao mesmo tempo:

- **útil:** a busca já existente precisa continuar funcionando;
- **compreensível:** cada parte do código deve ter uma responsabilidade fácil de explicar;
- **sóbria e autoral:** inspirada na organização direta do 1001 Albums Generator e na personalidade de sites pessoais, sem copiar gráficos ou códigos de terceiros;
- **evolutiva:** o futuro RAG não deve exigir reescrever a interface inteira.

Uma distinção importante: **interface de busca com histórico** não é o mesmo que **chat conversacional com memória**. Hoje, cada mensagem abre uma nova busca semântica independente. Um LLM com gerenciamento de contexto poderá ser integrado posteriormente.

## 2. Mapa dos arquivos

```text
app.py                                  # composição da página e interação
.streamlit/config.toml                 # cores e estilos nativos do Streamlit
src/bookmatch/ui/__init__.py           # identifica o pacote de UI
src/bookmatch/ui/components.py         # componentes visuais reutilizáveis
src/bookmatch/ui/styles.css             # ajustes visuais estáticos
src/bookmatch/retrieval/retriever.py   # mecanismo de busca já existente

tests/unit/test_ui_components.py       # testes de funções auxiliares
```

Observe o princípio: **a interface chama o recuperador, mas o recuperador não importa Streamlit**. Assim, continuamos podendo usar a recuperação em scripts, experimentos, notebooks ou em uma futura API HTTP.

## 3. O que o Streamlit realmente faz?

Streamlit é um framework Python que executa um script e produz elementos de interface no navegador. Exemplos:

```python
st.title("Uma biblioteca")          # título
st.caption("Protótipo")            # texto secundário
st.write("Olá!")                  # texto ou conteúdo
st.button("Limpar")                # botão interativo
st.chat_input("Sua busca...")     # entrada de texto em formato de chat
```

Você não escreve manualmente o HTML de cada componente. O Streamlit faz a renderização dos widgets. Para uma aplicação que demonstra pipelines de ML, isso reduz a quantidade de frontend que precisamos manter.

### 3.1. O ciclo de execução (*rerun*)

Em geral, a cada interação relevante, o Streamlit **executa o arquivo Python de cima para baixo novamente**.

Exemplo mental:

```text
Usuário abre a página
  ↓
Executa app.py
  ↓
Renderiza título, resultados e campo de busca
  ↓
Usuário envia uma mensagem
  ↓
Executa app.py de novo
  ↓
A mensagem é processada e os resultados aparecem
```

O script não precisa ficar em um `while True` aguardando eventos. O próprio framework coordena as interações.

**No código:** localize `main()` e o bloco final `if __name__ == "__main__": main()`.

**Experimento:** adicione temporariamente `print("Executando main()")` no início de `main()`. Abra o terminal do Streamlit e observe o que acontece quando você envia uma busca. Remova o `print` depois.

## 4. Por que usamos `st.session_state`?

Quando o script reexecuta, variáveis comuns são recriadas. Se fizéssemos apenas:

```python
history = []
```

o histórico seria reiniciado a cada execução.

Em `initialize_session()` usamos:

```python
if "search_history" not in st.session_state:
    st.session_state.search_history = []
```

Esse objeto pertence à **sessão** e é preservado entre reruns da mesma conexão. Quando a pessoa envia uma consulta, `run_search()` acrescenta `{"query": ..., "books": ...}` ao histórico. A aplicação lê esse estado para redesenhar as buscas anteriores.

A função `clear_history()` limpa **somente o histórico**, não o modelo de embeddings. `on_click=clear_history` registra uma função para ser chamada no clique; não devemos usar `on_click=clear_history()`, porque isso a executaria durante a renderização.

O histórico é limitado a 10 buscas (`MAX_HISTORY`) para não acumular dados indefinidamente. Não há persistência em banco de dados: a sessão pode ser perdida ao recarregar ou desconectar.

### Mini exercício

Localize a linha que contém `MAX_HISTORY = 10`. Altere para `3`, faça quatro buscas e observe quais permanecem. Depois restaure o valor.

## 5. Por que `st.cache_resource`?

`SemanticRetriever` precisa carregar o catálogo, o índice e o E5. Repetir isso a cada mensagem tornaria a interface lenta.

```python
@st.cache_resource(show_spinner="Carregando o catálogo e o modelo semântico...")
def load_retriever() -> SemanticRetriever:
    return SemanticRetriever(...)
```

O decorador permite reutilizar o recurso carregado em execuções posteriores.

**Diferença fundamental:**

| Mecanismo | Armazena | Compartilhamento esperado |
|---|---|---|
| `st.session_state` | histórico e estado de interação | por sessão |
| `st.cache_resource` | objetos pesados: modelos e conexões | normalmente entre execuções e sessões |

O cache global exige cuidado com **concorrência e mutabilidade**: objetos compartilhados devem ser seguros para chamadas de usuários diferentes. No protótipo local, reutilizamos o recuperador sem modificar seu índice durante buscas. Essa decisão precisa ser reavaliada ao publicar em múltiplos usuários.

**Armadilha:** se reconstruir o arquivo `.npz` enquanto o Streamlit está aberto, o objeto antigo poderá continuar em cache. Reinicie a aplicação ou limpe o cache antes de avaliar o novo índice.

## 6. Fluxo de uma consulta

Leia a função `run_search()` no `app.py` e siga os dados:

```text
st.chat_input()
    ↓ texto fornecido pelo usuário
run_search(query)
    ↓ normalização básica
load_retriever().search(query, top_k=5)
    ↓ lista de dicionários recuperados
st.session_state.search_history.append(...)
    ↓
st.rerun()
    ↓
display_books(...) para cada busca
```

Observe o que **não** acontece: `run_search()` não constrói embeddings manualmente, não faz chamadas à Apple Books e não conversa com um LLM. Essas responsabilidades pertencem a outros componentes.

### Por que chamar `st.rerun()`?

Depois de acrescentar o resultado ao histórico, `st.rerun()` pede uma nova execução imediatamente. A nova renderização encontra o histórico atualizado e exibe os resultados. Poderíamos organizar o fluxo de outras formas, mas aqui o rerun torna a atualização explícita.

### E os erros?

A função verifica se existem o catálogo e o índice antes de tentar procurar. Em caso de erro de busca, apresenta uma mensagem amigável e um detalhe técnico. Ela **não** simula resultados nem inventa livros.

## 7. Layout com componentes nativos

O arquivo `components.py` não sabe como recuperar os livros. Ele recebe dados e os apresenta.

### `st.columns()`

Usamos duas colunas no cabeçalho:

```python
brand_col, github_col = st.columns([4, 1])
```

O parâmetro `[4, 1]` determina uma **proporção de espaço**, não pixels fixos. Isso permite uma marca mais larga e um link menor para o repositório.

### `st.container()`

Agrupa título, autoria, sinopse e link de cada obra. Não colocamos borda de cartão: preferimos divisórias (`st.divider()`) e tipografia para obter um aspecto editorial.

### `st.expander()`

Sinopses longas não precisam ocupar toda a página imediatamente. O usuário abre a descrição quando quiser. Isso mantém o catálogo escaneável.

### `st.link_button()`

Utiliza `source_url` vindo do recuperador **somente se existir uma URL HTTP(S) com domínio**. O link é para a página informada na fonte; não presumimos que seja compra ou leitura gratuita.

O helper `_valid_source_url()` não garante que a página exista ou seja apropriada: apenas evita protocolos que não devem virar links na interface.

## 8. Responsabilidade de cada módulo

| Arquivo / função | Sabe sobre Streamlit? | Sabe executar a busca? |
|---|---:|---:|
| `app.py / run_search()` | sim | coordena chamada ao recuperador |
| `components.py / display_books()` | sim | não |
| `retriever.py / SemanticRetriever` | não | sim |
| `styles.css` | não (somente CSS) | não |

Essa separação simplifica os testes e permite que o projeto cresça sem transformar `app.py` em um arquivo de centenas de linhas.

**Pergunta para revisão:** por que `display_books()` recebe `books` em vez de acessar diretamente `st.session_state`? Resposta: essa função se torna mais reutilizável e mais simples de compreender; seu dado de entrada é explícito.

## 9. Identidade visual: tema e CSS

A direção visual é **biblioteca editorial independente**:

- fundo creme, texto escuro e contraste confortável;
- tipografia serifada nos títulos e sem serifa nos controles;
- cor ameixa discreta, em vez de botões chamativos;
- poucos elementos decorativos; foco nas obras e nas sinopses.

### 9.1. `.streamlit/config.toml`

O Streamlit lê configurações de aparência do arquivo na pasta `.streamlit` da raiz do projeto. Lá estão as cores e características dos widgets.

```toml
[theme]
base = "light"
primaryColor = "#725D70"
backgroundColor = "#F6F2EB"
secondaryBackgroundColor = "#ECE5DA"
textColor = "#302A27"
```

Ao estudar o arquivo, tente identificar que propriedade altera o fundo principal e qual altera o texto. Para mudanças de tema, normalmente é mais fácil reiniciar a aplicação.

### 9.2. `styles.css`

O CSS contém apenas nossas próprias classes `.bm-*`: marca, texto de seção e rodapé. Não usamos seletores internos do Streamlit como `[data-testid=...]`, que podem mudar em atualizações.

`apply_styles()` lê um CSS **estático pertencente ao projeto** e o injeta na página. `unsafe_allow_html=True` é usado somente para HTML/CSS escrito por nós: nunca interpolamos título, autor, descrição ou consulta de usuário nesse HTML.

**Exercício:** altere apenas `letter-spacing` de `.bm-eyebrow`. Observe o efeito visual. Depois, teste outra cor para `primaryColor` no tema.

## 10. Dados externos, segurança e limitações

O catálogo recebe descrições de fontes externas. Por isso:

1. Apresentamos título, autoria e descrição com componentes normais (`st.subheader`, `st.write`), sem habilitar HTML arbitrário para conteúdo externo.
2. Verificamos o esquema da URL antes de criar o botão, mas isso não equivale à verificação da página de destino.
3. O ranking é apresentado como **resultados de busca**, não como recomendações literárias comprovadas.
4. Não enviamos automaticamente o catálogo ao GitHub: precisamos preservar a revisão de procedência e dos direitos de uso.
5. Esta interface ainda não implementa a seleção de referências da Apple Books nem respostas geradas por LLM.

## 11. Como executar e depurar

Na raiz do repositório, com o `.venv` ativado:

```bash
python -m streamlit run app.py
```

Verifique se os arquivos locais `data/processed/catalog_v0.csv` e `data/processed/semantic_index_e5.npz` existem, pois o app os utiliza ao pesquisar.

Para testar os auxiliares da UI:

```bash
python -m pytest tests/unit/test_ui_components.py -v
```

Para conferir regressões em todo o projeto:

```bash
python -m pytest tests/ -v
```

Se `from bookmatch.ui.components import ...` falhar, confira se a pasta foi copiada para `src/bookmatch/ui/` e se a instalação editável do pacote está atualizada (`python -m pip install -e .`).

**Dependência:** como o código passa a usar `streamlit` em `app.py` e `components.py`, registre-o na lista de dependências da aplicação em `pyproject.toml`. Não substitua o arquivo existente apenas para adicionar esse pacote.

## 12. Roteiro de revisão (para explicar o código em uma entrevista)

Tente responder sem consultar a explicação:

1. Por que o Streamlit executa o script várias vezes?
2. O que seria perdido sem `st.session_state`?
3. Por que o E5 fica em `st.cache_resource`, e não em `st.session_state`?
4. Qual é a responsabilidade do `app.py` e qual é a de `components.py`?
5. Qual dado é usado para abrir a página de um livro? O LLM o inventa?
6. Por que esta versão é uma **interface de busca**, mesmo usando `st.chat_input`?
7. Onde devemos adicionar uma futura função que selecione livros na Apple Books?
8. O que impede a hospedagem imediata da versão local no Streamlit Community Cloud?

### Respostas esperadas, em linhas gerais

1. Interações acionam *reruns*, e a interface é descrita pelo script Python.
2. O histórico deixaria de sobreviver às execuções.
3. É um recurso pesado reutilizável; cache e estado de usuário têm funções diferentes. É preciso considerar segurança de acesso concorrente.
4. `app.py` coordena, `components.py` apresenta dados.
5. `source_url` do catálogo, quando disponível e com formato aceitável.
6. Cada mensagem inicia uma consulta independente; ainda não há memória conversacional de LLM.
7. A API fica em `integrations/`, a construção dos vetores em `recommendation/`; `app.py` apenas conecta essas partes à UI.
8. O acervo/índice não estão disponíveis no servidor público e sua reutilização ainda precisa ser revisada; além disso, faltam decisões de implantação.

## 13. Próximos passos, fora do escopo deste pacote

- Seleção explícita de até três livros de referência na interface, com confirmação da edição escolhida.
- Estruturação do fluxo de respostas RAG e validação de `book_id`.
- Área editorial “Recomendações” e “Explore também”, quando houver LLM e candidatos validados.
- Testes de interface mais abrangentes (por exemplo, com `streamlit.testing.v1.AppTest`).
- Planejamento da hospedagem, disponibilização segura dos artefatos e limites de recursos.

## Referências para aprofundar

- [Fundamentos do Streamlit](https://docs.streamlit.io/get-started/fundamentals/main-concepts)
- [Estado de sessão](https://docs.streamlit.io/develop/concepts/architecture/session-state)
- [Cache de recursos](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource)
- [Componentes de layout](https://docs.streamlit.io/develop/api-reference/layout/st.container)
- [Tema e configuração](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)
- [Chat input](https://docs.streamlit.io/develop/api-reference/chat/st.chat_input)

---

**Critério de conclusão desta aula:** você consegue explicar como uma mensagem chega ao recuperador, por que o histórico não desaparece após o rerun e como uma alteração visual pode ser feita sem modificar o algoritmo de busca.
