# Data Card — Catálogo Literário do BookMatch

**Projeto:** BookMatch  
**Dataset:** Catálogo literário enriquecido  
**Versão:** Experimental v0  
**Data da análise:** 05/11/2026  
**Arquivo analisado:** `catalog_experimental.csv`  
**Formato:** CSV  
**Idioma predominante esperado:** Português  
**Domínio:** Literatura em língua portuguesa  
**Status:** Corpus experimental, pendente de revisão qualitativa e de direitos de reutilização

## 1. Visão geral

O catálogo literário do BookMatch AI é um conjunto de dados bibliográficos enriquecido com descrições textuais, desenvolvido para apoiar experimentos de recuperação de informação e geração aumentada por recuperação (*Retrieval-Augmented Generation*, RAG).

O dataset foi construído a partir dos metadados bibliográficos do Prêmio Oceanos, complementados com descrições recuperadas de fontes externas.

O catálogo contempla cinco gêneros literários: Romance, Conto, Poesia, Crônica e Dramaturgia.

A versão analisada contém **469 registros**, todos com descrições preenchidas e aprovadas pelos critérios de triagem automática implementados no pipeline.

O conjunto constitui um corpus experimental e não representa uma seleção definitiva ou integralmente validada das obras.

## 2. Objetivo e aplicações

O dataset foi desenvolvido para permitir a implementação e a avaliação de componentes de Engenharia de IA associados à descoberta de literatura.

### 2.1. Aplicações previstas

- Recuperação lexical de livros utilizando BM25.
- Recuperação semântica utilizando representações vetoriais (*embeddings*).
- Comparação experimental entre métodos de recuperação.
- Desenvolvimento de estratégias híbridas de recuperação.
- Construção de um sistema RAG para recomendação literária.
- Avaliação da relevância e da fundamentação das recomendações.
- Investigação dos efeitos da qualidade dos dados no desempenho da recuperação.

### 2.2. Usos não previstos

O dataset não foi desenvolvido para:

- Representar de maneira exaustiva a literatura em língua portuguesa.
- Estabelecer avaliações objetivas de qualidade literária.
- Produzir rankings de popularidade ou importância cultural.
- Verificar automaticamente informações biográficas dos autores.
- Servir como fonte autorizada para redistribuição pública das descrições.

A utilização dos dados deve considerar as limitações de cobertura e os critérios de seleção aplicados.

## 3. Origem dos dados

### 3.1. Metadados bibliográficos

A fonte principal dos metadados é o conjunto de dados do Prêmio Oceanos.

Entre as informações utilizadas estão:

- Título da obra.
- Nome do autor.
- Gênero literário.
- Ano de inscrição.
- Editora.
- Site da editora.
- Indicadores de premiação.

O conjunto original não disponibiliza descrições textuais das obras.

### 3.2. Fontes de enriquecimento

As descrições foram recuperadas por meio de um pipeline automatizado que integra fontes bibliográficas externas.

Na versão analisada, os registros aceitos apresentam descrições provenientes de:

| Fonte | Registros | Participação |
|---|---:|---:|
| Apple Books | 334 | 71,2% |
| Sites editoriais | 135 | 28,8% |
| **Total** | **469** | **100%** |

O Google Books também integra a arquitetura de enriquecimento como fonte opcional, mas não aparece como origem de descrições aceitas no snapshot analisado.

A ausência de registros dessa fonte não permite determinar, isoladamente, sua taxa de sucesso ou disponibilidade.

## 4. Processo de construção

A construção do catálogo foi realizada pelo pipeline:

`scripts/enrich_oceanos_auto.py`

O processo contempla:

1. Leitura dos metadados do Oceanos.
2. Normalização dos campos bibliográficos.
3. Seleção e deduplicação de obras.
4. Consolidação dos sites editoriais.
5. Consulta às fontes externas.
6. Extração e limpeza das descrições.
7. Verificação de correspondências entre títulos e autores.
8. Aplicação de critérios heurísticos de qualidade textual.
9. Registro da procedência.
10. Persistência dos resultados e das informações de auditoria.

A metodologia completa está descrita em `docs/data/02-pipeline-atual.md`.

## 5. Estrutura do dataset

O arquivo contém **11 colunas**.

| Coluna | Tipo | Descrição |
|---|---|---|
| `book_id` | String | Identificador determinístico da obra |
| `title` | String | Título bibliográfico |
| `authors` | String | Nome do autor registrado |
| `genre` | String | Gênero literário |
| `description` | String | Texto recuperado para representar a obra |
| `source` | String | Fonte da descrição |
| `source_url` | String | URL de referência da fonte |
| `extraction_method` | String | Método utilizado para recuperar o texto |
| `quality_status` | String | Resultado da triagem textual |
| `match_status` | String | Resultado da verificação bibliográfica |
| `usage_status` | String | Situação da análise de direitos de reutilização |

O identificador `book_id` é construído a partir de título e autoria normalizados.

Ele não corresponde a um ISBN e não representa necessariamente uma edição bibliográfica específica.

## 6. Composição do catálogo

### 6.1. Estatísticas gerais

| Indicador | Resultado |
|---|---:|
| Registros | 469 |
| Identificadores únicos | 469 |
| Títulos distintos | 469 |
| Nomes de autores distintos | 390 |
| Gêneros literários | 5 |
| Campos de descrição preenchidos | 469 |
| Descrições exatamente duplicadas | 0 |
| Registros com valores ausentes | 0 |

A contagem de autores considera os nomes presentes no arquivo, sem uma etapa adicional de identificação de pessoas.

A ausência de duplicatas exatas não elimina a possibilidade de descrições semanticamente semelhantes ou obras equivalentes registradas sob títulos diferentes.

### 6.2. Distribuição por gênero

| Gênero | Registros | Participação |
|---|---:|---:|
| Romance | 204 | 43,5% |
| Conto | 87 | 18,6% |
| Poesia | 84 | 17,9% |
| Crônica | 72 | 15,4% |
| Dramaturgia | 22 | 4,7% |
| **Total** | **469** | **100%** |

A distribuição demonstra predominância de romances.

Dramaturgia apresenta a menor quantidade de registros, correspondendo a aproximadamente 4,7% do corpus.

A versão analisada não apresenta uma distribuição equilibrada entre os cinco gêneros.

### 6.3. Distribuição das fontes por gênero

| Gênero | Apple Books | Editoras | Total |
|---|---:|---:|---:|
| Romance | 183 | 21 | 204 |
| Conto | 53 | 34 | 87 |
| Poesia | 40 | 44 | 84 |
| Crônica | 47 | 25 | 72 |
| Dramaturgia | 11 | 11 | 22 |
| **Total** | **334** | **135** | **469** |

A contribuição das fontes varia conforme o gênero.

A Apple Books representa a principal origem das descrições de romances, enquanto as páginas editoriais apresentam participação relevante nos registros de poesia e dramaturgia.

Essas diferenças caracterizam a composição do corpus aceito, não necessariamente a cobertura geral das fontes.

## 7. Características textuais

### 7.1. Comprimento das descrições

| Indicador | Caracteres |
|---|---:|
| Mínimo | 181 |
| Média | 1.056 |
| Mediana | 924 |
| Primeiro quartil | 623 |
| Terceiro quartil | 1.332 |
| Máximo | 3.618 |

As descrições possuem comprimentos variados, refletindo diferenças entre fontes e formas de apresentação dos livros.

A quantidade de caracteres não constitui, isoladamente, uma medida de qualidade ou relevância semântica.

### 7.2. Métodos de extração

| Método | Registros |
|---|---:|
| `apple_api` | 334 |
| `json_ld` | 97 |
| `og_description` | 16 |
| `html_woocommerce` | 15 |
| `html_itemprop` | 6 |
| `html_tab_description` | 1 |
| **Total** | **469** |

Os resultados demonstram a utilização de diferentes representações de conteúdo durante o enriquecimento.

O método empregado é preservado para permitir a análise de procedência e a investigação de problemas específicos de extração.

### 7.3. Idioma

O projeto tem como escopo obras de literatura em língua portuguesa.

Entretanto, a versão analisada contém descrições em espanhol associadas a determinadas obras.

Foram identificados exemplos desse problema nos registros de *Galveias* e *Autobiografia*, de José Luís Peixoto.

Não foi realizada uma estimativa quantitativa completa da distribuição de idiomas.

A identificação e a revisão de descrições em outros idiomas permanecem como atividades de melhoria da qualidade do corpus.

## 8. Qualidade dos dados

### 8.1. Verificação automática

Todos os registros presentes no arquivo analisado apresentam:

| Campo | Valor | Registros |
|---|---|---:|
| `quality_status` | `candidate` | 469 |
| `match_status` | `verified` | 469 |
| `usage_status` | `pending_rights_review` | 469 |

A classificação `candidate` indica que a descrição passou pelos critérios heurísticos de qualidade implementados.

A classificação `verified` indica que a correspondência bibliográfica foi aceita segundo as regras automáticas do pipeline.

Esses estados não equivalem à validação humana integral.

### 8.2. Limitações da triagem

Os critérios automáticos não garantem que:

- O texto seja uma sinopse da obra.
- A descrição esteja em português.
- A correspondência bibliográfica esteja correta em todos os casos.
- O conteúdo esteja livre de informações promocionais.
- A descrição seja suficiente para representar adequadamente os temas da obra.
- O conteúdo possa ser redistribuído publicamente.

Portanto, a qualidade do catálogo deverá ser avaliada adicionalmente por meio de revisão amostral.

### 8.3. Duplicatas

O snapshot analisado não apresentou:

- Identificadores `book_id` duplicados.
- Combinações exatas duplicadas de título e autor.
- Descrições textualmente idênticas.

Esses resultados não excluem duplicações aproximadas ou relações entre diferentes edições de uma mesma obra.

## 9. Limitações e possíveis vieses

### 9.1. Desequilíbrio entre gêneros

A quantidade de registros varia significativamente entre os cinco gêneros.

Esse desequilíbrio pode influenciar a composição dos resultados recuperados e a diversidade das recomendações.

A avaliação dos métodos de recuperação deverá considerar a distribuição do corpus.

### 9.2. Viés de disponibilidade digital

O enriquecimento depende da presença de obras em catálogos digitais e sites editoriais.

Livros com maior disponibilidade nesses canais podem apresentar maior probabilidade de inclusão no dataset.

### 9.3. Qualidade heterogênea das descrições

Os textos recuperados podem apresentar diferentes estilos e objetivos comunicativos.

Algumas descrições são predominantemente informativas, enquanto outras possuem características promocionais ou críticas.

Essas diferenças podem afetar as representações utilizadas pelos modelos de recuperação.

### 9.4. Variação linguística

As fontes externas podem disponibilizar descrições em idiomas diferentes do português.

Essa característica exige atenção na preparação do corpus e na interpretação dos resultados de recuperação semântica.

### 9.5. Validação bibliográfica

A correspondência entre registros do Oceanos e resultados externos utiliza regras automáticas.

Embora essas regras reduzam associações incorretas, permanecem possíveis erros e ambiguidades.


## 10. Versionamento e reprodutibilidade

A construção do catálogo utiliza um processo incremental de enriquecimento.

Consequentemente, o conteúdo de `catalog_experimental.csv` pode ser alterado após novas execuções.

Para garantir a reprodutibilidade dos experimentos, recomenda-se manter versões fixas do corpus.

O snapshot analisado em 05/11/2026 possui:

- **Registros:** 469.
- **Colunas:** 11.
- **Formato:** CSV.
- **SHA-256:** `03b9a0105fba5e28298985f3c5b27f901a5bdb061e64a1bf1d2b493e11d668ef`.


## 11. Melhorias previstas

As principais melhorias identificadas para a preparação de versões posteriores são:

1. Validação automática e revisão amostral do idioma das descrições.
2. Identificação de textos promocionais, excertos e descrições pouco informativas.
3. Revisão das correspondências bibliográficas mais suscetíveis a ambiguidades.
4. Investigação do desequilíbrio entre gêneros.
5. Avaliação de duplicatas textuais aproximadas.
6. Verificação das condições de reutilização das descrições.
7. Construção de um conjunto de consultas e julgamentos de relevância para avaliação da recuperação.

Essas atividades não impedem o início dos experimentos de recuperação, desde que as limitações sejam registradas.

## 12. Considerações finais

O catálogo experimental do BookMatch AI reúne 469 registros bibliográficos enriquecidos com descrições textuais e informações de procedência.

A combinação de metadados estruturados do Prêmio Oceanos com fontes externas permitiu construir um corpus inicial para o desenvolvimento dos componentes de recuperação de informação e RAG.

A presença de descrições em todos os registros e a preservação das informações de origem representam características relevantes para a experimentação.

Entretanto, permanecem limitações relacionadas à distribuição dos gêneros, à qualidade textual, à validação bibliográfica e aos direitos de reutilização.

O conjunto deve ser tratado como um corpus experimental versionado, cuja qualidade será investigada nas etapas posteriores do projeto.