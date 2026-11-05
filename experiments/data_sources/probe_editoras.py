"""Extrai descrições candidatas de páginas editoriais do BookMatch AI."""

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import httpx
import pandas as pd
from bs4 import BeautifulSoup


USER_AGENT = "BookMatchAI-research/0.1"


def clean_text(value):
    """Remove marcações HTML e espaços desnecessários."""
    if not isinstance(value, str):
        return ""

    text = BeautifulSoup(value, "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def iter_nodes(data):
    """Percorre objetos JSON-LD, inclusive estruturas aninhadas."""
    if isinstance(data, list):
        for item in data:
            yield from iter_nodes(item)

    elif isinstance(data, dict):
        yield data

        for key in ("@graph", "mainEntity"):
            if key in data:
                yield from iter_nodes(data[key])


def extract_candidates(html):
    """Extrai possíveis descrições de uma página HTML."""

    soup = BeautifulSoup(html, "html.parser")

    candidates = []
    seen = set()

    def add_candidate(method, value):
        text = clean_text(value)

        if len(text) < 120:
            return

        if text.casefold() in seen:
            return

        seen.add(text.casefold())

        candidates.append({
            "extraction_method": method,
            "description_candidate": text,
        })

    # 1. JSON-LD
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue

        for node in iter_nodes(data):
            node_type = node.get("@type", [])

            if isinstance(node_type, str):
                node_type = [node_type]

            if any(t in ("Book", "Product") for t in node_type):
                add_candidate("json_ld", node.get("description"))

    # 2. Metadados HTML
    meta_selectors = {
        "og_description": 'meta[property="og:description"]',
        "meta_description": 'meta[name="description"]',
    }

    for method, selector in meta_selectors.items():
        element = soup.select_one(selector)

        if element:
            add_candidate(method, element.get("content"))

    # 3. Seções HTML comuns em páginas editoriais
    html_selectors = {
        "html_itemprop": '[itemprop="description"]',
        "html_woocommerce": ".woocommerce-Tabs-panel--description",
        "html_tab_description": "#tab-description",
    }

    for method, selector in html_selectors.items():
        element = soup.select_one(selector)

        if element:
            for unwanted in element.select("script, style"):
                unwanted.decompose()

            add_candidate(
                method,
                element.get_text(" ", strip=True),
            )

    return candidates


def robots_permission(client, url):
    """Verifica se as regras robots.txt permitem a consulta."""

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False, "invalid_url"

    robots_url = urljoin(
        f"{parsed.scheme}://{parsed.netloc}",
        "/robots.txt",
    )

    try:
        response = client.get(robots_url)
    except httpx.HTTPError as exc:
        return False, f"robots_error:{type(exc).__name__}"

    if response.status_code == 404:
        return True, "robots_missing"

    if response.status_code != 200:
        return False, f"robots_http_{response.status_code}"

    parser = RobotFileParser()
    parser.parse(response.text.splitlines())

    return parser.can_fetch(USER_AGENT, url), "robots_checked"


def run(queue_path, output_path, limit):

    queue = pd.read_csv(
        queue_path,
        dtype={"book_id": "string"},
    )

    required = {
        "book_id",
        "titulo_livro",
        "nome_autor",
        "publisher_page_url",
    }

    missing = required - set(queue.columns)

    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")

    # Apenas livros que já possuem página editorial identificada
    books = queue[
        queue["publisher_page_url"].notna()
    ].head(limit)

    results = []

    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=15,
        follow_redirects=False,
    ) as client:

        for index, book in enumerate(
            books.itertuples(index=False),
            start=1,
        ):
            url = str(book.publisher_page_url)

            base = {
                "book_id": str(book.book_id),
                "title": str(book.titulo_livro),
                "author": str(book.nome_autor),
                "source_url": url,
                "usage_status": "pending_rights_review",
            }

            print(f"[{index}/{len(books)}] {base['title']}")

            allowed, reason = robots_permission(client, url)

            if not allowed:
                results.append({
                    **base,
                    "status": "not_fetched",
                    "detail": reason,
                })
                continue

            try:
                response = client.get(url)
                response.raise_for_status()

            except httpx.HTTPError as exc:
                results.append({
                    **base,
                    "status": "request_error",
                    "detail": type(exc).__name__,
                })
                continue

            if "text/html" not in response.headers.get(
                "content-type", ""
            ).lower():
                results.append({
                    **base,
                    "status": "not_html",
                    "detail": "",
                })
                continue

            descriptions = extract_candidates(response.text)

            if not descriptions:
                results.append({
                    **base,
                    "status": "no_description_candidate",
                    "detail": "",
                })

            for description in descriptions:
                results.append({
                    **base,
                    **description,
                    "status": "pending_manual_review",
                    "detail": "",
                })

            time.sleep(1.5)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(results).to_csv(
        output_path,
        index=False,
    )

    print(f"\nRegistros gerados: {len(results)}")
    print(f"Arquivo: {output_path}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--queue",
        type=Path,
        default=Path(
            "data/interim/oceanos/piloto_multifonte/"
            "publisher_review_queue.csv"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/interim/oceanos/"
            "publisher_description_previews.csv"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=6,
    )

    args = parser.parse_args()

    run(
        args.queue,
        args.output,
        args.limit,
    )

    