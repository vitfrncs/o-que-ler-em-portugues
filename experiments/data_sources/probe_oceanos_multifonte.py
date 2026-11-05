"""Piloto auditavel de enriquecimento Oceanos: Apple Books + Google opcional + editoras.

    python scripts/probe_oceanos_multifonte.py --input data/raw/oceanos.csv --per-genre 6
"""
from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus

import httpx
import pandas as pd

GENRES = ("Poesia", "Romance", "Conto", "Crônica", "Dramaturgia")


def normalize(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", value))


def title_match(expected: str, actual: str) -> bool:
    exp, got = normalize(expected), normalize(actual)
    if not exp or not got:
        return False
    # Aceita um subtitulo acrescentado, mas nao aceita outro titulo apenas parecido.
    base = re.split(r"\s*[:–—]\s*|\s+-\s+", actual, maxsplit=1)[0]
    return exp == got or exp == normalize(base)


def author_match(expected: str, actual: str) -> bool:
    a, b = normalize(expected), normalize(actual)
    return bool(a and b and (a == b or sorted(a.split()) == sorted(b.split())))


def clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value))).strip()


def select_sample(df: pd.DataFrame, per_genre: int) -> pd.DataFrame:
    necessary = {"titulo_livro", "nome_autor", "genero_livro", "ano", "nome_editora"}
    missing = necessary - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    rows = df.dropna(subset=["titulo_livro", "nome_autor", "genero_livro"]).copy()
    rows = rows[rows["genero_livro"].isin(GENRES)].copy()
    rows["priority"] = 3
    for col, value in [("indicador_semifinalista", 2), ("indicador_finalista", 1), ("indicador_vencedor", 0)]:
        if col in rows:
            rows.loc[rows[col].astype(str).str.casefold().eq("sim"), "priority"] = value
    rows["sort_year"] = pd.to_numeric(rows["ano"], errors="coerce").fillna(0)
    rows["book_id"] = [
        hashlib.sha256((normalize(t) + "|" + normalize(a)).encode()).hexdigest()[:16]
        for t, a in zip(rows["titulo_livro"], rows["nome_autor"])
    ]
    rows = rows.sort_values(["priority", "sort_year"], ascending=[True, False], kind="stable")
    rows = rows.drop_duplicates("book_id")
    return pd.concat([rows[rows["genero_livro"] == g].head(per_genre) for g in GENRES], ignore_index=True)


def parse_apple_results(payload: dict, title: str, author: str, min_chars: int) -> dict:
    items = payload.get("results") or []
    matches = [x for x in items if title_match(title, x.get("trackName", ""))
               and author_match(author, x.get("artistName", ""))]
    for item in matches:
        desc = clean_text(item.get("description", ""))
        if len(desc) >= min_chars:
            return {"status": "found", "description": desc, "url": item.get("trackViewUrl", ""),
                    "matched_title": item.get("trackName", ""), "matched_author": item.get("artistName", "")}
    status = ("no_results" if not items else "no_match" if not matches else
              "short_or_missing_description")
    return {"status": status, "description": "", "url": "", "matched_title": "", "matched_author": ""}


def parse_google_results(payload: dict, title: str, author: str, min_chars: int) -> dict:
    items = payload.get("items") or []
    matches = [x.get("volumeInfo", {}) for x in items
               if title_match(title, x.get("volumeInfo", {}).get("title", ""))
               and any(author_match(author, name) for name in x.get("volumeInfo", {}).get("authors", []))]
    for info in matches:
        desc = clean_text(info.get("description", ""))
        if info.get("language") not in (None, "pt"):
            continue
        if len(desc) >= min_chars:
            return {"status": "found", "description": desc, "url": info.get("infoLink", ""),
                    "matched_title": info.get("title", ""), "matched_author": "; ".join(info.get("authors", []))}
    status = "no_results" if not items else "no_match" if not matches else "short_or_missing_description"
    return {"status": status, "description": "", "url": "", "matched_title": "", "matched_author": ""}


def request_json(client: httpx.Client, url: str, params: dict) -> dict:
    response = client.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def publisher_search_url(row: pd.Series) -> str:
    q = f'{row["titulo_livro"]} {row["nome_autor"]} {row.get("nome_editora", "")}'
    return "https://www.google.com/search?q=" + quote_plus(q)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--per-genre", type=int, default=6)
    parser.add_argument("--output-dir", default="data/interim/oceanos/piloto_multifonte")
    parser.add_argument("--min-chars", type=int, default=120)
    parser.add_argument("--country", choices=["BR", "PT"], default="BR")
    parser.add_argument("--delay", type=float, default=4.0, help="Segundos entre chamadas Apple")
    parser.add_argument("--use-google", action="store_true", help="Exige GOOGLE_BOOKS_API_KEY")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.per_genre < 1 or args.min_chars < 1 or args.delay < 3.2:
        parser.error("Use --per-genre >= 1, --min-chars >= 1 e --delay >= 3.2")
    api_key = os.environ.get("GOOGLE_BOOKS_API_KEY", "")
    if args.use_google and not api_key:
        parser.error("Defina GOOGLE_BOOKS_API_KEY antes de usar --use-google")

    sample = select_sample(pd.read_csv(args.input, compression="infer", dtype=str), args.per_genre)
    if args.dry_run:
        print(sample[["genero_livro", "titulo_livro", "nome_autor", "priority"]].to_string(index=False))
        return

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit_path = out / "audit.csv"
    descriptions_path = out / "descriptions_candidates.csv"
    queue_path = out / "publisher_review_queue.csv"
    audit = pd.read_csv(audit_path, dtype=str).fillna("") if audit_path.exists() else pd.DataFrame()
    descriptions = pd.read_csv(descriptions_path, dtype=str).fillna("") if descriptions_path.exists() else pd.DataFrame()
    completed = (set(audit.loc[(audit["status"] == "found") | ((audit["google_status"] != "skipped") if args.use_google else audit["status"].isin(["no_results", "no_match", "short_or_missing_description"])), "book_id"]) if not audit.empty else set())
    google_available = args.use_google
    with httpx.Client(headers={"User-Agent": "BookMatchAI/0.3 (educational project)"}, follow_redirects=True) as client:
        for index, row in sample.iterrows():
            bid = row["book_id"]
            if bid in completed:
                continue
            title, author = row["titulo_livro"], row["nome_autor"]
            print(f'[{index+1}/{len(sample)}] {row["genero_livro"]}: {title} — {author}', flush=True)
            time.sleep(args.delay)
            try:
                data = request_json(client, "https://itunes.apple.com/search", {
                    "term": f"{title} {author}", "country": args.country,
                    "media": "ebook", "entity": "ebook", "limit": 15,
                })
                apple = parse_apple_results(data, title, author, args.min_chars)
            except httpx.HTTPStatusError as exc:
                status = "rate_limited" if exc.response.status_code == 429 else "api_error"
                apple = {"status": status, "description": "", "url": "", "detail": f"HTTP {exc.response.status_code}"}
            except (httpx.HTTPError, ValueError) as exc:
                apple = {"status": "api_error", "description": "", "url": "", "detail": type(exc).__name__}
            result, source = apple, "apple_books"
            google_status = "skipped"
            if apple["status"] == "rate_limited":
                print("  Apple retornou 429. Parando o piloto para respeitar o limite.")
            elif apple["status"] != "found" and google_available:
                try:
                    g = request_json(client, "https://www.googleapis.com/books/v1/volumes", {
                        "q": f'intitle:"{title}" inauthor:"{author}"',
                        "key": api_key, "maxResults": 10, "printType": "books",
                    })
                    gr = parse_google_results(g, title, author, args.min_chars)
                    google_status = gr["status"]
                    if gr["status"] == "found":
                        result, source = gr, "google_books"
                except httpx.HTTPStatusError as exc:
                    google_status = f"http_{exc.response.status_code}"
                    if exc.response.status_code == 429:
                        google_available = False
                except (httpx.HTTPError, ValueError) as exc:
                    google_status = type(exc).__name__
            record = {
                "book_id": bid, "title": title, "authors": author, "genre": row["genero_livro"],
                "priority": str(row["priority"]), "publisher": row.get("nome_editora", ""),
                "publisher_site": row.get("site_editora", ""), "apple_status": apple["status"],
                "google_status": google_status,
                "status": result["status"], "source": source if result["status"] == "found" else "",
                "source_url": result.get("url", ""), "detail": apple.get("detail", ""),
            }
            audit = pd.concat([audit, pd.DataFrame([record])], ignore_index=True)
            audit = audit.drop_duplicates("book_id", keep="last")
            if result["status"] == "found":
                description_record = {
                    "book_id": bid, "title": title, "authors": author, "genre": row["genero_livro"],
                    "description": result["description"], "source": source,
                    "source_url": result.get("url", ""),
                    "usage_status": "pending_rights_review", "review_status": "pending",
                }
                descriptions = pd.concat([descriptions, pd.DataFrame([description_record])], ignore_index=True)
                descriptions = descriptions.drop_duplicates("book_id", keep="last")
            audit.to_csv(audit_path, index=False)
            if not descriptions.empty:
                descriptions.to_csv(descriptions_path, index=False)
            print(f'  -> Apple: {apple["status"]} | Google: {google_status} | Final: {result["status"]}')
            if apple["status"] == "rate_limited":
                break

    pending = sample[~sample["book_id"].isin(descriptions["book_id"] if not descriptions.empty else [])].copy()
    pending["publisher_search_url"] = pending.apply(publisher_search_url, axis=1)
    pending["publisher_page_url"] = ""
    pending["description_original"] = ""
    pending["review_status"] = "pending"
    pending[["book_id", "genero_livro", "titulo_livro", "nome_autor", "nome_editora",
             "site_editora", "publisher_search_url", "publisher_page_url",
             "description_original", "review_status"]].to_csv(queue_path, index=False)
    print(f"\nCandidatos selecionados: {len(sample)}; descricoes encontradas: {len(descriptions)}")
    print(f"Auditoria: {audit_path}\nDescricoes (uso nao aprovado): {descriptions_path}\nFila para editoras: {queue_path}")


if __name__ == "__main__":
    main()
