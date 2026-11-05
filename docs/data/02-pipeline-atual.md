# Pipeline de construção e enriquecimento do catálogo

**Projeto:** BookMatch AI  
**Componente:** Engenharia de Dados  
**Implementação:** `scripts/enrich_oceanos_auto.py`  
**Status:** Pipeline experimental funcional  
**Última atualização:** 05/11/2026

## 1. Visão geral

O pipeline de enriquecimento do BookMatch AI tem como objetivo construir um catálogo de obras literárias em língua portuguesa a partir de metadados bibliográficos do Prêmio Oceanos.

O dataset original apresenta informações como títulos, autores, gêneros e editoras, mas não disponibiliza descrições textuais das obras.

Essa ausência representa uma limitação para os componentes de recuperação lexical e semântica, que dependem de representações textuais para identificar documentos relevantes.

Para solucionar esse problema, foi desenvolvido um processo automatizado de enriquecimento que consulta fontes externas, recupera descrições e associa os textos às obras do catálogo.

A implementação também contempla mecanismos de validação, rastreabilidade, persistência incremental e tratamento de falhas.

## 2. Arquitetura do pipeline

O processo é organizado nas seguintes etapas:

```text
             Dataset Oceanos
                    │
                    ▼
        Leitura e preparação
                    │
                    ▼
       Seleção e deduplicação
                    │
                    ▼
     Consolidação das editoras
                    │
                    ▼
        Recuperação de textos
                    │
          ┌─────────┼──────────┐
          │         │          │
          ▼         ▼          ▼
        Apple     Google     Editoras
        Books     Books       (HTML)
          │         │          │
          └─────────┼──────────┘
                    │
                    ▼
       Validação bibliográfica
                    │
                    ▼
        Triagem de qualidade
                    │
                    ▼
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
     Candidatos          Casos para
      aceitos              revisão
          │                   │
          └─────────┬─────────┘
                    │
                    ▼
          Persistência e
             auditoria
```

As fontes são consultadas sequencialmente, conforme a necessidade.

O pipeline prioriza a Apple Books, utiliza o Google Books quando habilitado e recorre às páginas editoriais quando não existe uma descrição considerada suficiente.

Essa estratégia evita consultas complementares quando uma fonte anterior já fornece um candidato adequado.

## 3. Entrada de dados

O arquivo de entrada principal é:

`data/raw/oceanos.csv`

O pipeline utiliza a biblioteca Pandas para carregar os registros bibliográficos.

### 3.1. Campos utilizados

| Campo | Finalidade |
|---|---|
| `titulo_livro` | Identificação da obra |
| `nome_autor` | Identificação da autoria |
| `genero_livro` | Classificação literária |
| `ano` | Ordenação temporal |
| `nome_editora` | Identificação da editora |
| `site_editora` | Localização de páginas editoriais |
| `indicador_vencedor` | Priorização bibliográfica |
| `indicador_finalista` | Priorização bibliográfica |
| `indicador_semifinalista` | Priorização bibliográfica |

Os campos de título, autor e gênero são obrigatórios para o processamento.

A ausência de alguma dessas colunas provoca um erro de validação antes do início das consultas externas.

Outros campos são utilizados quando disponíveis.

## 4. Preparação e seleção das obras

### 4.1. Normalização textual

A função `normalize()` é utilizada para padronizar os valores empregados na identificação e comparação bibliográfica.

O procedimento inclui:

- Conversão para letras minúsculas, por meio de `casefold()`.
- Normalização Unicode.
- Remoção de marcas de acentuação.
- Substituição de pontuação por separadores.
- Normalização dos espaços.

Essa operação permite comparar representações textuais que diferem apenas por capitalização, acentuação ou pontuação.

Entretanto, a normalização não resolve automaticamente abreviações, pseudônimos ou divergências bibliográficas mais complexas.

### 4.2. Identificação única das obras

A função `book_id()` gera um identificador determinístico a partir do título e do autor normalizados.

A implementação utiliza SHA-256 e preserva os primeiros 16 caracteres hexadecimais do resultado.

Conceitualmente:

```python
key = normalize(title) + "|" + normalize(author)
identifier = sha256(key.encode("utf-8")).hexdigest()[:16]
```

Esse procedimento permite reconhecer o mesmo par título–autor em diferentes execuções.

A abordagem também facilita o controle de duplicatas e a retomada das consultas.

O identificador não representa um ISBN nem distingue necessariamente diferentes edições de uma obra.

### 4.3. Seleção dos registros

A função `select_oceanos()` realiza a preparação inicial do catálogo.

O procedimento:

1. Carrega o arquivo de entrada.
2. Seleciona os cinco gêneros considerados pelo projeto.
3. Remove registros sem título ou autor.
4. Gera os identificadores bibliográficos.
5. Define prioridades de seleção.
6. Ordena os registros.
7. Remove duplicatas com o mesmo identificador.

### 4.4. Priorização por premiação

Os registros são organizados considerando os indicadores de premiação do Oceanos.

A ordem de prioridade implementada é:

| Prioridade | Condição |
|---|---|
| 0 | Obra vencedora |
| 1 | Obra finalista |
| 2 | Obra semifinalista |
| 3 | Demais obras |

Dentro da mesma prioridade, os registros são ordenados pelo ano em ordem decrescente.

A priorização é uma decisão operacional de seleção. Não representa uma medida automática de qualidade literária ou relevância para consultas dos usuários.

### 4.5. Distribuição entre gêneros

A função `interleave_genres()` alterna os registros dos cinco gêneros durante o processamento.

Essa estratégia procura evitar que a execução percorra inicialmente apenas as obras de um único gênero.

A implementação permite estabelecer uma quantidade máxima de candidatos aceitos por gênero.

A alternância, entretanto, não garante distribuição equilibrada no catálogo final, pois a disponibilidade de descrições varia entre os gêneros.

## 5. Consolidação dos sites editoriais

O dataset original apresenta registros com endereços ausentes, inválidos ou inconsistentes.

Para ampliar as oportunidades de enriquecimento, foi implementado um cadastro consolidado de sites editoriais.

### 5.1. Normalização das URLs

A função `normal_publisher_base()` prepara e valida os endereços.

O procedimento considera:

- Remoção de observações textuais anexadas ao final de alguns campos.
- Padronização do esquema HTTPS.
- Validação da estrutura do domínio.
- Rejeição de endereços sintaticamente inválidos.
- Rejeição de endereços locais e de determinados destinos não públicos.

Por exemplo, um endereço acompanhado por uma observação editorial pode ser normalizado para preservar apenas o domínio.

Essa validação reduz a possibilidade de falhas durante a construção das requisições HTTP.

### 5.2. Construção do cadastro

A função `build_publisher_site_registry()` agrupa registros pelo nome normalizado da editora.

Para cada editora, são analisados os domínios disponíveis e a quantidade de obras distintas que apresentam cada domínio.

Um endereço pode ser inferido automaticamente quando:

1. Existe apenas um domínio válido associado à editora.
2. O domínio possui suporte de pelo menos duas obras distintas, conforme a configuração padrão.
3. Não existem domínios divergentes no grupo considerado.

Quando são identificados múltiplos domínios, o registro é classificado como conflitante e não recebe uma inferência automática.

### 5.3. Aplicação do cadastro

A função `apply_publisher_site_registry()` utiliza o cadastro para preencher endereços ausentes ou inválidos.

Os endereços originais válidos são preservados.

A origem do endereço é registrada por meio do campo `publisher_site_source`, que pode apresentar valores como:

- `original`
- `inferred`
- `conflict`
- `missing`

Essa informação permite diferenciar metadados obtidos diretamente do Oceanos de valores inferidos durante o processamento.

## 6. Recuperação de descrições

### 6.1. Apple Books

A Apple Books API constitui a primeira fonte consultada, quando habilitada.

As requisições utilizam informações de título e autor, além de parâmetros para restringir a busca a livros digitais.

A função `parse_apple()` analisa a resposta e procura registros compatíveis com a obra esperada.

Os resultados são submetidos às verificações bibliográficas e à triagem textual antes da aceitação.

### 6.2. Google Books

A integração com Google Books é opcional.

Sua utilização depende da ativação do argumento `--use-google` e da presença da variável de ambiente:

`GOOGLE_BOOKS_API_KEY`

A função `parse_google()` processa os resultados da API, verificando título, autoria e disponibilidade de descrição.

A implementação também considera a informação de idioma retornada pela fonte, aceitando registros identificados como portugueses ou sem idioma informado.

Essa regra não equivale a uma validação completa do idioma do texto.

A integração pode apresentar limitações relacionadas a cotas, indisponibilidade e restrições de requisições.

### 6.3. Sites editoriais

Quando não é obtida uma descrição satisfatória nas APIs, o pipeline pode consultar o site da editora.

A classe `PublisherClient` concentra as operações relacionadas a essas páginas.

O processo considera:

1. Identificação do domínio editorial.
2. Verificação das permissões de acesso.
3. Busca de páginas relacionadas à obra.
4. Verificação do título e da autoria.
5. Extração de candidatos textuais.

A descoberta de páginas utiliza, quando disponíveis, mecanismos de busca do WordPress e buscas internas do próprio site.

A extração considera diferentes estruturas:

| Método | Fonte do texto |
|---|---|
| `json_ld` | Dados estruturados JSON-LD |
| `html_woocommerce` | Descrição de produto WooCommerce |
| `html_itemprop` | Elementos HTML com propriedade de descrição |
| `html_tab_description` | Abas de descrição |
| `og_description` | Metadados Open Graph |
| `meta_description` | Metadados HTML |

A disponibilidade desses elementos depende da estrutura de cada página.

### 6.4. Respeito às restrições de acesso

O componente editorial consulta as regras de `robots.txt` e considera intervalos entre requisições.

Também limita o acompanhamento de redirecionamentos ao domínio editorial permitido.

Respostas de limitação de requisições e determinadas falhas de acesso são registradas em vez de provocar tentativas ilimitadas.

Esses mecanismos reduzem riscos operacionais, mas não substituem a verificação das condições de uso de cada fonte.

## 7. Validação bibliográfica

Uma das principais dificuldades do enriquecimento consiste em garantir que a descrição recuperada pertença à obra correta.

Para reduzir associações incorretas, foram implementadas verificações de título e autoria.

### 7.1. Correspondência de títulos

A função `title_matches()` compara versões normalizadas dos títulos.

A implementação aceita igualdade entre os títulos e determinados casos em que o resultado contém um subtítulo separado por pontuação reconhecida.

A correspondência não utiliza, nesta versão, um modelo semântico nem uma métrica de similaridade aproximada.

### 7.2. Correspondência de autores

A função `author_matches()` compara os nomes normalizados.

A implementação considera:

- Igualdade entre os nomes.
- Igualdade entre conjuntos ordenados de tokens, permitindo diferenças na ordem das palavras.

Abreviações, pseudônimos e variações não contempladas por essas regras podem resultar na rejeição de correspondências bibliográficas legítimas.

### 7.3. Verificação de páginas editoriais

A função `page_matches()` procura o título em elementos destacados da página, especialmente cabeçalhos e metadados de título.

A autoria é verificada no conteúdo textual da página.

Quando o título corresponde, mas não é encontrada evidência suficiente sobre a autoria, o registro pode ser classificado como `uncertain_author`.

Essa distinção evita aceitar automaticamente uma descrição com base apenas na presença do título.

## 8. Limpeza e qualidade textual

### 8.1. Preparação dos textos

A função `clean_text()` executa uma limpeza inicial das descrições recuperadas.

Entre as operações realizadas estão:

- Conversão de entidades HTML.
- Remoção de marcações HTML.
- Normalização dos espaços.

O objetivo é produzir um campo textual mais adequado ao processamento posterior.

### 8.2. Triagem automática

A função `quality_status()` aplica critérios heurísticos para avaliar as descrições.

Na configuração padrão, os critérios incluem:

| Condição | Classificação |
|---|---|
| Menos de 180 caracteres | `insufficient` |
| Menos de 25 palavras | `insufficient` |
| Mais de 4.500 caracteres | `needs_review` |
| Texto iniciado por determinados sinais de citação | `needs_review` |
| Demais textos que superam os filtros | `candidate` |

O limite mínimo de caracteres pode ser configurado por `--min-chars`.

A classificação `candidate` representa apenas uma aprovação preliminar de qualidade textual.

Ela não assegura que a descrição seja uma sinopse, esteja em português ou apresente informações literárias corretas.

### 8.3. Seleção entre candidatos

A função `best_description()` seleciona um candidato entre os textos disponíveis.

O procedimento considera:

- Classificação de qualidade.
- Prioridade do método de extração.
- Comprimento textual, utilizado como critério complementar.

Os métodos de extração recebem prioridades definidas na implementação.

A seleção não é realizada por um modelo de linguagem nem por avaliação humana.

## 9. Critérios de inclusão no catálogo

O catálogo experimental é construído a partir dos registros que satisfazem simultaneamente:

```text
quality_status == "candidate"
match_status == "verified"
```

Registros que apresentam qualidade insuficiente não são incluídos.

Candidatos com correspondência bibliográfica incerta ou textos classificados para revisão são mantidos separadamente.

### 9.1. Significado dos estados

| Estado | Interpretação |
|---|---|
| `candidate` | Descrição aprovada pela triagem heurística |
| `needs_review` | Descrição ou correspondência que exige revisão |
| `no_description` | Nenhuma descrição aproveitável foi encontrada |
| `transient_error` | A tentativa não produziu candidato e apresentou falha potencialmente temporária |

A classificação de um registro como `candidate` não equivale à sua validação definitiva.

### 9.2. Direitos de reutilização

As descrições recebem o campo:

```text
usage_status = pending_rights_review
```

Esse valor registra que as condições de reutilização ainda precisam ser analisadas.

A presença de uma descrição no catálogo experimental não representa autorização para sua redistribuição pública.

## 10. Persistência incremental e auditoria

O pipeline registra os resultados durante a execução.

A função `atomic_csv()` grava os arquivos por meio de um arquivo temporário, posteriormente substituído pelo arquivo definitivo.

Essa estratégia reduz o risco de deixar um CSV parcialmente escrito durante a persistência.

A implementação também carrega os resultados de execuções anteriores para evitar consultas repetidas.

### 10.1. Arquivos produzidos

O diretório padrão é:

`data/interim/oceanos/auto500/`

| Arquivo | Finalidade |
|---|---|
| `audit.csv` | Histórico das consultas e respectivos resultados |
| `descriptions_candidates.csv` | Candidatos textuais recuperados |
| `catalog_experimental.csv` | Registros aprovados pelos critérios automáticos |
| `needs_review.csv` | Candidatos que exigem revisão |
| `summary.csv` | Resumo por gênero |
| `publisher_sites_registry.csv` | Cadastro consolidado das editoras |
| `publisher_site_coverage.csv` | Cobertura dos endereços editoriais |

As tentativas sem descrição aproveitável permanecem registradas na auditoria, mas não necessariamente aparecem em `needs_review.csv`.

### 10.2. Retomada das execuções

O pipeline identifica registros já processados a partir dos arquivos existentes.

Por padrão, esses registros não são consultados novamente.

O argumento `--retry-errors` permite reprocessar registros classificados como `transient_error`.

Também existe suporte ao reprocessamento de casos anteriormente classificados como `no_publisher_site` quando um endereço editorial passa a estar disponível.

### 10.3. Importação de resultados anteriores

O argumento `--import-existing` permite incorporar descrições provenientes dos experimentos preliminares.

Essa importação utiliza identificadores bibliográficos e critérios de validação para reconhecer registros correspondentes.

Candidatos editoriais importados sem evidência suficiente de autoria permanecem classificados para revisão.

O mecanismo foi implementado para reaproveitar resultados sem atribuir automaticamente um nível de confiabilidade superior ao efetivamente demonstrado.

## 11. Execução do pipeline

Os comandos devem ser executados na raiz do repositório.

### 11.1. Verificação inicial

```bash
python scripts/enrich_oceanos_auto.py \
  --input data/raw/oceanos.csv \
  --per-genre 100 \
  --limit 15 \
  --dry-run
```

A opção `--dry-run` apresenta uma seleção preliminar das obras sem consultar APIs externas.

### 11.2. Relatório dos sites editoriais

```bash
python scripts/enrich_oceanos_auto.py \
  --input data/raw/oceanos.csv \
  --publisher-report-only
```

Esse modo produz os relatórios de editoras sem realizar consultas às fontes externas.

### 11.3. Enriquecimento incremental

```bash
python scripts/enrich_oceanos_auto.py \
  --input data/raw/oceanos.csv \
  --per-genre 100 \
  --limit 100 \
  --use-google
```

Nesse exemplo:

- `--per-genre 100` define a meta máxima de candidatos aceitos por gênero.
- `--limit 100` limita a quantidade de registros consultados na execução.
- `--use-google` habilita a fonte opcional Google Books.

A opção `--limit` não representa a quantidade de descrições que serão encontradas.

### 11.4. Tratamento de falhas

```bash
python scripts/enrich_oceanos_auto.py \
  --input data/raw/oceanos.csv \
  --per-genre 100 \
  --limit 15 \
  --retry-errors \
  --use-google
```

O argumento `--retry-errors` habilita novas tentativas para os registros classificados como falhas temporárias.

A utilização repetida dessa opção não garante a recuperação de descrições.

## 12. Limitações técnicas

A implementação atual apresenta limitações relevantes.

**Validação por regras:** a identificação bibliográfica utiliza correspondências textuais conservadoras, podendo rejeitar títulos ou autores apresentados em formatos diferentes.

**Qualidade das descrições:** a triagem utiliza características superficiais do texto e não verifica integralmente seu conteúdo semântico.

**Idioma:** o pipeline não realiza uma validação linguística uniforme para todas as fontes. Descrições em outros idiomas podem permanecer no corpus.

**Cobertura:** a disponibilidade de descrições varia entre gêneros, autores, editoras e plataformas.

**Descoberta editorial:** as estratégias de busca dependem dos recursos oferecidos pelos sites das editoras e podem não localizar páginas existentes.

**Dependência de serviços externos:** mudanças nas APIs, nos sites e nas políticas de acesso podem afetar as execuções.

**Avaliação:** a aprovação automática não substitui uma revisão amostral da qualidade bibliográfica e textual.

**Segurança e direitos:** a validação de URLs e o respeito às regras de acesso não equivalem à autorização para reutilização pública dos conteúdos recuperados.

## 13. Reprodutibilidade

A reprodução do processo depende de:

1. Disponibilidade do arquivo original do Oceanos.
2. Instalação das dependências definidas pelo projeto.
3. Utilização da mesma versão do script.
4. Registro dos parâmetros utilizados.
5. Disponibilidade das fontes externas durante a execução.
6. Preservação dos arquivos de auditoria e dos resultados intermediários.

A persistência incremental permite retomar o processamento, mas os resultados de novas consultas podem diferir dos observados anteriormente.

Isso ocorre porque as APIs e as páginas editoriais podem modificar seus catálogos e conteúdos.


## 14. Considerações finais

O pipeline desenvolvido permitiu integrar metadados bibliográficos estruturados e descrições provenientes de fontes externas em um processo automatizado de enriquecimento.

A implementação contempla mecanismos de seleção, deduplicação, validação, rastreabilidade e persistência incremental.

O catálogo produzido constitui um recurso experimental para o desenvolvimento dos sistemas de recuperação lexical e semântica do BookMatch AI.

A etapa posterior de avaliação deverá investigar a qualidade das descrições e os efeitos das decisões de enriquecimento sobre a relevância dos resultados recuperados.

O pipeline representa uma solução funcional para a preparação inicial do corpus, permanecendo sujeito a melhorias relacionadas à validação bibliográfica, à análise textual e à reprodutibilidade das consultas externas.