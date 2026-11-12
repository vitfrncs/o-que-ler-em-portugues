# O Que Ler em Português?

O Que Ler em Português? é uma aplicação de descoberta de livros originalmente escritos em língua portuguesa. A ideia é ajudar pessoas a encontrar novas leituras a partir de temas, gêneros e características de histórias de que gostam, aproximando obras de diferentes países que compartilham a língua.

A aplicação combina recuperação de informação e processamento de linguagem natural. A busca semântica utiliza embeddings de descrições literárias para identificar livros relacionados a uma consulta, mesmo quando não há correspondência exata entre as palavras. A próxima etapa é integrar essa recuperação a um pipeline de *Retrieval-Augmented Generation* (RAG), no qual um modelo de linguagem produzirá recomendações fundamentadas nas informações recuperadas do catálogo.

O desenvolvimento começou pela construção do catálogo literário. Como a busca precisa considerar mais do que títulos e autores, foi necessário reunir descrições, verificar correspondências entre fontes e preparar os registros para a indexação semântica.

## Construção do catálogo

O ponto de partida foi um levantamento de obras relacionadas ao Prêmio Oceanos, utilizado como referência bibliográfica para a seleção inicial. O objetivo não era apenas reunir títulos, mas construir uma base com metadados suficientes para buscar livros por características de suas histórias.

A preparação dos dados envolveu padronização de títulos e autores, organização dos gêneros, identificação de duplicatas e investigação de registros incompletos. Para enriquecer os dados, foram exploradas diferentes fontes, incluindo a Apple Books e páginas de editoras. Também foram realizados levantamentos e testes com outras fontes, como Skoob e Wikipédia, documentados no repositório.

Como uma mesma obra pode aparecer com títulos, edições e metadados diferentes, o enriquecimento exigiu verificar as correspondências encontradas antes de incorporar as descrições. O catálogo preserva informações de proveniência, como fonte, URL e método de extração, além de campos que ajudam a identificar o estado de revisão de cada registro.

A versão experimental utilizada atualmente contém 469 obras de 390 autores, distribuídas entre romance, conto, poesia, crônica e dramaturgia. Das descrições reunidas, 334 vieram da Apple Books e 135 de páginas de editoras.

Os dados processados são armazenados localmente em `data/processed/catalog_v0.csv`. A leitura é feita por `load_catalog()`, em `src/bookmatch/data/loader.py`, que verifica colunas obrigatórias, campos ausentes ou vazios e identificadores duplicados. O processo de construção e análise dos dados está registrado em `docs/data/`, `experiments/data_sources/` e `scripts/`.

O catálogo ainda possui limitações. A verificação de quais obras foram originalmente escritas em português e a revisão das condições de reutilização de algumas descrições não estão concluídas. Por esse motivo, os arquivos completos de dados não são distribuídos publicamente neste momento.

## Recuperação semântica

A primeira implementação de recuperação utiliza o modelo pré-treinado `intfloat/multilingual-e5-small`, por meio da biblioteca Sentence Transformers. Cada livro é representado por um texto composto de título, gênero e descrição, preparado pela função `build_book_text()` em `src/bookmatch/retrieval/semantic.py`.

Na indexação, os textos recebem o prefixo `passage:`, conforme a convenção de uso do E5. O script `scripts/build_embeddings.py` processa os livros em lotes, gera vetores normalizados de 384 dimensões e os salva em um arquivo NumPy `.npz`, junto aos respectivos `book_id` e ao nome do modelo. O índice é gerado previamente para que a aplicação não precise recalcular todos os embeddings a cada consulta.

A recuperação segue o mesmo princípio: o texto enviado pelo usuário recebe o prefixo `query:` e é transformado em um embedding pelo mesmo modelo. Como os vetores são normalizados, a similaridade de cosseno pode ser calculada pelo produto escalar entre o vetor da consulta e a matriz de embeddings. Em seguida, os resultados são ordenados por pontuação e associados aos livros do catálogo por seus identificadores.

As funções `compute_similarities()` e `get_top_k_indices()` já foram implementadas e testadas, e o fluxo de busca foi executado manualmente com livros reais. A integração dessas etapas em um componente `SemanticRetriever`, reutilizável pela aplicação, ainda está em desenvolvimento.

Durante os testes, identificou-se uma limitação da primeira abordagem: 423 dos 469 textos (90,2%) ultrapassavam o limite de 128 tokens do modelo inicialmente utilizado. Isso motivou a adoção do Multilingual E5 Small e a reconstrução do índice. A recuperação já funciona experimentalmente, mas a relevância dos resultados ainda não foi medida com um conjunto formal de avaliação.

## Aplicação e arquitetura prevista

A aplicação terá dois modos de descoberta. No primeiro, a pessoa descreve o que deseja ler, indicando temas, gêneros ou características narrativas. Essa descrição será transformada em uma consulta semântica ao catálogo.

No segundo, será possível selecionar até três livros de referência, inclusive obras escritas em outros idiomas. A integração prevista com a Apple Books permitirá localizar essas obras e obter os metadados disponíveis. Os textos das referências serão convertidos em embeddings e combinados para formar uma representação da preferência do usuário. O usuário também poderá informar quais características desses livros deseja encontrar em outra leitura. A agregação dos vetores será uma estratégia inicial, sujeita a ajustes conforme os testes.

Os dois modos compartilharão o mesmo recuperador semântico. Os livros mais próximos serão enviados a um componente responsável por organizar o contexto do RAG. Um LLM receberá a consulta e os metadados recuperados para gerar sugestões acompanhadas de justificativas. A resposta deverá mencionar apenas obras presentes no catálogo e evitar atribuir a elas características que não estejam sustentadas pelos dados.

A interface será desenvolvida com Streamlit, priorizando uma experiência simples de descoberta literária. A integração com a Apple Books, o pipeline RAG, a geração das respostas e a interface ainda não estão implementados.

O fluxo pretendido é:

```text
Descrição livre ────────────────────────┐
                                        ├─> Consulta semântica ─> Busca no catálogo
Até 3 livros ─> Apple Books ─> Vetores ┘                         │
                                                                  v
                                                       Livros recuperados
                                                                  │
                                                                  v
                                                        Contexto RAG + LLM
                                                                  │
                                                                  v
                                                       Recomendações no chat
```

## Organização e execução

O código principal está em `src/bookmatch/`, separado em módulos de dados, recuperação, recomendação, RAG e integração com modelos de linguagem. Os scripts de preparação e indexação ficam em `scripts/`, os testes automatizados em `tests/` e a documentação em `docs/`. Parte dessa estrutura já existe para acomodar as próximas etapas, mas nem todos os módulos estão implementados.

O projeto utiliza Python 3.10 ou superior. Para configurar o ambiente e executar os testes:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -v
```

Com o catálogo disponível localmente em `data/processed/catalog_v0.csv`, o índice semântico pode ser gerado com:

```bash
python scripts/build_embeddings.py
```

A geração do índice depende dos dados locais, que ainda não são redistribuídos. A execução completa da aplicação conversacional dependerá das integrações que estão em desenvolvimento.

## Próximos passos

As próximas etapas são concluir o recuperador semântico, implementar a busca por livros de referência, conectar o RAG a um modelo de linguagem e desenvolver a interface. Depois, o projeto poderá incorporar uma avaliação sistemática das recomendações, comparação com BM25 e experimentos de ajuste dos embeddings.
