"""Extract article text with Trafilatura and a structured HTML fallback.

Trafilatura first, BeautifulSoup/markdownify fallback. Unlike the source,
OpenGraph descriptions are never reconstructed as article text.
"""

import json
import re
from datetime import date
from urllib.parse import urljoin

import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

from .content import content_html, has_content_gaps, prepare_content, structured_content
from .models import Article, ScrapeError

_ACCESS_WALL = re.compile(
    r"(?:sign|log)\s?in to (?:continue|read|view|your account)|"
    r"subscribe to (?:continue|read)|verify (?:that )?you are human|"
    r"checking your browser|just a moment|access denied|human verification|"
    r"verify your identity|enable javascript and cookies|"
    r"請先登入|登入後(?:即可|繼續|閱讀)|訂閱(?:後|即可).*閱讀|驗證您是人類|會員限定",
    re.IGNORECASE,
)
_NOISE = (
    "script, style, noscript, nav, footer, aside, [hidden], [aria-hidden='true'], "
    "[role='navigation'], #comments, .comments, .comment-list, "
    ".cookie-banner, .sidebar"
)


def _value(value) -> str | None:
    return str(value).strip() or None if value is not None else None


def _published_date(soup: BeautifulSoup) -> str | None:
    """Use explicit publication evidence, never a URL-derived date."""
    candidates: list[str] = []
    names = {
        "article:published_time",
        "og:published_time",
        "datepublished",
        "pubdate",
        "publishdate",
        "publication_date",
        "dc.date.issued",
        "dcterms.issued",
    }
    for tag in soup.find_all("meta", content=True):
        name = str(tag.get("property") or tag.get("name") or tag.get("itemprop") or "").lower()
        if name in names:
            candidates.append(str(tag["content"]))
    for script in soup.select("script[type='application/ld+json']"):
        try:
            pending = [json.loads(script.get_text())]
        except (ValueError, RecursionError):
            continue
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                value = item.get("datePublished")
                if isinstance(value, str):
                    candidates.append(value)
                pending.extend(value for value in item.values() if isinstance(value, (dict, list)))
            elif isinstance(item, list):
                pending.extend(item)
    for tag in soup.select(
        "time[itemprop='datePublished'][datetime], time[pubdate][datetime], time.published[datetime], time.entry-date[datetime]"
    ):
        candidates.append(str(tag["datetime"]))
    for candidate in candidates:
        match = re.match(r"^(\d{4}-\d{2}-\d{2})(?:T|\s|$)", candidate.strip())
        if match:
            try:
                return date.fromisoformat(match.group(1)).isoformat()
            except ValueError:
                continue
    return None


def extract_article(html: str | bytes, url: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    published_date = _published_date(soup)
    password_form = soup.select_one("form input[type='password']") is not None
    # Take metadata before stripping scripts (which may contain JSON-LD).
    document = trafilatura.bare_extraction(
        str(soup),
        url=url,
        with_metadata=True,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
        date_extraction_params={"extensive_search": False, "original_date": True},
    )
    for node in soup.select(_NOISE):
        if node.parent is not None:
            node.decompose()
    prepare_content(soup, url)
    cleaned = content_html(soup) or str(soup)
    text = trafilatura.extract(
        cleaned,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    markdown = trafilatura.extract(
        cleaned,
        url=url,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        include_images=False,
        include_links=False,
        favor_precision=True,
    )
    # Retain the clean baseline when its semantic blocks are already present.
    # Expand only inside explicit content roots when actual omissions are found.
    if not text or has_content_gaps(soup, text):
        structured = structured_content(soup)
        if structured:
            text, markdown = structured
    warnings: list[str] = []
    if not text or not text.strip():
        container = soup.select_one("article, main, [role='main']") or soup.body
        if container:
            text = container.get_text("\n", strip=True)
            markdown = markdownify(str(container), heading_style="ATX")
        if text and text.strip():
            warnings.append("fallback_extraction")
    if not text or not text.strip():
        raise ScrapeError("no_content", "未找到正文；動態頁面可嘗試 --mode browser")

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    count = sum(not char.isspace() for char in text)
    if count < 100:
        warnings.append("short_content")
    if has_content_gaps(soup, text):
        warnings.append("incomplete_content")
    title_text = soup.title.get_text(" ", strip=True) if soup.title else ""
    if _ACCESS_WALL.search(title_text + "\n" + text[:4000]) or (
        password_form and (not soup.article or count < 300)
    ):
        warnings.append("possible_access_wall")

    canonical = soup.select_one("link[rel='canonical'][href]")
    explicit_author = soup.select_one("meta[name='author'][content]")
    explicit_site = soup.select_one("meta[property='og:site_name'][content]")
    title_node = soup.title or soup.h1
    title = _value(getattr(document, "title", None))
    if not title and title_node:
        title = _value(title_node.get_text(" ", strip=True))
    return Article(
        text=text,
        markdown=(markdown or text).strip(),
        title=title,
        author=(
            _value(explicit_author.get("content"))
            if explicit_author
            else _value(getattr(document, "author", None))
        ),
        published_date=published_date,
        site_name=_value(explicit_site.get("content")) if explicit_site else None,
        language=_value(soup.html.get("lang")) if soup.html else None,
        canonical_url=urljoin(url, str(canonical["href"])) if canonical else None,
        char_count=count,
        warnings=warnings,
    )
