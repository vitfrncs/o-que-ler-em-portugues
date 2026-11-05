# Experimentos de fontes de dados

Este diretório reúne implementações exploratórias desenvolvidas durante a construção do catálogo literário do **BookMatch AI**.

O objetivo desses experimentos foi investigar diferentes estratégias para obter e enriquecer metadados bibliográficos, especialmente descrições textuais utilizadas posteriormente nos sistemas de recuperação de informação e RAG.

Os scripts foram preservados para documentar a evolução técnica do projeto e permitir a análise das decisões tomadas.

## 1. Experimentos

### `enrich_oceanos.py`

Implementação anterior do processo de enriquecimento dos registros do Oceanos.

Foi desenvolvida antes da consolidação do pipeline automático atual e representa uma etapa intermediária da construção do catálogo.

### `probe_oceanos_multifonte.py`

Experimento para investigar a recuperação de informações bibliográficas a partir de diferentes fontes externas.

Entre as fontes avaliadas, utilizamos a Apple Books API, considerando consultas a diferentes catálogos regionais.

O objetivo foi investigar a disponibilidade de descrições e a viabilidade de utilizar essas fontes para enriquecer os registros do Oceanos.

### `probe_editoras.py`

Protótipo de extração de informações diretamente dos sites das editoras.

Foram exploradas estratégias de identificação de descrições em páginas HTML, incluindo dados estruturados e metadados.

Esse experimento ajudou a fundamentar a utilização de páginas editoriais como fonte complementar às APIs bibliográficas.

## 2. Solução adotada

Após os experimentos, o projeto passou a utilizar um pipeline integrado:

`scripts/enrich_oceanos_auto.py`

Esse script reúne as principais etapas do enriquecimento automático:

- Seleção de registros do Oceanos.
- Consulta a fontes bibliográficas externas.
- Busca complementar em sites editoriais.
- Validação heurística das correspondências.
- Armazenamento da procedência das descrições.
- Registro de auditoria e casos para revisão.
- Persistência dos resultados para retomada da execução.

## 3. Estado dos experimentos

Os arquivos deste diretório são **protótipos históricos**, não o ponto de entrada oficial para a construção do catálogo.

Eles foram preservados para fins de documentação e aprendizado.

Os comandos e caminhos internos desses scripts podem refletir a estrutura anterior do repositório. Sua execução após a reorganização ainda não foi validada.

Para utilizar o pipeline atual, consulte `scripts/enrich_oceanos_auto.py`.
