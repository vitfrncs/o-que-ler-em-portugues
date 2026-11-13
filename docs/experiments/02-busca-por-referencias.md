# Experimento 02 — Recuperação semântica por livros de referência

## 1. Objetivo

Investigar o comportamento da recuperação semântica quando a consulta é construída a partir das descrições de livros de referência.

Foram consideradas três estratégias:

1. Utilizar o embedding da descrição de um único livro.
2. Utilizar uma consulta temática formulada manualmente.
3. Combinar os embeddings de dois livros de referência por meio da média vetorial.

O experimento tem caráter exploratório. Seu objetivo é identificar comportamentos e limitações do sistema, e não demonstrar superioridade de uma estratégia.

## 2. Configuração experimental

**Catálogo:** versão `catalog_v0`, contendo 469 registros.

**Modelo de embeddings:** `intfloat/multilingual-e5-small`.

**Dimensionalidade:** 384.

**Mecanismo de recuperação:** `SemanticRetriever`.

**Métrica utilizada:** similaridade de cosseno entre vetores normalizados.

**Quantidade de resultados:** Top-5.

**Fonte das referências:** Apple Books API.

Os textos das obras de referência foram construídos a partir de seus títulos e descrições. As descrições tiveram suas marcações HTML removidas.

Os textos utilizados