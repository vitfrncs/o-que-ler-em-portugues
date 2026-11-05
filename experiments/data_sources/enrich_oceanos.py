"""Enriquecimento auditável do catálogo Oceanos via Google Books e Open Library.

Exemplo:
 python scripts/enrich_oceanos.py --input data/raw/oceanos.csv --per-genre 100 --limit 5 --skip-google
"""
from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
import time
import unicodedata
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path

import httpx
import pandas as pd

GOOGLE_URL = "https://www.googleapis.com/books/v1/volumes"
OPEN_LIBRARY_URL = "https://openlibrary.org"
OCEANOS_GENRES = ("Poesia", "Romance", "Conto", "Crônica", "Dramaturgia")
PROVIDERS = ("google", "open_library")
PROVIDER_DIAGNOSTIC_COLUMNS = [
    f"{p}_{name}" for p in PROVIDERS
    for name in ("status", "detail", "hits", "matches", "description_chars")
]
AUDIT_COLUMNS = [
    "book_id", "title", "authors", "genre", "priority_tier",
    "status", "source", "detail", "checked_at_utc",
    *PROVIDER_DIAGNOSTIC_COLUMNS,
]
CATALOG_COLUMNS = [
    "book_id", "title", "authors", "genre", "oceanos_year", "publisher",
    "description", "description_source", "description_source_url",
    "matched_title", "matched_authors", "source_record_id",
    "description_chars", "retrieved_at_utc", "usage_status",
]
NORMAL_FAILURES = {
    "no_results", "no_match", "no_description", "short_description", "other_language"
}


@dataclass
class LookupResult:
    status: str
    detail: str = ""
    hits: int = 0
    matches: int = 0
    description_chars: int = 0
    record: dict | None = None


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"br", "p", "div", "li"}:
            self.parts.append(" ")


def clean_description(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    parser = TextExtractor()
    parser.feed(raw)
    text = html.unescape("".join(parser.parts))
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^\w]+", " ", text).strip()


def title_matches(expected: str, actual: str) -> bool:
    e, a = norm(expected), norm(actual)
    if not e or not a:
        return False
    if e == a:
        return True
    # Aceita edição com subtítulo acrescentado, não mero prefixo arbitrário.
    base = re.split(r"\s*[:–—]\s*|\s+-\s+", actual, maxsplit=1)[0]
    if norm(base) == e:
        return True
    return len(e) >= 12 and SequenceMatcher(None, e, a).ratio() >= 0.96


def author_matches(expected: str, candidates: list[str] | str | None) -> bool:
    if isinstance(candidates, str):
        candidates = [candidates]
    if not isinstance(candidates, list) or not candidates:
        return False
    tokens = norm(expected).split()
    return any(
        norm(name) == norm(expected)
        or (len(tokens) >= 2 and sorted(tokens) == sorted(norm(name).split()))
        for name in candidates if isinstance(name, str)
    )


def identifier(title: str, author: str) -> str:
    key = f"{norm(title)}|{norm(author)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def priority_tier(row: dict) -> str:
    for col, value in (
        ("indicador_vencedor", "vencedor"),
        ("indicador_finalista", "finalista"),
        ("indicador_semifinalista", "semifinalista"),
    ):
        if norm(row.get(col, "")) == "sim":
            return value
    return "inscrito"


def select_books(df: pd.DataFrame, genres: set[str]) -> pd.DataFrame:
    required = {"titulo_livro", "nome_autor", "genero_livro", "ano", "nome_editora"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colunas do Oceanos ausentes: {sorted(missing)}")
    books = df.dropna(subset=["titulo_livro", "nome_autor", "genero_livro"]).copy()
    books = books.loc[books["genero_livro"].astype(str).map(lambda x: norm(x) in genres)].copy()
    books["book_id"] = [
        identifier(t, a) for t, a in zip(books["titulo_livro"], books["nome_autor"])
    ]
    books["priority_tier"] = books.apply(lambda r: priority_tier(r.to_dict()), axis=1)
    priority_order = {"vencedor": 0, "finalista": 1, "semifinalista": 2, "inscrito": 3}
    books["priority_order"] = books["priority_tier"].map(priority_order)
    books["year_sort"] = pd.to_numeric(books["ano"], errors="coerce")
    books = books.sort_values(
        ["priority_order", "year_sort"], ascending=[True, False], kind="stable"
    )
    return books.drop_duplicates(subset=["book_id"], keep="first")


def get_json(client: httpx.Client, url: str, params: dict | None = None) -> dict:
    response = client.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def google_lookup(
    client: httpx.Client, title: str, author: str, min_chars: int, api_key: str = ""
) -> LookupResult:
    params = {
        "q": f'intitle:"{title}" inauthor:"{author}"',
        "maxResults": 10,
        "printType": "books",
    }
    if api_key:
        params["key"] = api_key
    data = get_json(client, GOOGLE_URL, params)
    items = data.get("items") or []
    if not items:
        return LookupResult("no_results", "Google Books não retornou volumes")
    matched = 0
    empty = 0
    short = 0
    other_language = 0
    max_chars = 0
    for item in items:
        info = item.get("volumeInfo") or {}
        if not title_matches(title, info.get("title", "")) or not author_matches(author, info.get("authors")):
            continue
        matched += 1
        language = info.get("language", "")
        if language and language != "pt":
            other_language += 1
            continue
        description = clean_description(info.get("description"))
        max_chars = max(max_chars, len(description))
        if not description:
            empty += 1
            continue
        if len(description) < min_chars:
            short += 1
            continue
        volume_id = item.get("id", "")
        return LookupResult(
            "found", "Correspondência título+autor; descrição disponível",
            len(items), matched, len(description),
            {
                "description": description,
                "description_source": "google_books",
                "description_source_url": info.get("infoLink") or f"https://books.google.com/books?id={volume_id}",
                "matched_title": info["title"],
                "matched_authors": "; ".join(info.get("authors", [])),
                "source_record_id": volume_id,
            }
        )
    if not matched:
        return LookupResult("no_match", "Resultados sem título e autor correspondentes", len(items))
    if short:
        status = "short_description"
        detail = f"{short} correspondência(s) com descrição < {min_chars} caracteres"
    elif empty:
        status, detail = "no_description", f"{empty} correspondência(s) sem descrição"
    else:
        status, detail = "other_language", f"{other_language} edição(ões) em idioma diferente de pt"
    return LookupResult(status, detail, len(items), matched, max_chars)


def open_library_lookup(
    client: httpx.Client, title: str, author: str, min_chars: int,
    delay: float = 1.1,
) -> LookupResult:
    time.sleep(delay)
    data = get_json(client, f"{OPEN_LIBRARY_URL}/search.json", {
        "title": title, "author": author, "fields": "key,title,author_name", "limit": 5,
    })
    docs = data.get("docs") or []
    if not docs:
        # Busca diagnóstica mais ampla, mantendo a checagem conservadora
        # de título + autor antes de aceitar qualquer descrição.
        time.sleep(delay)
        fallback = get_json(client, f"{OPEN_LIBRARY_URL}/search.json", {
            "title": title, "fields": "key,title,author_name", "limit": 10,
        })
        docs = fallback.get("docs") or []
        if not docs:
            return LookupResult(
                "no_results",
                "Open Library: sem resultados por título+autor e por título",
            )
    matched = 0
    no_description = 0
    short = 0
    max_chars = 0
    for work in docs:
        if not title_matches(title, work.get("title", "")) or not author_matches(author, work.get("author_name")):
            continue
        key = work.get("key") or ""
        if not re.fullmatch(r"(?:/works/)?OL\d+W", key):
            continue
        matched += 1
        if not key.startswith("/works/"):
            key = "/works/" + key
        time.sleep(delay)
        work_data = get_json(client, f"{OPEN_LIBRARY_URL}{key}.json")
        raw = work_data.get("description", "")
        if isinstance(raw, dict):
            raw = raw.get("value", "")
        description = clean_description(raw)
        max_chars = max(max_chars, len(description))
        if not description:
            no_description += 1
            continue
        if len(description) < min_chars:
            short += 1
            continue
        return LookupResult(
            "found", "Correspondência título+autor; descrição da obra disponível",
            len(docs), matched, len(description),
            {
                "description": description,
                "description_source": "open_library",
                "description_source_url": f"{OPEN_LIBRARY_URL}{key}",
                "matched_title": work.get("title", ""),
                "matched_authors": "; ".join(work.get("author_name", [])),
                "source_record_id": key,
            }
        )
    if not matched:
        return LookupResult("no_match", "Obras retornadas sem título e autor correspondentes", len(docs))
    if short:
        status, detail = "short_description", f"{short} obra(s) com descrição < {min_chars} caracteres"
    else:
        status, detail = "no_description", f"{no_description} obra(s) sem descrição"
    return LookupResult(status, detail, len(docs), matched, max_chars)


def error_lookup(exc: Exception, provider: str) -> LookupResult:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        retry_after = exc.response.headers.get("Retry-After")
        hint = f"; Retry-After={retry_after}" if retry_after else ""
        return LookupResult(
            "rate_limited" if code == 429 else "api_error",
            f"{provider}: HTTP {code}{hint}",
        )
    return LookupResult("api_error", f"{provider}: {type(exc).__name__}: {exc}")


def overall_status(google: LookupResult, ol: LookupResult) -> str:
    if google.status == "found" or ol.status == "found":
        return "found"
    if google.status in {"rate_limited", "api_error"} or ol.status in {"rate_limited", "api_error"}:
        return "api_error"
    if google.status == "skipped" or ol.status == "skipped":
        return "partial_not_found"
    if google.status in NORMAL_FAILURES and ol.status in NORMAL_FAILURES:
        return "not_found"
    return "partial_not_found"


def balanced_catalog(catalog: pd.DataFrame, genres: list[str], per_genre: int) -> pd.DataFrame:
    parts = [
        catalog.loc[catalog["genre"].astype(str).map(norm) == norm(g)].head(per_genre)
        for g in genres
    ]
    return pd.concat(parts, ignore_index=True) if parts else catalog.iloc[0:0].copy()


def next_genre(
    genres: list[str], queues: dict[str, deque], found: dict[str, int],
    attempted: dict[str, int], quota: int,
) -> str | None:
    eligible = [g for g in genres if found[g] < quota and queues[g]]
    return min(eligible, key=lambda g: (attempted[g], genres.index(g))) if eligible else None


def load_history(path: Path, columns: list[str]) -> pd.DataFrame:
    history = pd.read_csv(path, dtype=str).fillna("") if path.exists() else pd.DataFrame()
    for col in columns:
        if col not in history.columns:
            history[col] = ""
    return history[columns]


def should_skip_old(status: str, skip_google: bool) -> bool:
    # Falha parcial sem Google não deve ser marcada como verificação das duas APIs.
    return status in {"found", "not_found"} or (skip_google and status == "partial_not_found")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Arquivo Oceanos (.csv ou .csv.gz)")
    parser.add_argument("--output-dir", default="data/interim/oceanos")
    parser.add_argument("--limit", type=int, default=5, help="Até 50 livros novos nesta execução")
    parser.add_argument("--per-genre", type=int, default=100)
    parser.add_argument("--genres", default=",".join(OCEANOS_GENRES))
    parser.add_argument("--min-chars", type=int, default=120)
    parser.add_argument("--skip-google", action="store_true")
    parser.add_argument(
        "--recheck-partials", action="store_true",
        help="Reconsulta registros antigos partial_not_found para detalhar o diagnóstico",
    )
    parser.add_argument("--contact-email", default="", help="Contato no User-Agent da Open Library")
    parser.add_argument("--ol-delay", type=float, default=1.1)
    parser.add_argument("--dry-run", action="store_true", help="Mostra seleção, sem acessar APIs nem gravar arquivos")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 50:
        parser.error("Use --limit entre 1 e 50 (consultas pontuais, não coleta em massa).")
    if args.per_genre < 1 or args.min_chars < 1 or args.ol_delay < 1.1:
        parser.error("Use --per-genre >= 1, --min-chars >= 1 e --ol-delay >= 1.1.")
    allowed = {norm(g): g for g in OCEANOS_GENRES}
    requested = [g.strip() for g in args.genres.split(",") if g.strip()]
    if not requested or any(norm(g) not in allowed for g in requested):
        parser.error(f"Gênero inválido. Opções: {OCEANOS_GENRES}")
    genres = list(dict.fromkeys(allowed[norm(g)] for g in requested))
    raw = pd.read_csv(args.input, compression="infer", dtype=str)
    books = select_books(raw, {norm(g) for g in genres})
    if args.dry_run:
        for g in genres:
            sample = books.loc[books["genero_livro"].astype(str).map(norm) == norm(g)].head(3)
            print(f"\n{g}: {len(books.loc[books['genero_livro'].astype(str).map(norm) == norm(g)])} candidatos distintos")
            for _, row in sample.iterrows():
                print(f"  [{row['priority_tier']}] {row['titulo_livro']} — {row['nome_autor']}")
        return

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit_path = out / "enrichment_audit.csv"
    catalog_path = out / "catalog_enriched_candidates.csv"
    balanced_path = out / "catalog_balanced.csv"
    audit = load_history(audit_path, AUDIT_COLUMNS)
    catalog = load_history(catalog_path, CATALOG_COLUMNS)
    already = set(
        audit.loc[
            audit["status"].map(
                lambda s: should_skip_old(s, args.skip_google) and not (args.recheck_partials and s == "partial_not_found")
            ), "book_id"
        ]
    )
    queues = {
        genre: deque(
            row for row in books.loc[books["genero_livro"].astype(str).map(norm) == norm(genre)].to_dict("records")
            if row["book_id"] not in already
        )
        for genre in genres
    }
    found = {g: int((catalog["genre"].astype(str).map(norm) == norm(g)).sum()) for g in genres}
    attempts = {g: 0 for g in genres}
    api_key = os.environ.get("GOOGLE_BOOKS_API_KEY", "")
    user_agent = f"BookMatchAI/0.2 ({args.contact_email})" if args.contact_email else "BookMatchAI/0.2 (educational prototype)"
    google_available = not args.skip_google
    checked = 0
    with httpx.Client(headers={"User-Agent": user_agent, "Accept": "application/json"}, follow_redirects=True) as client:
        while checked < args.limit:
            genre = next_genre(genres, queues, found, attempts, args.per_genre)
            if genre is None:
                break
            row = queues[genre].popleft()
            attempts[genre] += 1
            bid = row["book_id"]
            title, author = str(row["titulo_livro"]).strip(), str(row["nome_autor"]).strip()
            priority = row["priority_tier"]
            print(f"[{checked+1}/{args.limit}] [{genre}: {found[genre]}/{args.per_genre}] ({priority}) {title} — {author}", flush=True)

            google = LookupResult("skipped", "Google Books desativado ou limitado nesta execução")
            ol = LookupResult("skipped", "Open Library não consultada")
            if google_available:
                try:
                    google = google_lookup(client, title, author, args.min_chars, api_key)
                except (httpx.HTTPError, ValueError) as exc:
                    google = error_lookup(exc, "Google Books")
                    if google.status == "rate_limited":
                        google_available = False
                        print("  Google Books: HTTP 429. Suspendendo Google nesta execução.")

            matched = google.record
            if matched is None:
                try:
                    ol = open_library_lookup(client, title, author, args.min_chars, args.ol_delay)
                except (httpx.HTTPError, ValueError) as exc:
                    ol = error_lookup(exc, "Open Library")
                matched = ol.record

            status = overall_status(google, ol)
            diagnostics = {}
            for provider, result in (("google", google), ("open_library", ol)):
                diagnostics.update({
                    f"{provider}_status": result.status,
                    f"{provider}_detail": result.detail,
                    f"{provider}_hits": result.hits,
                    f"{provider}_matches": result.matches,
                    f"{provider}_description_chars": result.description_chars,
                })
            detail = f"Google: {google.status}; Open Library: {ol.status}"
            now = utc_now()
            if matched is not None:
                data = {
                    "book_id": bid, "title": title, "authors": author, "genre": genre,
                    "oceanos_year": row.get("ano", ""),
                    "publisher": row.get("nome_editora", "") if pd.notna(row.get("nome_editora")) else "",
                    **matched,
                    "description_chars": len(matched["description"]),
                    "retrieved_at_utc": now,
                    "usage_status": "pending_rights_review",
                }
                catalog = pd.concat([catalog, pd.DataFrame([data])], ignore_index=True)
                catalog = catalog.drop_duplicates("book_id", keep="last")
                found[genre] += 1
            new_audit = {
                "book_id": bid, "title": title, "authors": author, "genre": genre,
                "priority_tier": priority,
                "status": status, "source": matched["description_source"] if matched else "",
                "detail": detail, "checked_at_utc": now,
                **diagnostics,
            }
            audit = pd.concat([audit, pd.DataFrame([new_audit])], ignore_index=True)
            audit = audit.drop_duplicates("book_id", keep="last")
            # Preserva progresso após cada obra, inclusive antes de qualquer erro futuro.
            audit.to_csv(audit_path, index=False)
            catalog.to_csv(catalog_path, index=False)
            balanced_catalog(catalog, genres, args.per_genre).to_csv(balanced_path, index=False)
            checked += 1
            print(f"  -> {status} | Google: {google.status} | OL: {ol.status}", flush=True)
            if ol.status == "rate_limited":
                print("Open Library: HTTP 429.")
                break

    balanced = balanced_catalog(catalog, genres, args.per_genre)
    balanced.to_csv(balanced_path, index=False)
    print(f"\nTentativas nesta execução: {checked}")
    print(f"Catálogo candidato acumulado: {len(catalog)}")
    for g in genres:
        count = int((balanced["genre"].astype(str).map(norm) == norm(g)).sum())
        print(f"  {g}: {count}/{args.per_genre} livros com descrição")
    print(f"Catálogo balanceado: {balanced_path}")
    print(f"Auditoria: {audit_path}")
    print("Descrição coletada NÃO equivale a licença para publicação. Verifique direitos antes de redistribuir.")


if __name__ == "__main__":
    main()