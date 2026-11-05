# Histórico de seleção e enriquecimento das fontes de dados

**Projeto:** BookMatch AI  
**Etapa:** Construção do catálogo literário  
**Status:** Documentação retrospectiva dos experimentos  
**Última atualização:** 05/11/2026

## 1. Introdução

A construção do catálogo literário constituiu uma das etapas iniciais do desenvolvimento do BookMatch AI.

O projeto requer um conjunto de dados bibliográficos que permita recuperar obras a partir de consultas em linguagem natural, utilizando métodos de recuperação lexical e semântica. Posteriormente, os documentos recuperados serão utilizados como contexto para a geração de recomendações fundamentadas por modelos de linguagem.

Para atender a esses objetivos, o catálogo deve disponibilizar, no mínimo, informações de identificação das obras, autoria e descrições textuais relevantes.

A obtenção desses dados apresentou desafios relacionados à cobertura das fontes, à qualidade dos metadados, à identificação das obras e à disponibilidade de descrições.

Este documento apresenta o histórico da investigação de fontes bibliográficas e as decisões que conduziram à adoção do catálogo do Prêmio Oceanos, complementado por processos automatizados de enriquecimento.

## 2. Requisitos para seleção das fontes

A seleção das fontes de dados considerou os seguintes critérios:

- **Adequação ao domínio:** presença de obras compatíveis com o recorte literário do projeto.
- **Qualidade dos metadados:** disponibilidade de informações confiáveis sobre títulos, autores e gêneros.
- **Cobertura textual:** existência de descrições aproveitáveis para recuperação de informação.
- **Rastreabilidade:** possibilidade de identificar a origem dos registros e das descrições.
- **Viabilidade técnica:** acesso aos dados por arquivos locais, APIs ou outras interfaces disponíveis.
- **Reprodutibilidade:** possibilidade de registrar procedimentos, critérios de seleção e resultados.
- **Condições de uso:** necessidade de avaliar restrições aplicáveis à coleta e à redistribuição dos conteúdos.

A investigação demonstrou que a disponibilidade de grande quantidade de registros não garante, isoladamente, a adequação de um dataset para sistemas de recuperação e RAG.

## 3. Exploração inicial de datasets

### 3.1. Goodbooks-10k Extended

O Goodbooks-10k Extended foi uma das primeiras fontes consideradas durante a exploração inicial.

O arquivo analisado continha aproximadamente 10 mil registros e 30 colunas, incluindo informações bibliográficas e descrições.

A análise exploratória identificou 9.943 registros com o campo de descrição preenchido. Entretanto, a presença desse campo não assegurava que todos os textos fossem adequados à recuperação de informação.

A principal limitação estava relacionada à adequação do conjunto de dados ao recorte literário pretendido.

**Decisão:** o dataset não foi selecionado como fonte principal. Sua análise foi mantida como parte dos estudos exploratórios de preparação de dados.

### 3.2. Skoob

O conjunto de dados proveniente do Skoob apresentou maior potencial para a identificação de obras relacionadas à literatura brasileira.

O arquivo analisado continha 11.975 registros, dos quais 11.318 possuíam descrições não vazias.

Durante a exploração, foram encontrados 949 registros associados à classificação `Literatura Brasileira`. Uma seleção posterior, com critérios adicionais, produziu aproximadamente 946 registros candidatos.

Entretanto, foram identificadas limitações importantes:

- Inconsistências nas classificações de gênero.
- Dificuldade de verificar a nacionalidade dos autores.
- Registros potencialmente duplicados, incluindo diferentes edições.
- Variações na qualidade e no conteúdo das descrições.
- Necessidade de verificar as condições de reutilização dos textos.

A classificação `Literatura Brasileira` não foi considerada evidência suficiente para confirmar a nacionalidade de um autor.

**Decisão:** o dataset foi mantido como referência exploratória, mas não adotado diretamente como catálogo principal.

## 4. Investigação de fontes bibliográficas externas

### 4.1. Open Library

A Open Library foi considerada como fonte complementar de metadados bibliográficos.

A investigação identificou que a disponibilidade de descrições varia entre as obras, o que limita sua utilização como fonte única para o enriquecimento textual do catálogo.

A ausência de descrições em parte dos registros também exigiria consultas complementares.

**Decisão:** a Open Library permaneceu como fonte potencial para o fluxo de consulta por livro de referência, no qual uma obra mencionada é utilizada para identificar características relevantes e recuperar títulos semelhantes.

### 4.2. Google Books

A Google Books API foi investigada como alternativa para obter metadados e descrições de livros.

Durante os testes iniciais, foram observadas respostas HTTP 429, associadas à limitação de requisições.

Esse comportamento evidenciou a necessidade de implementar controles de frequência, tratamento de erros e mecanismos que evitassem dependência exclusiva de uma API externa.

Posteriormente, foi incorporado suporte à autenticação por chave de API, configurada por variável de ambiente.

**Decisão:** o Google Books passou a integrar o pipeline como fonte opcional de enriquecimento, sem constituir uma dependência obrigatória.

## 5. Adoção do Prêmio Oceanos como base bibliográfica

A investigação posterior identificou o conjunto de dados do Prêmio Oceanos como uma alternativa mais adequada para estruturar o catálogo.

O dataset analisado continha 16.799 registros, correspondentes a 16.746 combinações distintas de título e autor após a deduplicação considerada.

Entre os metadados disponíveis, destacam-se:

- Título da obra.
- Nome do autor.
- Ano de inscrição.
- Gênero literário.
- Nome da editora.
- Site da editora, quando disponível.
- Informações de país.
- Indicadores de premiação.

O conjunto apresenta cinco categorias literárias: Romance, Conto, Poesia, Crônica e Dramaturgia.

Entretanto, o arquivo original não disponibiliza descrições textuais das obras.

Assim, a adoção do Oceanos exigiu a implementação de uma etapa adicional de enriquecimento.

### 5.1. Atualização do recorte literário

O escopo inicial priorizava obras de autoria brasileira.

Durante a construção do catálogo, a necessidade de verificar rigorosamente a nacionalidade dos autores representou uma limitação relevante para a obtenção de um corpus inicial.

Diante disso, o recorte operacional foi ampliado para **literatura em língua portuguesa**, permitindo a utilização do conjunto bibliográfico do Oceanos sem restringir os registros exclusivamente à autoria brasileira.

Essa decisão alterou o escopo do catálogo, mas preservou os objetivos técnicos relacionados à recuperação de informação, à avaliação experimental e ao RAG.

## 6. Enriquecimento das descrições

### 6.1. Apple Books

A Apple Books API foi investigada como fonte de descrições bibliográficas.

Um piloto com 30 obras, distribuídas entre os cinco gêneros do Oceanos, encontrou nove resultados úteis na loja brasileira.

Consultas complementares à loja portuguesa identificaram quatro resultados, todos já encontrados na loja brasileira naquele piloto.

Os resultados indicaram que a Apple Books poderia contribuir para o enriquecimento do catálogo.

Entretanto, a cobertura observada no piloto não pode ser generalizada para todo o conjunto do Oceanos.

### 6.2. Sites editoriais

Também foram realizados experimentos de extração de informações diretamente das páginas das editoras.

A investigação considerou diferentes formas de apresentação das descrições, incluindo:

- Dados estruturados em JSON-LD.
- Metadados Open Graph.
- Elementos HTML de páginas de produtos.

Os testes identificaram páginas com descrições potencialmente úteis, mas também textos inadequados, como excertos literários, apresentações de autores e informações insuficientes sobre as obras.

Essas observações fundamentaram a necessidade de combinar extração automática com critérios de validação textual e bibliográfica.

### 6.3. Consolidação dos sites editoriais

O dataset do Oceanos apresentava registros sem endereço eletrônico da editora e casos com informações inconsistentes.

Para ampliar as oportunidades de enriquecimento, foi implementada uma estratégia de consolidação dos endereços editoriais.

O procedimento identifica registros pertencentes à mesma editora e permite recuperar endereços ausentes quando há evidências consistentes em outros registros.

A análise realizada identificou 3.278 registros adicionais com endereços inferidos segundo os critérios conservadores utilizados.

Conflitos entre domínios foram mantidos sem resolução automática.

A recuperação do endereço de uma editora não garante a disponibilidade de uma descrição para determinada obra.

## 7. Consolidação do pipeline automático

Os experimentos anteriores fundamentaram o desenvolvimento do script principal:

`scripts/enrich_oceanos_auto.py`

O pipeline integra as seguintes operações:

1. Leitura e preparação dos registros do Oceanos.
2. Seleção de obras considerando os gêneros literários.
3. Consolidação de informações sobre as editoras.
4. Consulta à Apple Books.
5. Consulta opcional ao Google Books.
6. Busca complementar em sites editoriais.
7. Verificação heurística de correspondências bibliográficas.
8. Avaliação preliminar da qualidade das descrições.
9. Registro da procedência dos textos.
10. Persistência de resultados e auditoria das consultas.

A execução incremental permite preservar resultados anteriores e retomar a coleta sem reiniciar todo o processo.

Os registros potencialmente ambíguos são separados para revisão, enquanto as tentativas realizadas permanecem documentadas nos arquivos de auditoria.


## 8. Limitações identificadas

Apesar dos resultados obtidos, permanecem limitações relevantes:

**Cobertura desigual:** a disponibilidade de descrições varia entre gêneros e fontes bibliográficas.

**Qualidade textual:** alguns registros podem apresentar descrições em outros idiomas, textos promocionais ou conteúdos pouco informativos.

**Correspondência bibliográfica:** a validação automática reduz o risco de associação incorreta, mas não elimina ambiguidades entre títulos, autores e edições.

**Dependência de fontes externas:** APIs e páginas editoriais podem sofrer alterações, indisponibilidade ou restrições de acesso.

**Direitos de utilização:** as descrições recuperadas permanecem sujeitas à verificação das condições de reutilização e redistribuição.

**Viés de seleção:** obras com maior presença em catálogos digitais podem apresentar maior probabilidade de inclusão no corpus enriquecido.

## 9. Considerações finais

A construção do catálogo demonstrou que a preparação de dados para sistemas de recuperação de informação envolve desafios que ultrapassam a simples obtenção de registros bibliográficos.

A solução adotada combina uma base estruturada de metadados com fontes complementares de descrições, mecanismos de validação e registros de auditoria.

A trajetória experimental também evidencia a importância de distinguir disponibilidade de dados, qualidade textual, cobertura das fontes e adequação aos requisitos do sistema.

O catálogo resultante constitui uma base experimental para o desenvolvimento e a avaliação dos componentes de recuperação lexical, recuperação semântica e geração aumentada por recuperação do BookMatch AI.

A descrição detalhada da implementação será apresentada em `docs/data/02-pipeline-atual.md`, enquanto os resultados dos experimentos com fontes externas serão consolidados em `docs/experiments/01-comparacao-fontes.md`.