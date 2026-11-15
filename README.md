# O Que Ler em Português?

O Que Ler em Português? é um projeto de descoberta literária que utiliza recuperação semântica e modelos de linguagem para recomendar livros originalmente escritos em português.

A aplicação permite buscar obras a partir de uma descrição em linguagem natural ou de livros de referência. Em ambos os casos, a recuperação é realizada sobre um catálogo literário construído e preparado durante o desenvolvimento do projeto.

O projeto também explora o uso de Retrieval-Augmented Generation (RAG) para produzir recomendações fundamentadas nas informações recuperadas, em vez de depender apenas do conhecimento do modelo de linguagem.

O sistema ainda está em desenvolvimento, principalmente no que diz respeito à qualidade do catálogo e à avaliação das recomendações.

## Construção do catálogo

O desenvolvimento começou pela construção de uma base de dados literária. Como a proposta é recuperar livros a partir de temas, gêneros e características narrativas, não seria suficiente utilizar apenas títulos e autores.

O ponto de partida foi um levantamento de obras relacionadas ao Prêmio Oceanos. Os registros passaram por etapas de padronização, identificação de duplicatas e enriquecimento de metadados.

As descrições literárias foram obtidas principalmente por meio da Apple Books e de páginas de editoras. Outras fontes, como Skoob e Wikipédia, também foram investigadas durante o desenvolvimento.

A versão experimental do catálogo contém:

- 469 obras de 390 autores;
- 334 descrições obtidas da Apple Books;
- 135 descrições obtidas de páginas de editoras;
- obras distribuídas entre romance, conto, poesia, crônica e dramaturgia.

Os registros também preservam informações de proveniência, como a fonte utilizada e o método de obtenção dos dados.

A preparação e a investigação das fontes estão documentadas em `docs/data/`, `experiments/data_sources/` e `scripts/`.

O catálogo é armazenado localmente em `data/processed/catalog_v0.csv`. Sua leitura é realizada pelo módulo `bookmatch.data.loader`, responsável por validar a estrutura dos registros.

Os dados processados não são distribuídos publicamente neste momento, pois a revisão das condições de reutilização de algumas descrições ainda não foi concluída.

## Recuperação semântica

O projeto utiliza o modelo pré-treinado `intfloat/multilingual-e5-small`, da biblioteca Sentence Transformers, para representar os livros e as consultas como embeddings.

Cada obra é representada por um texto construído a partir de seus metadados, incluindo título, gênero e descrição.

Durante a indexação, os textos recebem o prefixo `passage:`, conforme a convenção de uso do E5. O script `scripts/build_embeddings.py` gera embeddings normalizados de 384 dimensões e os armazena em um arquivo NumPy (`.npz`).

Na busca, a consulta recebe o prefixo `query:` e é transformada em um embedding pelo mesmo modelo. A similaridade é calculada por produto escalar entre os vetores normalizados, e os resultados são ordenados pela proximidade com a consulta.

O `SemanticRetriever`, em `src/bookmatch/retrieval/retriever.py`, reúne essas operações e permite realizar buscas por texto ou diretamente por vetor.

O índice é construído previamente, evitando recalcular os embeddings de todos os livros durante as consultas.

A relevância dos resultados ainda não foi avaliada sistematicamente com consultas e julgamentos de relevância específicos para o catálogo literário.

## Modos de busca

A interface Streamlit oferece dois modos de descoberta.

### Busca por preferências

O usuário descreve o tipo de livro que deseja encontrar, utilizando linguagem natural.

Por exemplo:

> Um romance sobre memórias de família, com uma atmosfera melancólica e personagens complexos.

A descrição é transformada em um embedding e utilizada para recuperar as obras mais próximas no catálogo.

A busca não depende exclusivamente da presença das mesmas palavras na descrição dos livros, embora a qualidade dos resultados ainda dependa das informações disponíveis sobre cada obra.

### Busca por livros de referência

Também é possível procurar livros a partir de obras que o usuário já conhece.

A interface utiliza a Apple Books para pesquisar livros e apresentar possíveis correspondências. O usuário seleciona de uma a três referências.

As descrições dessas obras são utilizadas para construir representações semânticas, posteriormente combinadas em uma consulta ao índice local.

Isso permite utilizar livros externos ao catálogo, inclusive escritos em outros idiomas, para buscar obras com características semelhantes.

Os resultados da Apple Books passam por uma filtragem que exige identificador, título e descrição utilizável. A seleção da edição correta continua sendo responsabilidade do usuário.

A implementação está concentrada nos módulos:

- `bookmatch.integrations.apple_books`;
- `bookmatch.recommendation.query_builder`;
- `bookmatch.recommendation.reference_search`.

Os dois modos utilizam o mesmo índice semântico para recuperar obras do catálogo.

## Geração de recomendações com RAG

Além da recuperação semântica, o projeto possui um pipeline RAG que utiliza um modelo de linguagem para gerar recomendações a partir dos livros encontrados.

O fluxo separa a recuperação da geração. Primeiro, o sistema identifica as obras mais próximas da consulta. Depois, organiza os dados recuperados em um contexto enviado ao LLM.

Os componentes estão em `src/bookmatch/rag/`:

- `context_builder.py`: preparação das informações recuperadas;
- `prompts.py`: instruções utilizadas na geração;
- `llm.py`: integração com o modelo de linguagem;
- `schemas.py`: estrutura das respostas;
- `pipeline.py`: integração dos componentes.

A geração utiliza Gemini por meio da integração com LangChain e uma estrutura de resposta definida com Pydantic.

As recomendações devem se limitar aos livros recuperados e às características efetivamente disponíveis no catálogo.

Entretanto, a utilização de RAG não elimina a possibilidade de afirmações incorretas. Descrições incompletas ou pouco informativas podem dificultar a identificação de semelhanças e comprometer as justificativas geradas.

A qualidade das recomendações ainda precisa ser avaliada experimentalmente.

## Interface

A aplicação utiliza Streamlit e reúne os dois modos de busca em uma interface de descoberta literária.

A interface permite pesquisar obras por preferências ou livros de referência, visualizar os resultados recuperados e utilizar o pipeline de geração de recomendações.

O código principal está em `app.py`, enquanto os componentes visuais reutilizáveis ficam em `src/bookmatch/ui/`.

O modelo e o índice são carregados com cache para evitar reinicializações desnecessárias durante as interações.

As decisões relacionadas à interface e à busca por referências também estão registradas em `docs/learning/`.

## Tecnologias

- Python
- Pandas e NumPy
- Sentence Transformers
- `intfloat/multilingual-e5-small`
- Gemini API e LangChain
- Pydantic
- Streamlit
- Pytest

## Organização do projeto

```text
bookmatch/
├── app.py
├── data/
├── docs/
│   ├── data/
│   └── learning/
├── experiments/
├── notebooks/
├── scripts/
├── src/
│   └── bookmatch/
│       ├── catalog/
│       ├── data/
│       ├── integrations/
│       ├── rag/
│       ├── recommendation/
│       ├── retrieval/
│       └── ui/
├── tests/
└── pyproject.toml
```

O projeto separa a preparação dos dados, a recuperação, a geração de recomendações e a interface.

Os notebooks e documentos são utilizados principalmente para exploração de dados e registro do aprendizado, enquanto a implementação principal está organizada em módulos Python.

## Como executar

O projeto utiliza Python 3.10 ou superior.

Para preparar o ambiente:

```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -e ".[dev]"
```

Para executar os testes:

```bash
python -m pytest -v
```

A aplicação depende do catálogo preparado e do índice semântico, que devem estar disponíveis em:

```text
data/processed/catalog_v0.csv
data/processed/semantic_index_e5.npz
```

Com o catálogo disponível, o índice pode ser gerado por:

```bash
python scripts/build_embeddings.py
```

Para utilizar a geração com Gemini, é necessário configurar uma chave de API:

```bash
read -r -s -p "Gemini API key: " GEMINI_API_KEY
echo
export GEMINI_API_KEY
```

Depois, a interface pode ser iniciada com:

```bash
python -m streamlit run app.py
```

Os dados processados não estão incluídos no repositório público. Portanto, a execução completa depende da disponibilidade de uma cópia local do catálogo.

## Testes e avaliação

O projeto possui testes automatizados para componentes de recuperação, construção do contexto, integração do pipeline e interface.

Parte dos testes utiliza componentes simulados para verificar o comportamento do código sem depender de chamadas reais ao Gemini.

A recuperação semântica já foi testada durante o desenvolvimento, mas ainda não existe uma avaliação quantitativa completa das recomendações literárias.

A avaliação futura deverá considerar tanto a relevância dos livros recuperados quanto a qualidade das justificativas produzidas pelo LLM.

## Limitações e próximos passos

A principal limitação do projeto está relacionada à cobertura e à diversidade do catálogo. A base foi construída a partir de obras relacionadas ao Prêmio Oceanos, que possui um recorte literário específico e não representa toda a variedade de livros originalmente escritos em português.

Durante os testes exploratórios de uso, essa limitação ficou evidente em buscas por livros com características diferentes das obras presentes no catálogo. Nesses casos, os resultados recuperados nem sempre correspondiam às preferências informadas, mesmo quando a busca semântica funcionava corretamente.

Isso também afeta a geração com RAG, já que o modelo de linguagem depende das obras recuperadas para produzir suas recomendações. Quando o catálogo não contém livros suficientemente relacionados à consulta, a qualidade das recomendações e de suas justificativas fica comprometida.

Além disso, as descrições literárias disponíveis variam em quantidade e qualidade, e ainda não foi realizada uma avaliação experimental sistemática da relevância das recomendações.

Como próximos passos, estão previstos a ampliação e a diversificação do catálogo, priorizando obras de autores brasileiros, a construção de um conjunto de avaliação para recuperação e recomendação e a comparação entre diferentes estratégias de busca. Também poderão ser investigadas melhorias nos embeddings e na geração das justificativas.
