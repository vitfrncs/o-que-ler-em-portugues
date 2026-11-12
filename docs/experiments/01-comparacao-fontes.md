# Experimentos de seleção e enriquecimento de fontes bibliográficas

**Projeto:** BookMatch
**Etapa:** Construção do catálogo literário  
**Status:** Documentação retrospectiva  
**Última atualização:** 05/11/2026

## 1. Objetivo

Os experimentos descritos neste documento tiveram como objetivo identificar fontes de dados adequadas à construção de um catálogo de obras literárias em língua portuguesa, destinado à recuperação de informação e à geração aumentada por recuperação (*Retrieval-Augmented Generation*, RAG).

A investigação considerou duas necessidades complementares:

1. Obtenção de metadados bibliográficos estruturados, especialmente títulos, autores e gêneros literários.
2. Disponibilidade de descrições textuais relevantes para representar semanticamente as obras.

Inicialmente, foram avaliados datasets existentes. Posteriormente, foram investigadas APIs bibliográficas e páginas editoriais para enriquecimento dos registros.

A análise buscou identificar uma solução tecnicamente viável, reproduzível e compatível com os recursos disponíveis para o desenvolvimento do projeto.

## 2. Critérios de avaliação

As fontes foram analisadas considerando os seguintes critérios:

| Critério | Descrição |
|---|---|
| Adequação ao domínio | Compatibilidade dos registros com o recorte literário |
| Cobertura bibliográfica | Quantidade de obras potencialmente aproveitáveis |
| Cobertura textual | Disponibilidade de descrições das obras |
| Qualidade dos metadados | Consistência de títulos, autores e gêneros |
| Facilidade de integração | Viabilidade de acesso e processamento dos dados |
| Rastreabilidade | Identificação da origem dos registros |
| Confiabilidade operacional | Comportamento diante de erros e indisponibilidades |
| Condições de uso | Restrições de acesso e reutilização dos conteúdos |

Nem todos os critérios foram mensurados quantitativamente.

As conclusões combinam resultados de análises exploratórias, observações durante os testes e limitações identificadas nas implementações.

## 3. Experimento 1 — Avaliação de datasets existentes

### 3.1. Hipótese

A utilização de um dataset bibliográfico previamente estruturado poderia reduzir o esforço necessário para construir o corpus inicial do sistema.

A principal vantagem esperada seria a obtenção imediata de registros com metadados e descrições textuais.

### 3.2. Goodbooks-10k Extended

O Goodbooks-10k Extended foi investigado durante a etapa inicial de exploração.

O conjunto analisado apresentava aproximadamente 10 mil registros e incluía informações bibliográficas e descrições.

Embora a disponibilidade textual fosse elevada, o dataset não apresentou adequação suficiente ao recorte de literatura pretendido.

**Resultado:** a existência de descrições não foi suficiente para justificar a adoção da fonte.

**Decisão:** não utilizar o Goodbooks como catálogo principal.

### 3.3. Skoob

O dataset proveniente do Skoob apresentou maior proximidade com o domínio literário inicialmente estabelecido.

A análise exploratória identificou:

| Indicador | Resultado |
|---|---:|
| Registros totais | 11.975 |
| Registros com descrições preenchidas | 11.318 |
| Registros classificados como `Literatura Brasileira` | 949 |
| Registros candidatos após filtros adicionais | Aproximadamente 946 |

Apesar da disponibilidade de descrições, a análise identificou dificuldades relacionadas à consistência dos metadados.

A classificação de uma obra como literatura brasileira não assegurava, isoladamente, a nacionalidade de seu autor.

Também foram observadas dificuldades relacionadas à classificação dos gêneros e à diferenciação entre obras e edições.

**Resultado:** o conjunto apresentava cobertura textual promissora, mas exigia uma etapa adicional de validação bibliográfica.

**Decisão:** preservar o dataset como referência exploratória, sem utilizá-lo como fonte principal da versão inicial do catálogo.

### 3.4. Conclusão do experimento

A análise dos datasets demonstrou que a disponibilidade de descrições deve ser avaliada em conjunto com a adequação ao domínio e a confiabilidade dos metadados.

A busca por uma base bibliográfica mais estruturada permaneceu necessária.

## 4. Experimento 2 — Investigação de APIs bibliográficas

### 4.1. Hipótese

APIs bibliográficas poderiam fornecer informações complementares, permitindo enriquecer registros de uma base estruturada sem depender exclusivamente de datasets que já contivessem descrições.

Foram investigadas alternativas como Open Library e Google Books.

### 4.2. Open Library

A Open Library foi considerada devido à disponibilidade de informações bibliográficas e à possibilidade de consultar obras a partir de seus títulos e autores.

A investigação identificou limitações na cobertura de descrições.

Parte dos registros consultados não disponibilizava conteúdo textual suficiente para o enriquecimento.

Não foi estabelecida uma taxa geral de cobertura da Open Library para o catálogo do projeto.

**Resultado:** a API apresentou potencial como fonte complementar de informações bibliográficas, mas não foi considerada suficiente como fonte única de descrições.

**Decisão:** manter a Open Library como alternativa para funcionalidades posteriores, especialmente consultas baseadas em livros de referência.

### 4.3. Google Books

A Google Books API foi investigada como fonte de metadados e descrições.

Durante os testes iniciais, ocorreram respostas HTTP 429, indicando limitação de requisições.

Esse comportamento dificultou a utilização da API como principal mecanismo de enriquecimento.

Posteriormente, foi incorporado suporte à autenticação por chave de API.

O pipeline também passou a considerar mecanismos de tratamento de erros e controle de requisições.

**Resultado:** a integração apresentou limitações operacionais, mas permaneceu tecnicamente aproveitável como fonte complementar.

**Decisão:** manter a integração com Google Books como opção do pipeline, sem torná-la obrigatória.

### 4.4. Conclusão do experimento

Os testes evidenciaram a necessidade de evitar dependência exclusiva de uma API externa.

A arquitetura de enriquecimento passou a priorizar a combinação de fontes independentes e o armazenamento persistente dos resultados.

## 5. Experimento 3 — Seleção do Oceanos como base bibliográfica

### 5.1. Hipótese

Uma base de dados associada a um prêmio literário poderia oferecer metadados mais adequados ao recorte do projeto, mesmo sem disponibilizar descrições.

### 5.2. Dataset investigado

O conjunto de dados do Prêmio Oceanos apresentou:

| Indicador | Resultado |
|---|---:|
| Registros totais | 16.799 |
| Combinações distintas de título e autor | 16.746 |
| Gêneros literários | 5 |

Os gêneros identificados foram:

- Romance.
- Conto.
- Poesia.
- Crônica.
- Dramaturgia.

Entre os atributos disponíveis estavam informações de autoria, editoras, países, anos e indicadores de premiação.

Entretanto, o dataset não apresentava descrições textuais das obras.

### 5.3. Resultado

A fonte demonstrou adequação para estruturar o catálogo bibliográfico.

A principal limitação identificada foi a ausência de textos descritivos, necessários para os experimentos de recuperação de informação.

### 5.4. Decisão

O Oceanos foi adotado como base bibliográfica principal.

A solução passou a separar duas responsabilidades:

**Seleção bibliográfica:** identificação das obras e obtenção de metadados estruturados.

**Enriquecimento textual:** recuperação de descrições em fontes externas.

Durante essa etapa, o recorte operacional foi ampliado de literatura brasileira para literatura em língua portuguesa.

## 6. Experimento 4 — Enriquecimento pela Apple Books

### 6.1. Objetivo

Investigar a disponibilidade de descrições para obras presentes no Oceanos utilizando a Apple Books API.

### 6.2. Metodologia

Foi desenvolvido um experimento exploratório com obras selecionadas do catálogo.

O piloto considerou 30 livros distribuídos entre os gêneros literários.

Foram realizadas consultas à loja brasileira e, complementarmente, à loja portuguesa.

O procedimento procurou identificar correspondências bibliográficas e verificar a disponibilidade de informações textuais.

### 6.3. Resultados

| Indicador | Resultado |
|---|---:|
| Obras no piloto | 30 |
| Obras encontradas na loja brasileira | 9 |
| Obras encontradas na loja portuguesa | 4 |
| Novas obras acrescentadas exclusivamente pela loja portuguesa | 0 |

A loja brasileira apresentou correspondências para aproximadamente 30% dos livros do piloto.

Entretanto, a amostra era pequena e não foi estabelecida como representativa de todo o conjunto do Oceanos.

A presença de um resultado na API também não garante, isoladamente, que a descrição tenha qualidade suficiente para inclusão no corpus.

### 6.4. Decisão

A Apple Books foi incorporada como fonte prioritária no enriquecimento.

A decisão foi fundamentada na disponibilidade observada de registros e na possibilidade de automatizar as consultas.

## 7. Experimento 5 — Extração de informações em sites editoriais

### 7.1. Hipótese

Sites de editoras poderiam disponibilizar descrições de obras ausentes das APIs bibliográficas.

### 7.2. Metodologia

Foi desenvolvido o protótipo `probe_editoras.py` para investigar estratégias de extração textual em páginas editoriais.

Foram consideradas diferentes representações de conteúdo:

- Dados estruturados em JSON-LD.
- Metadados Open Graph.
- Elementos HTML associados à descrição de produtos.

O experimento também procurou identificar limitações relacionadas à natureza dos textos extraídos.

### 7.3. Resultados qualitativos

O piloto examinou seis páginas editoriais, das quais cinco produziram candidatos textuais para análise.

Entre os candidatos obtidos, foram identificados exemplos de:

- Descrições bibliográficas potencialmente adequadas.
- Excertos literários que não correspondiam necessariamente a uma sinopse.
- Textos concentrados na apresentação do autor.
- Conteúdos insuficientes para caracterizar uma obra.

Essas observações demonstraram que a extração de texto não garante sua adequação ao objetivo do sistema.

### 7.4. Decisão

Os sites editoriais foram incorporados como fonte complementar.

Também foi estabelecida a necessidade de critérios de qualidade e de revisão para situações em que a classificação automática permanecesse incerta.

## 8. Experimento 6 — Consolidação de endereços editoriais

### 8.1. Problema identificado

Parte dos registros do Oceanos não apresentava o endereço eletrônico da editora.

Essa ausência impedia a tentativa automática de enriquecimento a partir de páginas editoriais.

### 8.2. Hipótese

A repetição de editoras em diferentes registros poderia permitir a recuperação de endereços ausentes.

### 8.3. Metodologia

Foi implementada uma estratégia de consolidação dos domínios associados às editoras.

A inferência automática foi condicionada à existência de evidências consistentes em diferentes obras vinculadas à mesma editora.

Registros com divergências entre domínios foram mantidos sem preenchimento automático.

### 8.4. Resultados

| Classificação | Registros |
|---|---:|
| Site original válido | 7.503 |
| Site inferido automaticamente | 3.278 |
| Site com conflito de informações | 3.453 |
| Site ausente | 2.512 |
| **Total** | **16.746** |

Os valores correspondem à classificação dos registros únicos considerados na consolidação.

A estratégia permitiu ampliar a quantidade de obras com um domínio editorial disponível para investigação.

### 8.5. Limitações

A identificação de um domínio não garante que:

- O site esteja ativo.
- A obra possua uma página específica.
- A página contenha uma descrição.
- O conteúdo encontrado seja adequado para recuperação semântica.

Portanto, o aumento da cobertura de endereços não deve ser interpretado como aumento equivalente da cobertura de descrições.

## 9. Experimento 7 — Integração das fontes

Os resultados anteriores fundamentaram o desenvolvimento do pipeline `enrich_oceanos_auto.py`.

A estratégia integrada considera:

1. Seleção bibliográfica a partir do Oceanos.
2. Consulta à Apple Books.
3. Consulta opcional ao Google Books.
4. Consulta complementar aos sites editoriais.
5. Verificação de correspondências entre títulos e autores.
6. Triagem automática da qualidade textual.
7. Registro da procedência dos dados.
8. Persistência incremental dos resultados.
9. Separação dos casos que exigem revisão.

O pipeline também mantém arquivos de auditoria que permitem analisar consultas realizadas, resultados encontrados e falhas.

A integração reduz a necessidade de executar manualmente os procedimentos utilizados nos experimentos iniciais.


## 10. Comparação das alternativas

A tabela apresenta uma síntese qualitativa das observações realizadas.

| Fonte | Principal contribuição | Limitação identificada | Papel adotado |
|---|---|---|---|
| Goodbooks | Dados bibliográficos e descrições | Adequação limitada ao domínio | Exploração inicial |
| Skoob | Grande disponibilidade de descrições | Inconsistências bibliográficas e questões de reutilização | Referência exploratória |
| Open Library | Metadados de obras | Cobertura textual insuficiente nos casos investigados | Complementação futura |
| Google Books | Metadados e descrições | Limitações de requisição observadas | Fonte opcional |
| Oceanos | Base literária estruturada | Ausência de descrições | Catálogo bibliográfico principal |
| Apple Books | Recuperação de descrições | Cobertura incompleta | Fonte prioritária |
| Sites editoriais | Descrições complementares | Heterogeneidade das páginas e dos textos | Fonte complementar |

A tabela não representa um ranking quantitativo de desempenho.

As fontes foram utilizadas em etapas diferentes e apresentavam objetivos distintos dentro do processo de construção do catálogo.

