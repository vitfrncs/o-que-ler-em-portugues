"""BookMatch AI — Oceanos: enriquecimento Apple Books + editoras (uma execução).

Metas por gênero, cadastro consolidado de editoras, persistência CSV e auditoria.
O status 'candidate' NÃO concede autorização de reutilização pública.

Uso na raiz do repositório:
  python scripts/enrich_oceanos_auto.py --input data/raw/oceanos.csv --per-genre 100 --limit 15
"""
from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import os
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import pandas as pd
from bs4 import BeautifulSoup

# Carrega .env no computador da usuária quando python-dotenv está disponível.
# Nunca coloca a chave em CSV nem no código-fonte.
try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()

GENRES = ("Poesia", "Romance", "Conto", "Crônica", "Dramaturgia")
APPLE_API = "https://itunes.apple.com/search"
GOOGLE_API = "https://www.googleapis.com/books/v1/volumes"
USER_AGENT = "BookMatchAI-Research/0.5 (educational catalog enrichment; contact: configure-email)"
REVIEW_STATUSES = {"needs_review", "mismatch_needs_review"}


def normalize(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    t = unicodedata.normalize("NFKD", str(value)).casefold()
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return " ".join(re.findall(r"\w+", t))


def book_id(title: str, author: str) -> str:
    key = normalize(title) + "|" + normalize(author)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def title_matches(expected: str, actual: str) -> bool:
    exp, got = normalize(expected), normalize(actual)
    if not exp or not got:
        return False
    prefix = re.split(r"\s*[:–—]\s*|\s+-\s+|\s*\|\s*", str(actual), maxsplit=1)[0]
    return exp == got or exp == normalize(prefix)


def author_matches(expected: str, actual: str) -> bool:
    a, b = normalize(expected), normalize(actual)
    return bool(a and b and (a == b or sorted(a.split()) == sorted(b.split())))


def clean_text(text: object) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", html.unescape(BeautifulSoup(text, "html.parser").get_text(" "))).strip()


def quality_status(text: str, minimum: int) -> str:
    """Heurística de triagem; não é verificação bibliográfica nem jurídica."""
    content = text.strip()
    if len(content) < minimum or len(content.split()) < 25:
        return "insufficient"
    if len(content) > 4500 or content.startswith(("«", "“", '"', "‘")):
        return "needs_review"
    return "candidate"


def select_oceanos(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, compression="infer").fillna("")
    mandatory = {"titulo_livro", "nome_autor", "genero_livro"}
    if not mandatory.issubset(df.columns):
        raise ValueError(f"Colunas ausentes: {sorted(mandatory - set(df.columns))}")
    df = df[df["genero_livro"].isin(GENRES)].copy()
    df = df[(df["titulo_livro"].str.strip() != "") & (df["nome_autor"].str.strip() != "")]
    df["book_id"] = [book_id(t, a) for t, a in zip(df["titulo_livro"], df["nome_autor"])]
    df["priority"] = 3
    for col, tier in (("indicador_semifinalista", 2), ("indicador_finalista", 1), ("indicador_vencedor", 0)):
        if col in df:
            df.loc[df[col].str.strip().str.casefold().eq("sim"), "priority"] = tier
    years = df["ano"] if "ano" in df.columns else pd.Series("0", index=df.index)
    df["sort_year"] = pd.to_numeric(years, errors="coerce").fillna(0)
    df = df.sort_values(["priority", "sort_year"], ascending=[True, False], kind="stable")
    df = df.drop_duplicates("book_id", keep="first")
    return df


def interleave_genres(df: pd.DataFrame):
    """Alterna gêneros; mantém prioridade por premiação dentro de cada um."""
    groups = {g: df[df["genero_livro"] == g].to_dict("records") for g in GENRES}
    for pos in range(max(len(v) for v in groups.values())):
        for genre in GENRES:
            if pos < len(groups[genre]):
                yield groups[genre][pos]


def normal_publisher_base(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return ""
    # O catálogo inclui observações anexadas ao site, por exemplo:
    # "www.edicoeshumus.pt (em manutenção e reorganização até 15MAI21)".
    # Removemos somente observações finais entre parênteses, sem tentar
    # inventar um domínio quando o campo está malformado.
    address = re.sub(r"\s+\([^)]*\)\s*$", "", raw.strip()).strip()
    if not address.startswith(("https://", "http://")):
        address = "https://" + address
    try:
        parsed = urlparse(address)
        host = (parsed.hostname or "").lower()
        ascii_host = host.encode("idna").decode("ascii")
    except (ValueError, UnicodeError):
        return ""
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return ""
    # Verifica se o hostname é sintaticamente válido antes de chamar httpx.
    labels = ascii_host.split(".")
    if (len(ascii_host) > 253 or len(labels) < 2
            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                   for label in labels)):
        return ""
    if host == "localhost" or host.endswith(".local"):
        return ""
    try:
        if not ipaddress.ip_address(host).is_global:
            return ""
    except ValueError:
        pass
    return f"https://{parsed.netloc}"


def canonical_publisher_host(base: str) -> str:
    """Domínio normalizado para comparar URLs com/sem www."""
    return (urlparse(base).hostname or "").lower().removeprefix("www.")


def build_publisher_site_registry(df: pd.DataFrame, min_support: int = 2) -> pd.DataFrame:
    """Consolida sites por nome EXATO normalizado de editora.

    Só infere um endereço quando existe um único hostname entre os registros
    válidos da editora, apoiado por >= min_support livros distintos.
    Múltiplos hostnames geram 'conflict': nunca escolhemos um arbitrariamente.
    """
    if min_support < 1:
        raise ValueError("min_support precisa ser >= 1")
    if not {"titulo_livro", "nome_autor"}.issubset(df.columns):
        raise ValueError("CSV sem título ou autor")
    df = df.copy()
    for col in ("nome_editora", "site_editora"):
        if col not in df.columns:
            df[col] = ""
    rows = df[["nome_editora", "site_editora", "titulo_livro", "nome_autor"]].copy().fillna("")
    rows["publisher_key"] = rows["nome_editora"].map(normalize)
    rows = rows[rows["publisher_key"].ne("")].copy()
    rows["site_valid"] = rows["site_editora"].map(normal_publisher_base)
    rows["host"] = rows["site_valid"].map(canonical_publisher_host)
    rows["source_book_id"] = [book_id(t, a) for t, a in zip(rows["titulo_livro"], rows["nome_autor"])]
    results = []
    for publisher_key, group in rows.groupby("publisher_key", sort=True):
        by_host = group[group["host"].ne("")].groupby("host")
        support = {host: g["source_book_id"].nunique() for host, g in by_host}
        if not support:
            status, inferred = "no_valid_site", ""
        elif len(support) > 1:
            status, inferred = "conflict", ""
        elif next(iter(support.values())) < min_support:
            status, inferred = "low_support", ""
        else:
            status, inferred = "consistent", "https://" + next(iter(support))
        results.append({
            "publisher_key": publisher_key,
            "publisher_example": group.iloc[0]["nome_editora"],
            "site_status": status,
            "inferred_site": inferred,
            "domains_seen": ";".join(sorted(support)),
            "unique_domains": len(support),
            "supporting_books": sum(support.values()),
        })
    return pd.DataFrame(results, columns=[
        "publisher_key", "publisher_example", "site_status", "inferred_site",
        "domains_seen", "unique_domains", "supporting_books",
    ])


def apply_publisher_site_registry(selected: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    """Preenche apenas sites ausentes/invalidos. Preserva os originais e a origem."""
    result = selected.copy()
    if "site_editora" not in result.columns:
        result["site_editora"] = ""
    result["publisher_site_original"] = result["site_editora"].fillna("")
    result["publisher_site_resolved"] = result["publisher_site_original"].map(normal_publisher_base)
    result["publisher_site_source"] = "missing"
    result.loc[result["publisher_site_resolved"].ne(""), "publisher_site_source"] = "original"
    publisher_keys = result["nome_editora"].map(normalize)
    inferred = registry.set_index("publisher_key")["inferred_site"].to_dict()
    statuses = registry.set_index("publisher_key")["site_status"].to_dict()
    need_site = result["publisher_site_resolved"].eq("")
    suggested_sites = publisher_keys.map(inferred).fillna("")
    fill_mask = need_site & suggested_sites.ne("")
    result.loc[fill_mask, "publisher_site_resolved"] = suggested_sites[fill_mask]
    result.loc[fill_mask, "publisher_site_source"] = "inferred"
    conflict = need_site & ~fill_mask & publisher_keys.map(statuses).eq("conflict")
    result.loc[conflict, "publisher_site_source"] = "conflict"
    return result


def same_publisher(url: str, base: str) -> bool:
    parsed, ref = urlparse(url), urlparse(base)
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    expected = (ref.hostname or "").lower().removeprefix("www.")
    return bool(parsed.scheme == "https" and hostname and hostname == expected
                and not parsed.username and not parsed.password)


def iter_json_nodes(value: object):
    if isinstance(value, list):
        for item in value:
            yield from iter_json_nodes(item)
    elif isinstance(value, dict):
        yield value
        for key in ("@graph", "mainEntity", "itemListElement"):
            if key in value:
                yield from iter_json_nodes(value[key])


def extract_descriptions(page: str, minimum: int) -> list[dict]:
    soup = BeautifulSoup(page, "html.parser")
    results, seen = [], set()

    def add(method, value):
        content = clean_text(value)
        if len(content) < minimum or content.casefold() in seen:
            return
        seen.add(content.casefold())
        results.append({"description": content, "extraction_method": method})

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        for node in iter_json_nodes(data):
            types = node.get("@type", [])
            types = [types] if isinstance(types, str) else types if isinstance(types, list) else []
            if any(str(t).split("/")[-1] in {"Book", "Product"} for t in types):
                add("json_ld", node.get("description"))
    for method, selector in (
        ("html_woocommerce", ".woocommerce-Tabs-panel--description"),
        ("html_itemprop", '[itemprop="description"]'),
        ("html_tab_description", "#tab-description"),
        ("og_description", 'meta[property="og:description"]'),
        ("meta_description", 'meta[name="description"]'),
    ):
        element = soup.select_one(selector)
        if element is None:
            continue
        if element.name == "meta":
            add(method, element.get("content", ""))
        else:
            for unwanted in element.select("script,style"):
                unwanted.decompose()
            add(method, element.get_text(" ", strip=True))
    return results


def page_matches(page: str, title: str, author: str) -> str:
    """verified, uncertain_author ou mismatch. Nunca aceita apenas título no rodapé."""
    soup = BeautifulSoup(page, "html.parser")
    headings = [n.get_text(" ", strip=True) for n in soup.select("h1")[:5]]
    meta = soup.select_one('meta[property="og:title"]')
    if meta:
        headings.append(meta.get("content", ""))
    if not any(title_matches(title, name) for name in headings):
        return "mismatch"
    all_text = normalize(soup.get_text(" ", strip=True))
    author_norm = normalize(author)
    if author_norm and re.search(r"(?<!\w)" + re.escape(author_norm) + r"(?!\w)", all_text):
        return "verified"
    return "uncertain_author"


def best_description(items: list[dict], minimum: int) -> dict | None:
    order = {"json_ld": 4, "html_woocommerce": 3, "html_itemprop": 3,
             "html_tab_description": 2, "og_description": 1, "meta_description": 0, "apple_api": 3,
             "google_books_api": 3}
    chosen = []
    for item in items:
        text = item.get("description", "")
        quality = quality_status(text, minimum)
        if quality == "insufficient":
            continue
        chosen.append((quality == "candidate", order.get(item.get("extraction_method", ""), 0),
                       min(len(text), 2400), item, quality))
    if not chosen:
        return None
    _, _, _, item, quality = max(chosen, key=lambda value: value[:3])
    return {**item, "quality_status": quality}


def parse_apple(payload: dict, title: str, author: str, minimum: int) -> dict:
    rows = payload.get("results") or []
    matched = [r for r in rows if title_matches(title, r.get("trackName", ""))
               and author_matches(author, r.get("artistName", ""))]
    texts = [{"description": clean_text(r.get("description")), "source": "apple_books",
              "source_url": r.get("trackViewUrl", ""), "extraction_method": "apple_api",
              "match_status": "verified"} for r in matched]
    chosen = best_description(texts, minimum)
    if chosen:
        return {"status": "found", **chosen}
    return {"status": "no_results" if not rows else "no_match" if not matched else "no_description"}


def parse_google(payload: dict, title: str, author: str, minimum: int) -> dict:
    rows = payload.get("items") or []
    matched = [r.get("volumeInfo", {}) for r in rows if
               title_matches(title, r.get("volumeInfo", {}).get("title", "")) and
               any(author_matches(author, a) for a in r.get("volumeInfo", {}).get("authors", []))]
    texts = [{"description": clean_text(info.get("description", "")), "source": "google_books",
              "source_url": info.get("infoLink", ""), "extraction_method": "google_books_api",
              "match_status": "verified"} for info in matched if info.get("language") in ("pt", None)]
    chosen = best_description(texts, minimum)
    if chosen:
        return {"status": "found", **chosen}
    return {"status": "no_results" if not rows else "no_match" if not matched else "no_description"}


def safely_get(client: httpx.Client, url: str, *, params: dict | None = None, headers: dict | None = None,
               redirects: bool = False):
    try:
        response = client.get(url, params=params, headers=headers, timeout=18, follow_redirects=redirects)
        if response.status_code == 429:
            return None, "rate_limited"
        if response.is_redirect:
            return response, "ok"
        response.raise_for_status()
        return response, "ok"
    except httpx.HTTPStatusError as exc:
        return None, f"http_{exc.response.status_code}"
    except (httpx.HTTPError, httpx.InvalidURL, ValueError) as exc:
        # InvalidURL não herda de HTTPError; sem esta captura, uma linha
        # problemática do CSV pode interromper toda a execução.
        return None, f"error_{type(exc).__name__}"


class PublisherClient:
    def __init__(self, client: httpx.Client, delay: float):
        self.client = client
        self.delay = delay
        self.robot_parsers: dict[str, RobotFileParser | None] = {}
        self.robot_status: dict[str, str] = {}
        self.last_request: dict[str, float] = {}
        self.blocked_hosts: set[str] = set()

    def _permissions(self, url: str) -> tuple[bool, str, float]:
        parsed = urlparse(url)
        host = parsed.netloc
        if host not in self.robot_parsers:
            robots_url = f"https://{host}/robots.txt"
            response, status = safely_get(self.client, robots_url)
            # Segue redirecionamentos de robots.txt SOMENTE no mesmo domínio editorial.
            for _ in range(3):
                if status != "ok" or response is None or not response.is_redirect:
                    break
                target = urljoin(robots_url, response.headers.get("location", ""))
                if not same_publisher(target, f"https://{host}"):
                    status = "robots_external_redirect"
                    break
                robots_url = target
                response, status = safely_get(self.client, robots_url)
            if status == "ok" and response is not None and response.is_redirect:
                status = "robots_redirect_loop"
            if status == "http_404":
                self.robot_parsers[host] = None
                self.robot_status[host] = "robots_missing"
            elif status != "ok":
                self.robot_parsers[host] = None
                self.robot_status[host] = f"robots_{status}"
                self.blocked_hosts.add(host)
            else:
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                self.robot_parsers[host] = parser
                self.robot_status[host] = "robots_checked"
        if host in self.blocked_hosts:
            reason = self.robot_status[host]
            return False, ("publisher_rate_limited" if reason in ("robots_checked", "robots_missing") else reason), 0.0
        parser = self.robot_parsers[host]
        if parser is not None and not parser.can_fetch(USER_AGENT, url):
            return False, "robots_disallowed", 0.0
        delay = parser.crawl_delay(USER_AGENT) if parser is not None else None
        return True, self.robot_status[host], float(delay or 0)

    def fetch(self, url: str, base: str) -> tuple[str, str]:
        """Segue até 3 redirecionamentos apenas no domínio editorial permitido."""
        for _ in range(4):
            if not same_publisher(url, base):
                return "", "not_publisher_domain"
            allowed, reason, robot_delay = self._permissions(url)
            if not allowed:
                return "", reason
            host = urlparse(url).netloc
            wait = max(self.delay, robot_delay) - (time.monotonic() - self.last_request.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            self.last_request[host] = time.monotonic()
            response, status = safely_get(self.client, url)
            if status == "rate_limited":
                self.blocked_hosts.add(host)
            if status != "ok":
                return "", status
            if response.is_redirect:
                location = response.headers.get("location", "")
                if not location:
                    return "", "redirect_without_location"
                url = urljoin(url, location)
                continue
            content_type = response.headers.get("content-type", "").lower()
            if "/wp-json/" in urlparse(url).path and ("application/json" in content_type or response.text.lstrip().startswith("[")):
                return response.text, "ok"
            if "text/html" not in content_type and "<html" not in response.text[:500].lower():
                return "", "not_html"
            return response.text, "ok"
        return "", "too_many_redirects"

    def find_pages(self, base: str, title: str, known_url: str = "") -> tuple[list[str], str]:
        if known_url and same_publisher(known_url, base):
            return [known_url], "known_page"
        found = []
        # Busca oficial do WordPress, caso a editora a ofereça.
        wp_url = urljoin(base, "/wp-json/wp/v2/search") + "?search=" + quote(title) + "&per_page=10"
        response, wp_status = self.fetch(wp_url, base)
        if wp_status == "ok":
            try:
                hits = json.loads(response)
                for hit in hits if isinstance(hits, list) else []:
                    url = hit.get("url", "")
                    if (title_matches(title, clean_text(hit.get("title", "")))
                            and same_publisher(url, base) and url not in found):
                        found.append(url)
            except (TypeError, ValueError):
                pass
        if found:
            return found[:3], "wordpress_search"
        # Busca interna do site: não depende de scraping de resultados do Google.
        for query in ("?s=" + quote(title), "?post_type=product&s=" + quote(title)):
            search_url = base + "/" + query
            page, status = self.fetch(search_url, base)
            if status != "ok":
                continue
            soup = BeautifulSoup(page, "html.parser")
            for element in soup.select("a[href]"):
                label = element.get_text(" ", strip=True)
                url = urljoin(base, element.get("href", ""))
                if title_matches(title, label) and same_publisher(url, base) and url not in found:
                    found.append(url)
                    if len(found) >= 3:
                        break
            if found:
                return found[:3], "site_search"
        return [], f"no_page;wp:{wp_status}"


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("") if path.exists() and path.stat().st_size else pd.DataFrame()


def atomic_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(temp_path, index=False)
    temp_path.replace(path)


def known_editorial_pages(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    if not {"book_id", "publisher_page_url"}.issubset(df.columns):
        raise ValueError("A fila editorial precisa de book_id e publisher_page_url")
    return {r.book_id: r.publisher_page_url.strip() for r in df.itertuples(index=False)
            if r.publisher_page_url.strip().startswith("https://")}


def count_accepted(candidates: pd.DataFrame) -> dict[str, int]:
    if candidates.empty:
        return {}
    valid = candidates[(candidates["quality_status"].eq("candidate")) &
                       (candidates["match_status"].eq("verified"))]
    return valid.groupby("genre")["book_id"].nunique().to_dict()


def export_outputs(out: Path, audit: pd.DataFrame, candidates: pd.DataFrame, quota: int) -> None:
    audit_fields = ["book_id", "title", "authors", "genre", "priority", "publisher", "publisher_site", "publisher_site_resolved", "publisher_site_source",
                    "apple_status", "google_status", "editorial_status", "status", "quality_status",
                    "match_status", "source", "source_url", "detail"]
    candidate_fields = ["book_id", "title", "authors", "genre", "description", "source", "source_url",
                        "extraction_method", "quality_status", "match_status", "usage_status"]
    if audit.empty:
        audit = pd.DataFrame(columns=audit_fields)
    if candidates.empty:
        candidates = pd.DataFrame(columns=candidate_fields)
    atomic_csv(audit, out / "audit.csv")
    atomic_csv(candidates, out / "descriptions_candidates.csv")
    # Corpus automático inclui apenas candidatos com boa qualidade heurística e título+autor confirmados.
    experimental = candidates[(candidates["quality_status"] == "candidate") &
                              (candidates["match_status"] == "verified")].copy()
    atomic_csv(experimental, out / "catalog_experimental.csv")
    manual = candidates[(candidates["quality_status"] != "candidate") |
                        (candidates["match_status"] != "verified")].copy()
    atomic_csv(manual, out / "needs_review.csv")
    accepted = count_accepted(candidates)
    summary = pd.DataFrame([{"genre": g, "target": quota, "candidate_count": accepted.get(g, 0),
                             "checked": int((audit["genre"] == g).sum()),
                             "remaining": max(0, quota - accepted.get(g, 0))} for g in GENRES])
    atomic_csv(summary, out / "summary.csv")


def import_previous_pilots(source_df: pd.DataFrame, pilot_dir: Path, editorial_file: Path,
                           minimum: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reaproveita resultados anteriores sem marcar textos editoriais como verificados.

    Importa somente registros reconhecidos no Oceanos, identificados pelo mesmo book_id.
    Não reutiliza dados de outras fontes de procedência desconhecida.
    """
    by_id = {r["book_id"]: r for r in source_df.to_dict("records")}
    records, audits = [], []
    inputs = [(pilot_dir / "descriptions_candidates.csv", "apple_pilot"),
              (editorial_file, "editorial_preview")]
    for path, origin in inputs:
        if not path.exists():
            continue
        data = pd.read_csv(path, dtype=str).fillna("")
        if "book_id" not in data.columns:
            continue
        for bid, rows in data.groupby("book_id", sort=False):
            reference = by_id.get(bid)
            if reference is None:
                continue
            choices = []
            for row in rows.to_dict("records"):
                description = clean_text(row.get("description") or row.get("description_candidate"))
                if len(description) < minimum:
                    continue
                # No piloto Apple o título e o autor foram conferidos na resposta da API.
                if origin == "apple_pilot":
                    if (not title_matches(reference["titulo_livro"], row.get("title", ""))
                            or not author_matches(reference["nome_autor"], row.get("authors", ""))):
                        continue
                    source = row.get("source", "apple_books") or "apple_books"
                    matched = "verified"
                    method = "apple_api" if source == "apple_books" else "google_books_api"
                else:
                    if not title_matches(reference["titulo_livro"], row.get("title", "")):
                        continue
                    source, matched = "publisher", "uncertain_author"
                    method = row.get("extraction_method") or "json_ld"
                choices.append({"description": description, "source": source,
                                "source_url": row.get("source_url", ""), "extraction_method": method,
                                "match_status": matched})
            chosen = best_description(choices, minimum)
            if not chosen:
                continue
            status = "candidate" if (chosen["quality_status"] == "candidate"
                                     and chosen["match_status"] == "verified") else "needs_review"
            records.append({"book_id": bid, "title": reference["titulo_livro"],
                            "authors": reference["nome_autor"], "genre": reference["genero_livro"],
                            "description": chosen["description"], "source": chosen["source"],
                            "source_url": chosen["source_url"], "extraction_method": chosen["extraction_method"],
                            "quality_status": chosen["quality_status"],
                            "match_status": chosen["match_status"],
                            "usage_status": "pending_rights_review"})
            audits.append({"book_id": bid, "title": reference["titulo_livro"],
                           "authors": reference["nome_autor"], "genre": reference["genero_livro"],
                           "priority": str(reference["priority"]),
                           "publisher": reference.get("nome_editora", ""),
                           "publisher_site": reference.get("site_editora", ""),
                           "apple_status": "imported" if origin == "apple_pilot" else "skipped",
                           "google_status": "skipped", "editorial_status": "imported" if origin == "editorial_preview" else "skipped",
                           "status": status, "quality_status": chosen["quality_status"],
                           "match_status": chosen["match_status"], "source": chosen["source"],
                           "source_url": chosen["source_url"], "detail": "imported_from:" + origin})
    candidate_df = pd.DataFrame(records)
    audit_df = pd.DataFrame(audits)
    # Prefere o piloto Apple, que conferiu o autor, a uma prévia editorial não validada.
    if not candidate_df.empty:
        candidate_df["_rank"] = candidate_df["match_status"].eq("verified").astype(int)
        candidate_df = candidate_df.sort_values("_rank").drop_duplicates("book_id", keep="last").drop(columns="_rank")
    if not audit_df.empty:
        audit_df["_rank"] = audit_df["match_status"].eq("verified").astype(int)
        audit_df = audit_df.sort_values("_rank").drop_duplicates("book_id", keep="last").drop(columns="_rank")
    return audit_df, candidate_df


def run(args, client: httpx.Client | None = None) -> dict:
    if args.per_genre < 1 or args.limit < 0 or args.apple_delay < 3.2 or args.publisher_delay < 1:
        raise ValueError("per-genre >= 1, limit >= 0, apple-delay >= 3.2, publisher-delay >= 1")
    base_df = select_oceanos(Path(args.input))
    # Usa TODAS as linhas do Oceanos para consolidar sites, não somente as
    # linhas deduplicadas do corpus final.
    raw_publisher_data = pd.read_csv(args.input, dtype=str, compression="infer").fillna("")
    registry = build_publisher_site_registry(
        raw_publisher_data, min_support=getattr(args, "publisher_min_support", 2)
    )
    base_df = apply_publisher_site_registry(base_df, registry)
    out = Path(args.output_dir)
    if args.dry_run:
        for row in list(interleave_genres(base_df))[:max(1, args.limit)]:
            print(f"{row['genero_livro']}: {row['titulo_livro']} — {row['nome_autor']} [prioridade {row['priority']}]")
        print(f"Obras únicas elegíveis: {len(base_df)}")
        return {"attempted": 0, "accepted": 0}
    if getattr(args, "publisher_report_only", False):
        out.mkdir(parents=True, exist_ok=True)
        atomic_csv(registry, out / "publisher_sites_registry.csv")
        coverage = (base_df.groupby("publisher_site_source", dropna=False)
                    .size().rename("books").reset_index())
        atomic_csv(coverage, out / "publisher_site_coverage.csv")
        print("Cobertura:", dict(zip(coverage["publisher_site_source"], coverage["books"])))
        print("Relatórios gerados sem consultar APIs:", out)
        return {"attempted": 0, "accepted": 0, "publisher_coverage": coverage}
    out.mkdir(parents=True, exist_ok=True)
    # Esse CSV contém somente metadados de sites, nunca chaves de API.
    atomic_csv(registry, out / "publisher_sites_registry.csv")
    coverage = (base_df.groupby("publisher_site_source", dropna=False)
                .size().rename("books").reset_index())
    atomic_csv(coverage, out / "publisher_site_coverage.csv")
    print("Sites por origem:", dict(zip(coverage["publisher_site_source"], coverage["books"])))
    audit = load_csv(out / "audit.csv")
    candidates = load_csv(out / "descriptions_candidates.csv")
    if getattr(args, "import_existing", False):
        imported_audit, imported_candidates = import_previous_pilots(
            base_df, Path(args.pilot_dir), Path(args.editorial_previews), args.min_chars)
        if not imported_candidates.empty:
            candidates = pd.concat([imported_candidates, candidates], ignore_index=True).drop_duplicates("book_id", keep="last")
        if not imported_audit.empty:
            audit = pd.concat([imported_audit, audit], ignore_index=True).drop_duplicates("book_id", keep="last")
        print(f"Registros reaproveitados dos pilotos: {len(imported_candidates)}")
        export_outputs(out, audit, candidates, args.per_genre)
    done = set(audit["book_id"]) if not audit.empty else set()
    if args.retry_errors and not audit.empty:
        done -= set(audit.loc[audit["status"].eq("transient_error"), "book_id"])
    # Reprocessar SOMENTE os registros antes classificados sem site e que agora
    # passaram a ter endereço, sem refazer consultas Apple/Google já realizadas.
    retry_missing_sites: set[str] = set()
    if getattr(args, "retry_missing_sites", False) and not audit.empty:
        old_failures = audit.loc[
            audit["status"].eq("no_description") &
            audit["editorial_status"].eq("no_publisher_site"), "book_id"
        ]
        has_site = set(base_df.loc[
            base_df["publisher_site_resolved"].ne(""), "book_id"
        ])
        retry_missing_sites = set(old_failures) & has_site
        done -= retry_missing_sites
        print(f"Registros elegíveis para nova tentativa editorial: {len(retry_missing_sites)}")
    if getattr(args, "only_retry_missing_sites", False) and not getattr(args, "retry_missing_sites", False):
        raise ValueError("--only-retry-missing-sites exige --retry-missing-sites")
    accepted = count_accepted(candidates)
    urls = known_editorial_pages(Path(args.publisher_queue)) if args.publisher_queue else {}
    google_key = os.environ.get("GOOGLE_BOOKS_API_KEY", "") if args.use_google else ""
    if args.use_google and not google_key:
        raise ValueError("--use-google exige a variável GOOGLE_BOOKS_API_KEY")
    own_client = client is None
    if own_client:
        client = httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=False)
    publisher = PublisherClient(client, args.publisher_delay)
    google_available = bool(google_key)
    apple_available = not args.skip_apple
    last_apple = 0.0
    attempted = 0
    try:
        for row in interleave_genres(base_df):
            genre, bid = row["genero_livro"], row["book_id"]
            if bid in done or accepted.get(genre, 0) >= args.per_genre:
                continue
            if getattr(args, "only_retry_missing_sites", False) and bid not in retry_missing_sites:
                continue
            if attempted >= args.limit:
                break
            attempted += 1
            title, author = row["titulo_livro"], row["nome_autor"]
            print(f"[{attempted}/{args.limit}] [{genre}: {accepted.get(genre, 0)}/{args.per_genre}] {title} — {author}", flush=True)
            trace = {"apple_status": "skipped", "google_status": "skipped", "editorial_status": "skipped"}
            proposals: list[dict] = []
            transient = False
            if apple_available and bid not in retry_missing_sites:
                wait = args.apple_delay - (time.monotonic() - last_apple)
                if wait > 0:
                    time.sleep(wait)
                last_apple = time.monotonic()
                response, status = safely_get(client, APPLE_API,
                    params={"term": f"{title} {author}", "country": args.country, "media": "ebook", "entity": "ebook", "limit": 15})
                if status == "rate_limited":
                    apple_available, transient = False, True
                    trace["apple_status"] = status
                elif status != "ok":
                    transient = True
                    trace["apple_status"] = status
                else:
                    try:
                        result = parse_apple(response.json(), title, author, args.min_chars)
                        trace["apple_status"] = result["status"]
                        if result["status"] == "found":
                            proposals.append(result)
                    except (ValueError, TypeError):
                        trace["apple_status"] = "invalid_json"
                        transient = True
            # Google Books opcional, nunca usado após 429 na mesma execução.
            if not proposals and google_available and bid not in retry_missing_sites:
                response, status = safely_get(client, GOOGLE_API,
                    params={"q": f'intitle:"{title}" inauthor:"{author}"', "key": google_key, "maxResults": 10,
                            "printType": "books"})
                if status == "rate_limited":
                    google_available, transient = False, True
                if status == "ok":
                    try:
                        gr = parse_google(response.json(), title, author, args.min_chars)
                        trace["google_status"] = gr["status"]
                        if gr["status"] == "found":
                            proposals.append(gr)
                    except (ValueError, TypeError):
                        trace["google_status"] = "invalid_json"
                        transient = True
                else:
                    trace["google_status"] = status
                    transient = True
            # Se a descrição da API é insuficiente ou ambígua, tenta também a editora.
            api_best = best_description(proposals, args.min_chars)
            needs_better = not api_best or api_best["quality_status"] != "candidate"
            details = []
            if needs_better and not args.skip_publisher:
                known = urls.get(bid, "")
                base = row.get("publisher_site_resolved", "") or normal_publisher_base(known)
                if not base:
                    trace["editorial_status"] = "no_publisher_site"
                else:
                    page_links, discovery_status = publisher.find_pages(base, title, known)
                    trace["editorial_status"] = discovery_status
                    if any(code in discovery_status for code in ("error_", "rate_limited", "http_5")):
                        transient = True
                    for page_url in page_links:
                        page_html, fetch_status = publisher.fetch(page_url, base)
                        if fetch_status != "ok":
                            details.append(f"page:{fetch_status}")
                            if fetch_status.startswith(("error_", "http_5", "rate_limited")):
                                transient = True
                            continue
                        match = page_matches(page_html, title, author)
                        if match == "mismatch":
                            details.append("page:mismatch")
                            continue
                        texts = extract_descriptions(page_html, args.min_chars)
                        chosen = best_description(texts, args.min_chars)
                        if chosen:
                            proposals.append({**chosen, "source": "publisher", "source_url": page_url,
                                              "match_status": match})
                            trace["editorial_status"] = "page_extracted"
                            break
                        details.append("page:no_informative_text")
            best = best_description(proposals, args.min_chars)
            if best:
                match_status = best["match_status"]
                status = "candidate" if best["quality_status"] == "candidate" and match_status == "verified" else "needs_review"
                candidate = {
                    "book_id": bid, "title": title, "authors": author, "genre": genre,
                    "description": best["description"], "source": best["source"],
                    "source_url": best.get("source_url", ""), "extraction_method": best["extraction_method"],
                    "quality_status": best["quality_status"], "match_status": match_status,
                    "usage_status": "pending_rights_review",
                }
                candidates = pd.concat([candidates, pd.DataFrame([candidate])], ignore_index=True)
                candidates = candidates.drop_duplicates("book_id", keep="last")
                if status == "candidate":
                    accepted[genre] = accepted.get(genre, 0) + 1
            else:
                status = "transient_error" if transient else "no_description"
                match_status = ""
            record = {
                "book_id": bid, "title": title, "authors": author, "genre": genre,
                "priority": str(row["priority"]), "publisher": row.get("nome_editora", ""),
                "publisher_site": row.get("site_editora", ""),
                "publisher_site_resolved": row.get("publisher_site_resolved", ""),
                "publisher_site_source": row.get("publisher_site_source", ""),
                **trace, "status": status,
                "quality_status": best["quality_status"] if best else "",
                "match_status": match_status, "source": best["source"] if best else "",
                "source_url": best.get("source_url", "") if best else "", "detail": ";".join(details),
            }
            audit = pd.concat([audit, pd.DataFrame([record])], ignore_index=True).drop_duplicates("book_id", keep="last")
            done.add(bid)
            export_outputs(out, audit, candidates, args.per_genre)
            print(f"  -> {status} | Apple: {trace['apple_status']} | Editora: {trace['editorial_status']}", flush=True)
    finally:
        if own_client:
            client.close()
    export_outputs(out, audit, candidates, args.per_genre)
    total = sum(count_accepted(candidates).values())
    print(f"\nNovos livros consultados: {attempted}. Candidatos por gênero: {count_accepted(candidates)}")
    print(f"Total com descrição (triagem automática): {total}/{args.per_genre * len(GENRES)} (meta)")
    print(f"Sites de editoras consolidados: {out / 'publisher_sites_registry.csv'}")
    print(f"Arquivos em: {out}")
    return {"attempted": attempted, "accepted": total, "audit": audit, "candidates": candidates}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV Oceanos (.csv ou .csv.gz)")
    parser.add_argument("--per-genre", type=int, default=100, help="COTA de candidatos por gênero")
    parser.add_argument("--limit", type=int, default=15, help="Máximo de livros NOVOS nesta execução")
    parser.add_argument("--output-dir", default="data/interim/oceanos/auto500")
    parser.add_argument("--publisher-queue", default="data/interim/oceanos/piloto_multifonte/publisher_review_queue.csv")
    parser.add_argument("--country", choices=("BR", "PT"), default="BR")
    parser.add_argument("--min-chars", type=int, default=180)
    parser.add_argument("--apple-delay", type=float, default=3.4, help="Intervalo entre chamadas Apple, >=3.2s")
    parser.add_argument("--publisher-delay", type=float, default=2.0, help="Intervalo por domínio editorial, >=1s")
    parser.add_argument("--skip-apple", action="store_true")
    parser.add_argument("--skip-publisher", action="store_true")
    parser.add_argument("--use-google", action="store_true", help="Opcional; requer GOOGLE_BOOKS_API_KEY")
    parser.add_argument("--retry-errors", action="store_true", help="Reconsultar apenas registros com transient_error")
    parser.add_argument("--publisher-min-support", type=int, default=2,
                        help="Mínimo de obras diferentes com mesmo domínio para inferir site")
    parser.add_argument("--retry-missing-sites", action="store_true",
                        help="Reprocessar casos anteriores sem site quando agora houver domínio resolvido")
    parser.add_argument("--only-retry-missing-sites", action="store_true",
                        help="Nesta execução, processar apenas os casos recuperados pelo novo cadastro")
    parser.add_argument("--import-existing", action="store_true", help="Reutilizar descrições dos pilotos Apple/editoras")
    parser.add_argument("--pilot-dir", default="data/interim/oceanos/piloto_multifonte")
    parser.add_argument("--editorial-previews", default="data/interim/oceanos/publisher_description_previews.csv")
    parser.add_argument("--publisher-report-only", action="store_true",
                        help="Gera cadastro e cobertura de editoras sem consultar nenhuma API")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
