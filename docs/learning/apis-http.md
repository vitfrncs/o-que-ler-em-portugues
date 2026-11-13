# APIs HTTP em Python: um guia passo a passo

> Material de consulta para aprender a integrar serviços externos em aplicações Python. A Apple Books é o exemplo principal, mas o processo vale para APIs de livros, previsão do tempo, mapas, LLMs e outros serviços. O objetivo é entender **o que fazer, por que fazer e como investigar uma API nova sem depender de um tutorial específico**.

## 1. O que vou aprender?

Ao terminar este guia, você deverá conseguir:

- distinguir API, HTTP, REST e JSON;
- localizar e interpretar a documentação de uma API;
- construir uma requisição `GET` com parâmetros;
- entender o objeto de resposta e seus possíveis erros;
- transformar um JSON externo em dados usados pelo seu próprio programa;
- escrever uma função de integração com validação e tratamento de falhas;
- testar essa integração sem fazer requisições reais;
- adaptar o processo a APIs que usam autenticação ou outros métodos HTTP.

**Pré-requisitos:** funções, listas, dicionários, `for`, `if`, exceções e ambientes virtuais em Python.

---

## 2. Entenda primeiro a comunicação

Uma **API** (*Application Programming Interface*) é uma interface que define como um programa pode interagir com outro componente. A API de uma biblioteca Python também é uma API; não é necessário haver internet.

Uma **API HTTP** expõe operações através de requisições HTTP. Há normalmente um **cliente** (quem solicita) e um **servidor** (quem processa e responde):

```text
Seu código Python                    Serviço externo
     cliente                             servidor
        |                                   |
        | ---- GET /search?term=... -----> |
        |                                   | pesquisa os dados
        | <--- status + JSON ------------- |
        |                                   |
  interpreta a resposta
```

O **HTTP** define a estrutura dessa troca de mensagens. O **HTTPS** é HTTP protegido por TLS, que ajuda a garantir confidencialidade e integridade durante a transmissão.

Uma API **REST** é uma API construída seguindo um estilo arquitetural específico. Muitas APIs na Web usam HTTP e JSON sem seguir rigorosamente todos os princípios REST. Portanto, *API*, *API HTTP* e *API REST* não são sinônimos.

**JSON** (*JavaScript Object Notation*) é um formato de representação de dados. Pode ser enviado no corpo de uma resposta HTTP, mas não é parte obrigatória do protocolo HTTP.

### Anatomia de uma requisição

Uma requisição costuma ter:

- **Método:** o tipo de operação, como `GET` (consultar) ou `POST` (enviar dados para criação/processamento).
- **URL/endpoint:** o endereço do recurso ou operação.
- **Parâmetros de consulta (*query parameters*):** filtros e opções após `?` na URL.
- **Cabeçalhos (*headers*):** metadados como `Accept` e, em algumas APIs, informações de autenticação.
- **Corpo (*body*):** dados enviados em operações que necessitam de um payload, como muitos `POST`.

Exemplo conceitual:

```http
GET /search?term=Crepusculo&limit=5 HTTP/1.1
Host: itunes.apple.com
Accept: application/json
```

Em uma URL como `https://itunes.apple.com/search?term=Crepusculo&limit=5`:

- `https` é o esquema/protocolo de acesso;
- `itunes.apple.com` é o host;
- `/search` é o caminho (*path*) do endpoint;
- `term` e `limit` são nomes de parâmetros;
- `Crepusculo` e `5` são seus valores.

**Não construa a URL manualmente com concatenação de strings.** Letras acentuadas, espaços e caracteres reservados precisam ser codificados corretamente. A biblioteca HTTP faz isso por você quando utiliza `params`.

### Métodos HTTP mais comuns

| Método | Uso típico |
| --- | --- |
| `GET` | Consultar dados, sem solicitar alteração do recurso. |
| `POST` | Enviar dados para criação ou processamento. |
| `PUT` | Substituir a representação de um recurso. |
| `PATCH` | Atualizar parte de um recurso. |
| `DELETE` | Solicitar a exclusão de um recurso. |

Os detalhes dependem do contrato da API. Um `POST` não significa, necessariamente, “salvar no banco”: APIs de modelos de linguagem também usam `POST` para executar inferências.

---

## 3. Antes de programar: aprenda a ler a documentação

Quando receber o nome de uma API desconhecida, procure responder às perguntas abaixo, **nesta ordem**.

1. **O que a API oferece?** Busca, consulta por ID, criação, atualização, processamento?
2. **Qual endpoint faz isso?** Anote URL e método HTTP.
3. **Quais argumentos são obrigatórios?** Identifique `path parameters`, `query parameters`, headers e body.
4. **Precisa de autenticação?** Há chave de API, token Bearer, OAuth ou acesso público?
5. **Qual é a estrutura da resposta?** Busque um exemplo de JSON e identifique campos obrigatórios/opcionais.
6. **Como a API sinaliza erros?** HTTP 4xx/5xx, códigos no JSON, limites de requisição?
7. **Existem paginação, limites e cache?** Quantos resultados vêm por chamada? Posso repetir a chamada?
8. **Quais são as condições de uso dos dados?** Disponível para consultar não significa livre para redistribuir.

Guarde essas respostas como um pequeno **contrato de integração**, antes de escrever a função.

### Contrato do exemplo: pesquisa na Apple Books

A Apple disponibiliza a *iTunes Search API*, que inclui pesquisas no catálogo da Apple Books.

- **Endpoint:** `https://itunes.apple.com/search`
- **Método:** `GET`
- **Parâmetro obrigatório:** `term` (texto pesquisado) e `country` (país da loja, segundo a documentação).
- **Parâmetros úteis:** `media=ebook`, `entity=ebook`, `limit=5` e `country=br`.
- **Formato de resposta:** JSON com `resultCount` e `results`.
- **Autenticação:** não é necessária para essa pesquisa pública conforme o uso documentado.
- **Cuidados:** disponibilidade varia por loja; resultados podem incluir diferentes edições; campos podem faltar; existem condições de uso e recomendações de limitação de chamadas.

A documentação indica `limit` no intervalo de **1 a 200** e menciona um limite de chamadas aproximado, sujeito a mudanças. Não trate esses valores como uma garantia permanente: confira a documentação antes de aumentar o volume de consultas.

> Importante: buscar um livro na loja brasileira **não prova** que ele foi originalmente escrito em português. Essa é uma regra de curadoria separada da integração HTTP.

---

## 4. Primeiro experimento: uma chamada isolada

No ambiente Python, instale a biblioteca caso não esteja disponível:

```bash
python -m pip install httpx
```

Crie um arquivo temporário para experimentar, ou execute no terminal com `python - <<'PY'`:

```bash
python - <<'PY'
import httpx

url = "https://itunes.apple.com/search"
params = {
    "term": "Crepúsculo Stephenie Meyer",
    "media": "ebook",
    "entity": "ebook",
    "country": "br",
    "limit": 3,
}

response = httpx.get(url, params=params, timeout=10.0)
print("URL enviada:", response.request.url)
print("Status HTTP:", response.status_code)
response.raise_for_status()

data = response.json()
print("Quantidade informada pela API:", data.get("resultCount"))
print("Resultados recebidos:", len(data.get("results", [])))
PY
```

O resultado exato depende do catálogo disponível no momento da consulta. Não pressupomos que uma edição específica será encontrada.

**Perguntas para observar no teste:**

- Como a biblioteca transformou espaços e caracteres especiais na URL?
- Qual código HTTP retornou?
- `data` é uma lista ou um dicionário?
- Onde está a lista de livros no JSON?

Se o teste falhar, isso ainda não prova que a função está errada: uma requisição real depende de rede, DNS, certificados, servidor e da disponibilidade da API.

### Uma alternativa: observar a requisição com `curl`

```bash
curl --get 'https://itunes.apple.com/search' \
  --data-urlencode 'term=Crepúsculo Stephenie Meyer' \
  --data-urlencode 'media=ebook' \
  --data-urlencode 'entity=ebook' \
  --data-urlencode 'country=br' \
  --data-urlencode 'limit=3'
```

Esse teste ajuda a separar problemas de comunicação HTTP de problemas específicos no seu código Python.

---

## 5. Entenda os objetos `Request` e `Response`

Ao executar `httpx.get(...)`, o Python recebe um objeto `httpx.Response`. Ele representa a **resposta HTTP**, não diretamente a lista de livros.

```python
response = httpx.get(url, params=params, timeout=10.0)
```

Alguns atributos e métodos importantes:

| Expressão | O que representa |
| --- | --- |
| `response.status_code` | Código de status, como 200 ou 404. |
| `response.headers` | Cabeçalhos enviados pelo servidor. |
| `response.text` | Corpo interpretado como texto. |
| `response.content` | Corpo em bytes. |
| `response.request.url` | URL efetivamente enviada. |
| `response.raise_for_status()` | Lança `HTTPStatusError` para respostas não bem-sucedidas. |
| `response.json()` | Interpreta o corpo como JSON e devolve estruturas Python. |

Ordem recomendada:

```python
response = httpx.get(url, params=params, timeout=10.0)
response.raise_for_status()
data = response.json()
```

Não confunda `response.json()` com a validação do formato dos dados. Um JSON pode estar sintaticamente correto e **não conter** as chaves esperadas.

### Códigos HTTP mais importantes

| Família/exemplo | Interpretação comum |
| --- | --- |
| `2xx`, como `200` | Operação HTTP bem-sucedida. |
| `400` | Requisição inválida. |
| `401` | Autenticação ausente ou inválida. |
| `403` | Acesso negado. |
| `404` | Recurso/rota não encontrado. |
| `429` | Requisições em excesso (*rate limiting*). |
| `500`/`503` | Falha no servidor ou serviço indisponível. |

Uma pesquisa que devolve `200` e `"results": []` **não é um erro HTTP**. Significa que o servidor respondeu normalmente, mas não encontrou itens para aquela pesquisa.

---

## 6. JSON não é um dicionário Python, mas é fácil convertê-lo

Considere este exemplo **fictício e simplificado** de resposta:

```json
{
  "resultCount": 2,
  "results": [
    {
      "trackId": 101,
      "trackName": "Livro A",
      "artistName": "Autora A",
      "description": "Uma história de aventura."
    },
    {
      "trackId": 102,
      "trackName": "Livro B",
      "artistName": "Autor B"
    }
  ]
}
```

Depois de `data = response.json()`:

```python
books = data["results"]             # lista
first_book = books[0]                # dicionário
name = first_book["trackName"]       # string
```

Correspondências comuns entre JSON e Python:

| JSON | Python |
| --- | --- |
| Objeto `{...}` | `dict` |
| Array `[...]` | `list` |
| String | `str` |
| Número | `int` ou `float` |
| `true` / `false` | `True` / `False` |
| `null` | `None` |

### Campos opcionais: quando usar `.get()`?

No exemplo, o segundo livro não tem `description`.

```python
book["description"]       # KeyError se a chave não existir
book.get("description")   # None se ela estiver ausente
```

Use `[...]` para campos que seu contrato exige. Use `.get()` para campos realmente opcionais. Não transforme automaticamente toda ausência em string vazia, pois isso pode esconder problemas de dados.

**Atenção:** `data.get("results", [])` evita `KeyError`, mas não garante que o valor obtido seja uma lista. Em uma integração mais cuidadosa, verifique `isinstance(data, dict)` e `isinstance(data.get("results"), list)` antes de percorrer os registros.

---

## 7. De experimento a função reutilizável

Uma função de integração não é apenas uma chamada `httpx.get()`. Ela estabelece um **contrato entre a API externa e seu próprio programa**.

```text
Entrada do programa
  -> validação
  -> parâmetros HTTP
  -> requisição
  -> verificação de status
  -> leitura do JSON
  -> validação da estrutura
  -> conversão de campos
  -> retorno consistente
```

### Passo 1 — Defina a interface da função

Exemplo:

```python
def search_books(query: str, limit: int = 5) -> list[dict]:
    ...
```

Antes de implementá-la, decida:

- O que significa `query`? Um título, autor ou ambos?
- `limit` controla os resultados da API ou a quantidade exibida ao usuário?
- O que retornar se não houver resultados? Uma lista vazia é adequada.
- O que fazer se a rede falhar? Uma lista vazia **não** é adequada, pois esconderia o erro.
- Quais campos a aplicação precisa? Evite devolver todo o JSON sem necessidade.

### Passo 2 — Valide a entrada antes de usar a rede

```python
if not isinstance(query, str) or not query.strip():
    raise ValueError("A consulta deve ser um texto não vazio.")

if isinstance(limit, bool) or not isinstance(limit, int) or not (1 <= limit <= 200):
    raise ValueError("limit deve ser um inteiro entre 1 e 200.")
```

**Por quê?** Porque uma entrada inválida é um erro local, identificável antes de fazer uma requisição. Observe a checagem explícita de `bool`: em Python, `bool` é uma subclasse de `int`.

### Passo 3 — Prepare `params`

```python
params = {
    "term": query.strip(),
    "media": "ebook",
    "entity": "ebook",
    "country": "br",
    "limit": limit,
}
```

A biblioteca cuida da codificação dos parâmetros. Em outra API, os nomes serão diferentes: por exemplo, `q` em vez de `term`, ou um parâmetro na própria rota, como `/books/{id}`. **Leia o contrato da API, não memorize nomes de parâmetros.**

### Passo 4 — Execute a requisição e diferencie erros

Este é um exemplo de tratamento **explícito** das principais falhas:

```python
import httpx

try:
    response = httpx.get(
        "https://itunes.apple.com/search",
        params=params,
        timeout=10.0,
    )
    response.raise_for_status()
except httpx.TimeoutException as exc:
    raise RuntimeError("O serviço demorou demais para responder.") from exc
except httpx.HTTPStatusError as exc:
    raise RuntimeError(
        f"O serviço respondeu com HTTP {exc.response.status_code}."
    ) from exc
except httpx.RequestError as exc:
    raise RuntimeError("Não foi possível comunicar-se com o serviço.") from exc
```

A ordem importa: `TimeoutException` é uma categoria mais específica de erro de requisição. O `from exc` preserva a exceção original para diagnóstico.

Em bibliotecas reutilizáveis, você também pode optar por deixar as exceções do `httpx` propagarem, documentando-as para o chamador. O importante é definir uma política consistente — **não usar `except Exception: return []`**.

### Passo 5 — Interprete e valide a resposta

```python
try:
    data = response.json()
except ValueError as exc:
    raise RuntimeError("O serviço não retornou um JSON válido.") from exc

if not isinstance(data, dict):
    raise ValueError("Resposta inesperada: esperava um objeto JSON.")

raw_books = data.get("results")
if not isinstance(raw_books, list):
    raise ValueError("Resposta inesperada: 'results' não é uma lista.")
```

Aqui, `ValueError` do `response.json()` representa JSON inválido. Já os `ValueError` seguintes representam **estrutura incompatível com nosso contrato**, ainda que o JSON seja válido.

### Passo 6 — Traduza os campos externos para seu modelo interno

A Apple pode usar `trackName`, mas seu programa prefere `title`. A decisão pertence à camada de integração:

```python
normalized_books = []

for raw_book in raw_books:
    if not isinstance(raw_book, dict):
        continue

    book_id = raw_book.get("trackId")
    title = raw_book.get("trackName")

    if book_id is None or not title:
        continue  # sem identificador/título não sabemos apresentar o item

    normalized_books.append({
        "id": str(book_id),
        "title": title,
        "author": raw_book.get("artistName"),
        "description": raw_book.get("description"),
        "cover_url": raw_book.get("artworkUrl100"),
        "source_url": raw_book.get("trackViewUrl"),
    })
```

O `continue` é uma **política de tratamento de registros incompletos** adotada nesse exemplo, não uma obrigação universal. Em outro sistema, talvez você queira registrar o item como incompleto ou lançar um erro.

A descrição e a capa podem estar ausentes. Nunca invente esses dados para preencher o resultado. Observe também que algumas descrições podem conter marcação HTML: exibi-las como texto simples pode exigir limpeza adequada.

### Passo 7 — Retorne os dados padronizados

```python
return normalized_books
```

O resultado é uma `list[dict]` que não depende dos nomes internos da Apple. Uma versão futura pode usar `TypedDict`, `dataclass` ou um modelo Pydantic para validar o contrato mais formalmente.

**Importante:** o código desta seção apresenta as partes do método em sequência. Se copiá-las, reúna-as **dentro de uma mesma função**, mantendo a indentação; não são vários programas independentes.

### Exemplo consolidado: todos os passos em uma função

As partes anteriores foram explicadas separadamente para facilitar o aprendizado. Abaixo está **uma versão de referência completa**, útil quando você estiver implementando outra integração. Ela exige internet para executar uma pesquisa real, mas pode ser lida e testada com respostas simuladas.

```python
import httpx


def search_books(query: str, limit: int = 5) -> list[dict]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("A consulta deve ser um texto não vazio.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("limit deve ser um inteiro entre 1 e 200.")

    params = {
        "term": query.strip(),
        "media": "ebook",
        "entity": "ebook",
        "country": "br",
        "limit": limit,
    }

    try:
        response = httpx.get(
            "https://itunes.apple.com/search", params=params, timeout=10.0
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("Falha ao consultar a API de livros.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("A API retornou um JSON inválido.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Formato de resposta inesperado.")

    books = []
    for item in data["results"]:
        if not isinstance(item, dict):
            continue
        if item.get("trackId") is None or not item.get("trackName"):
            continue
        books.append({
            "id": str(item["trackId"]),
            "title": item["trackName"],
            "author": item.get("artistName"),
            "description": item.get("description"),
            "cover_url": item.get("artworkUrl100"),
            "source_url": item.get("trackViewUrl"),
        })

    return books
```

Para transformá-la em um método de `AppleBooksClient`, acrescente `self` à assinatura e, se fizer sentido, mova URL, cliente HTTP e configuração para os atributos da classe. **A lógica continua a mesma.**

Faça um exercício de leitura: encontre no código onde começam e terminam a validação, a rede, a leitura da resposta e a normalização. Depois tente explicar por que cada etapa existe antes de adaptá-la.

---

## 8. A diferença entre uma função simples e um cliente HTTP

Para uma única chamada, `httpx.get()` é suficiente. Para muitas chamadas, um `httpx.Client` geralmente é melhor porque reutiliza conexões e centraliza configurações.

```python
import httpx

with httpx.Client(timeout=10.0) as client:
    response = client.get(
        "https://itunes.apple.com/search",
        params={"term": "Crepúsculo", "media": "ebook", "country": "br"},
    )
    response.raise_for_status()
    data = response.json()
```

O `with` fecha os recursos do cliente ao final. Se o cliente pertencer a uma classe que dura toda a aplicação, defina claramente **quem cria e fecha** esse cliente.

Uma classe como `AppleBooksClient` pode encapsular `search_books()`, mas **ser uma classe não é uma exigência de HTTP**. Use uma classe quando precisar compartilhar configuração, sessão HTTP, autenticação ou vários métodos correlatos.


---

## 9. Aprenda a testar sem depender da internet

Testes que fazem chamadas reais podem ser lentos, instáveis e consumir cotas. Para verificar a lógica da função, podemos simular o servidor.

O HTTPX oferece `MockTransport`, que intercepta a requisição e devolve uma resposta fabricada. Veja um exemplo completo, executável e independente da Apple:

```python
import httpx


def fake_server(request: httpx.Request) -> httpx.Response:
    assert request.method == "GET"
    assert request.url.path == "/search"
    assert request.url.params["term"] == "exemplo"
    return httpx.Response(
        200,
        json={"resultCount": 1, "results": [{"trackId": 123, "trackName": "Livro A"}]},
    )


transport = httpx.MockTransport(fake_server)

with httpx.Client(transport=transport) as client:
    response = client.get("https://servico.exemplo/search", params={"term": "exemplo"})
    response.raise_for_status()
    data = response.json()

assert data["results"][0]["trackName"] == "Livro A"
print("Teste sem rede concluído.")
```

O endereço `servico.exemplo` é fictício: a requisição **não chega à internet** porque o transporte foi substituído.

Esse teste verifica montagem da requisição e interpretação básica da resposta. Para testar sua função `search_books()` efetivamente, você precisará permitir que ela receba um cliente `httpx.Client` ou substituir a chamada de rede usando uma ferramenta de *mock*. Esse padrão é chamado de **injeção de dependência**: o código não precisa criar sozinho todas as dependências que utiliza.

### Quais situações vale testar?

| Caso | Resultado esperado |
| --- | --- |
| Busca válida | Lista com campos internos padronizados. |
| Sem resultados (`200` + `results: []`) | `[]`, sem erro. |
| `query` vazia ou `limit` inválido | Exceção de validação antes de usar a rede. |
| Erro HTTP 429 ou 503 | Falha identificável, não confundida com ausência de livros. |
| Falha de conexão ou timeout | Erro de comunicação controlado. |
| JSON malformado | Erro de formato de resposta. |
| JSON válido, mas sem `results` | Erro de contrato de dados. |
| Item sem descrição | Campo opcional representado como `None`. |
| Dois títulos semelhantes | A função devolve candidatos; outra camada resolve a escolha. |

Um **teste unitário** deve isolar a lógica da função. Um **teste de integração real** verifica a comunicação com o serviço, mas é melhor executá-lo separadamente e com menos frequência.

---

## 10. Problemas comuns e como investigar

**`ModuleNotFoundError: No module named 'httpx'`**  
Confira se o ambiente virtual está ativo e se instalou as dependências no mesmo interpretador utilizado para executar o arquivo. Compare `python -m pip show httpx` e `which python`.

**`ConnectError`, `ConnectTimeout` ou `ReadTimeout`**  
A rede, o DNS, o proxy, o servidor ou a conexão podem ter falhado. Verifique a URL, a conectividade e o timeout. Não confunda isso com uma pesquisa sem resultados.

**`CERTIFICATE_VERIFY_FAILED`**  
Há um problema na cadeia de confiança TLS, comum em redes corporativas com inspeção de HTTPS. A solução é configurar corretamente os certificados/CA confiáveis; não use `verify=False` como correção permanente.

**`HTTPStatusError: 429`**  
Pode indicar limite de requisições. Reduza a frequência, implemente cache quando permitido e respeite as orientações do serviço. Evite repetir indefinidamente.

**`KeyError: 'results'`**  
Talvez a resposta não tenha a estrutura esperada. Inspecione um exemplo seguro da resposta e valide o esquema. Uma API pode devolver mensagens de erro com outro formato.

**`JSONDecodeError` / erro em `response.json()`**  
O corpo pode ser HTML, texto vazio ou JSON inválido. Confira o status, o `Content-Type` e uma amostra limitada da resposta, sem registrar dados sensíveis.

**A API devolve o livro errado**  
Isso pode ser um problema de **resolução de entidade**, não de HTTP: título, autor, idioma, edição e identificadores precisam ser comparados. Não escolha cegamente o primeiro resultado.

**Os mesmos resultados aparecem em outra ordem**  
Serviços de busca podem alterar ranking e disponibilidade. Não escreva testes unitários que dependam da ordem atual dos resultados reais.

---

## 11. Autenticação, segurança e boas práticas

Nem todas as APIs são públicas. Algumas exigem chave ou token. Um padrão frequente de autenticação é o cabeçalho `Authorization`:

```python
import os
import httpx

api_token = os.environ["EXAMPLE_API_TOKEN"]
headers = {"Authorization": f"Bearer {api_token}"}

# Exemplo genérico: o endpoint e o token NÃO pertencem à Apple Books.
response = httpx.get(
    "https://api.exemplo.com/items",
    headers=headers,
    timeout=10.0,
)
```

Nunca coloque tokens reais no repositório, no README ou em prints de depuração. Use variáveis de ambiente e mantenha `.env` fora do Git. Alguns serviços usam chaves em parâmetros, mas isso aumenta o risco de exposição em logs de URLs; siga a documentação específica.

Outros cuidados:

- **Timeout:** não permita que a chamada espere indefinidamente; `10.0` é um exemplo, não uma regra universal. Timeouts podem ter fases de conexão, leitura, escrita e obtenção de conexão do pool.
- **Rate limiting:** limite a frequência; use cache quando permitido, evitando requisições idênticas.
- **Retries:** repetir pode ajudar em falhas transitórias, mas use tentativas limitadas e respeite `429` e o cabeçalho `Retry-After` quando aplicável. Não repita operações que modificam dados sem entender sua idempotência.
- **Licença e proveniência:** acesso técnico à API não concede automaticamente licença para redistribuir descrições, capas ou outros conteúdos.
- **Logs:** registre informações úteis (endpoint, tipo do erro, duração), mas não exponha tokens ou dados pessoais.
- **Contrato estável:** documente tipos, campos opcionais e exceções esperadas.
- **Chamadas síncronas ou assíncronas:** `httpx.get()`/`Client` são suficientes para nossa primeira integração. `AsyncClient` e `async/await` são úteis em aplicações concorrentes, mas acrescentam complexidade desnecessária para um começo.

---

## 12. Roteiro universal: integrar qualquer API HTTP

Ao implementar uma API nova daqui a alguns meses, siga este roteiro:

**A — Investigue (sem código)**

1. Escreva em uma frase a operação desejada.
2. Localize endpoint, método, autenticação e limites na documentação oficial.
3. Copie um exemplo de requisição e um de resposta.
4. Liste os campos necessários e os opcionais.
5. Defina claramente o que significa “não encontrado” e o que significa “falha”.

**B — Explore (em um script curto)**

6. Faça uma requisição mínima usando `curl` ou `httpx`.
7. Confira status, URL efetiva e estrutura do JSON.
8. Altere um parâmetro por vez para entender seu efeito.

**C — Implemente (função reutilizável)**

9. Defina entradas e saída da função antes de codificá-la.
10. Valide parâmetros localmente.
11. Prepare parâmetros, headers e/ou body conforme a documentação.
12. Envie a requisição com timeout.
13. Verifique status e trate exceções de rede.
14. Leia o JSON e valide sua estrutura.
15. Converta campos externos para um formato próprio e retorne o resultado.

**D — Torne confiável (testes e manutenção)**

16. Teste sucesso, vazio, entradas inválidas, erros HTTP, timeout e dados incompletos.
17. Simule respostas HTTP para que testes unitários não dependam da internet.
18. Documente limites, campos, origem e termos de uso.
19. Avalie cache, sessão reutilizável e monitoramento somente se fizerem falta.

### Perguntas de revisão

Sem consultar a seção anterior, tente responder:

1. Por que `response.json()` não substitui `raise_for_status()`?
2. Em que situação `return []` é correto? Em que situação esconderia uma falha?
3. Por que `params={...}` é melhor do que montar a URL concatenando strings?
4. O que muda se outra API chamar título de `name` em vez de `trackName`?
5. Como testar a conversão de JSON sem enviar requisições reais?
6. Por que um token de autenticação não deve aparecer em uma URL ou commit?
7. Qual é a diferença entre buscar dados externos e expor uma API própria?

Se conseguir responder a essas perguntas e repetir as etapas do roteiro, você já terá uma base para implementar integrações HTTP de forma autônoma.

---

## 13. Referências

- [Apple — iTunes Search API](https://performance-partners.apple.com/search-api): parâmetros, limite de resultados, exemplos e condições de uso.
- [HTTPX — QuickStart](https://www.python-httpx.org/quickstart/): requisições, `params`, `json()`, `raise_for_status()` e exceções.
- [HTTPX — Timeouts](https://www.python-httpx.org/advanced/timeouts/): configuração e tipos de timeout.
- [HTTPX — MockTransport](https://www.python-httpx.org/advanced/transports/#mock-transports): testes sem acessar a rede.
- [HTTPX — Client](https://www.python-httpx.org/advanced/clients/): sessões e reutilização de conexões.

