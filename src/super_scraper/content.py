"""Keep publisher-declared article bodies and semantic headings intact.

Publisher body selectors preserve listicles and embedded product galleries
that boilerplate extraction can discard. Campaign layouts also need scoped
adapters because short div/span copy is not reliably recognized as prose.
"""

import re
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from markdownify import markdownify

_CAMPAIGN_BODIES = ".fla-body .fla-main, .fla-body .sec-teach"
_BODY_SELECTORS = (
    "[itemprop~='articleBody'], [data-journey-body], .body__inner-container, "
    ".article-body, .article-content__editor, .post-content, .entry-content, #article-body, "
    "[data-section='article-content-editor'], #newsContent, [data-gu-name='body'], "
    ".post-content-container, "
) + _CAMPAIGN_BODIES
_EXTRA_NOISE = (
    "iframe, svg, video, audio, img, picture, button, input, select, textarea, "
    "[data-block='transporter'], [data-gpt-wrapper], .breaker-ad, "
    ".article-body__footer, .related-posts, .related-articles, .related-content, "
    ".recommended-module, #module-recommended, "
    ".piano-inline-content-module, [aria-label='推薦文章輪播'], "
    "[id^='taboola-'], .trc_rbox_container, "
    "[data-testid='external-link-embed--inline'], .caption__credit, "
    "[data-theme-key$='-credit'], ul.tag, .tag-cloud, dialog, [role='dialog'], "
    "[aria-modal='true'], .account-modal, .tn-modal, .coffee-btn-wrapper, "
    ".googlenews_Content, .newsLetter_articleContent, .article-tags-area, .socialcount, "
    "[class*='__RelatedBlock-'], [class*='related__Block-'], "
    "astro-island[component-url*='/ArticleCard.'], [data-further-topic-cta], "
    ".hashtags-container, .docsanddownloads, .presscontacts, .nr-article-share, "
    "[class*='donation-box__Container-'], a[href*='from=articlebottom'], "
    "[id^='compass-fit-'], .pansc-entity-placement, #recirc, .gliaplayer-container"
)
_RELATED = re.compile(r"^(?:延伸閱讀|相關閱讀|推薦閱讀|read\s+more|also\s+read)\s*[:：]", re.I)
_RELATED_LABEL = re.compile(r"^(?:延伸閱讀|相關閱讀|推薦閱讀)\s*[:：]?$", re.I)
_PROMOTION = re.compile(
    r"(?:看新聞天天中獎|快來追蹤|"
    r"不用抽\s*不用搶\s*現在用APP看新聞\s*保證天天中獎\s*(?:按我看活動辦法)?|"
    r"[♥❤\ufe0f\s]*[\w\u4e00-\u9fff]{1,30}IG全新上架[！!]\s*快來追蹤\s*>>|"
    r"[♥❤\ufe0f\s]*加入[\w\u4e00-\u9fff]{1,30}\s*LINE\s*所有慾望一次滿足)",
    re.I,
)
_BLOCKS = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "figure",
    "figcaption",
    "details",
    "summary",
    "dl",
    "dt",
    "dd",
}


def _key(text: str) -> str:
    return re.sub(r"\s+", "", text)


def prepare_content(soup: BeautifulSoup, url: str = "") -> None:
    # The sensi campaign template places its lessons beside the hero, while
    # forms and trial-result dialogs are siblings outside both content roots.
    # Keep tab/accordion answers present in the source, including closed tabs.
    for campaign in soup.select(".fla-body"):
        for node in campaign.select(
            ".fla-main .btn-white, .fla-main .search-block, .sec-teach .click-hint, "
            ".sec-teach .sec-btn, .sec-teach .sec-3-acc .more"
        ):
            if node.parent is not None:
                node.decompose()
        for heading in campaign.select(".sec-teach .sec-head, .sec-teach .sec-3-acc > a"):
            heading.name = "h2"
            heading.string = heading.get_text(" ", strip=True)
    posts = soup.select("[data-type='post'][data-url]")
    if len(posts) > 1 and url:
        canonical = soup.select_one("link[rel='canonical'][href]")
        targets = [url]
        if canonical:
            targets.append(urljoin(url, str(canonical["href"])))
        for target in targets:
            matching = [
                node
                for node in posts
                if urldefrag(urljoin(url, str(node["data-url"])))[0].rstrip("/")
                == urldefrag(target)[0].rstrip("/")
            ]
            if matching:
                for node in posts:
                    if node.parent is not None and not any(node is match for match in matching):
                        node.decompose()
                break
    # Some news publishers use an image + caption paragraph instead of figure.
    # Normalize it before removing the image so caption omissions are not mistaken
    # for lost article paragraphs and do not force an unnecessarily broad fallback.
    for paragraph in soup.find_all("p"):
        if paragraph.find("img") and re.search(
            r"(?:記者[^。\n]{0,30}[／/]攝影|[（(](?:圖|照片)[／/][^）)]{1,80}[）)])\s*$",
            paragraph.get_text(" ", strip=True),
        ):
            paragraph.name = "figure"
    for node in soup.select(_EXTRA_NOISE):
        if node.parent is not None:
            node.decompose()
    # Some product descriptions are editorial paragraphs inside image captions.
    # Keep explicitly marked caption text; ordinary photo captions stay optional.
    for paragraph in soup.select(".caption__text p"):
        figure = paragraph.find_parent("figure")
        if figure:
            figure.name = "div"
    for link in soup.find_all("a"):
        if link.parent is None:
            continue
        action = str(link.get("data-vars-ga-call-to-action", ""))
        href = str(link.get("href", "")).lower()
        social_action = ("instagram.com/" in href or "line.me/" in href) and action.startswith(
            ("點選連結看更多", "立即加好友", "快來追蹤")
        )
        if link.get("data-desc") == "APP載點" or social_action:
            paragraph = link.find_parent("p")
            link.decompose()
            # Remove only recognized standalone promotion copy. A CTA appended
            # to an editorial paragraph must never delete that paragraph.
            if paragraph:
                remaining = paragraph.get_text(" ", strip=True)
                if not remaining or _PROMOTION.fullmatch(remaining):
                    paragraph.decompose()
            continue
        if _RELATED.match(link.get_text(" ", strip=True)):
            parent = link.parent
            if parent.name == "p" and parent.get_text(strip=True) == link.get_text(strip=True):
                parent.decompose()
            else:
                link.decompose()
    for node in list(soup.find_all(["h2", "h3", "h4", "p"])):
        if not node.parent:
            continue
        label = node.get_text(" ", strip=True).strip("【】[]()（）:： \t\n")
        if _RELATED_LABEL.fullmatch(label):
            slide = node.find_parent(attrs={"data-journey-listicle-slide": True})
            if slide:
                slide.decompose()
                continue
            following = node.find_next_sibling()
            if following and following.name in {"ul", "ol"} and following.find("a"):
                following.decompose()
            node.decompose()
    for node in soup.find_all(["div", "p", "span", "a"]):
        if (
            node.parent
            and node.string
            and node.get_text(strip=True).lower()
            in {
                "watch next",
                "see more details",
                "advertisement",
                "廣告 - 內文未完請往下捲動",
            }
        ):
            node.decompose()
    for heading in soup.select("[role='heading']"):
        level = str(heading.get("aria-level", "2"))
        heading.name = f"h{level if level in {'1', '2', '3', '4', '5', '6'} else '2'}"
    for paragraph in soup.select("div.pagebody-copy"):
        paragraph.name = "p"
    for paragraph in soup.find_all("p"):
        first = next(
            (
                child
                for child in paragraph.children
                if not isinstance(child, NavigableString) or child.strip()
            ),
            None,
        )
        if not isinstance(first, Tag) or first.name not in {"strong", "b"}:
            continue
        following = first.next_sibling
        while isinstance(following, NavigableString) and not following.strip():
            following = following.next_sibling
        if (
            isinstance(following, Tag)
            and following.name == "br"
            and first.get_text(strip=True).endswith(("?", "？"))
        ):
            heading = soup.new_tag("h3")
            heading.append(first.extract())
            paragraph.insert_before(heading)
            following.decompose()


def _primary(soup: BeautifulSoup) -> Tag | None:
    main = soup.find("main") or soup.select_one("[role='main'], div#main, section#main")
    articles = (main or soup).find_all("article")
    article = max(articles, key=lambda node: len(node.get_text()), default=None)
    if article:
        # A publisher body can contain a supplementary <article> widget. That
        # nested semantic tag must not replace its enclosing declared body.
        for root in soup.select(_BODY_SELECTORS):
            if any(parent is root for parent in article.parents):
                return root
    return article or main


def _roots(soup: BeautifulSoup) -> list[Tag]:
    primary = _primary(soup)
    candidates = [
        node
        for node in soup.select(_BODY_SELECTORS)
        if node.get_text(strip=True)
        and (
            primary is None or node is primary or any(parent is primary for parent in node.parents)
        )
    ]
    identities = {id(node) for node in candidates}
    roots = [
        node for node in candidates if not any(id(parent) in identities for parent in node.parents)
    ]
    if not roots:
        return [primary] if primary else []
    # Publishers may put the lead and conclusion beside a nested body. Retain
    # semantic siblings along its enclosing containers, without widening the
    # selection to unrelated nested widgets, captions, or recommendation rails.
    if primary and primary.name == "article":
        containers = {id(primary)}
        for root in roots:
            for parent in root.parents:
                if parent is primary:
                    break
                containers.add(id(parent))
        extras = [
            node
            for node in primary.select("p, h2, h3, h4, h5, h6")
            if id(node.parent) in containers
            and not any(id(parent) in identities for parent in node.parents)
            and id(node) not in identities
        ]
        selected = {id(node) for node in roots + extras}
        return [node for node in soup.descendants if isinstance(node, Tag) and id(node) in selected]
    return roots


def _plain(node) -> str:
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))
    if node.name == "br":
        return "\n"
    if node.name == "pre":
        return "\n" + node.get_text() + "\n"
    if node.name == "tr":
        cells = [
            "".join(_plain(child) for child in cell.children).strip()
            for cell in node.find_all(["th", "td"], recursive=False)
        ]
        return "\n" + "\t".join(cells) + "\n"
    text = "".join(_plain(child) for child in node.children)
    if node.name == "li":
        return "\n- " + text.strip() + "\n"
    if node.name in _BLOCKS:
        return "\n" + text + "\n"
    return text


def content_html(soup: BeautifulSoup) -> str | None:
    roots = _roots(soup)
    if not roots:
        return None
    return (
        "<html><body><article>" + "".join(str(root) for root in roots) + "</article></body></html>"
    )


def structured_content(soup: BeautifulSoup) -> tuple[str, str] | None:
    roots = _roots(soup)
    if not roots:
        return None
    content = BeautifulSoup("<article></article>", "html.parser")
    for root in roots:
        # Copy nodes: metadata and completeness checks still need the source tree.
        clone = BeautifulSoup(str(root), "html.parser")
        content.article.append(clone)
    text = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", _plain(content)).strip()
    markdown = markdownify(str(content), strip=["a"], heading_style="ATX").strip()
    return (text, markdown) if text else None


def has_content_gaps(soup: BeautifulSoup, text: str) -> bool:
    """Check substantial paragraph and heading evidence within content scopes."""
    scopes = _roots(soup)
    if not scopes:
        # Campaign pages sometimes consist entirely of short div/span blocks.
        # Detect concrete missing fragments, but do not broaden extraction to
        # the entire page when no trusted article scope has been identified.
        actual = _key(text)
        missing = set()
        for node in soup.select("div, span, li"):
            if node.find(["div", "p", "li", "section", "article", "h1", "h2", "h3"]):
                continue
            if node.find_parent(["header", "form", "figure", "figcaption"]):
                continue
            expected = _key(node.get_text())
            if len(expected) >= 12 and expected not in actual:
                missing.add(expected)
        return len(missing) >= 3 and sum(map(len, missing)) >= 120
    actual = _key(text)
    campaign_bodies = {id(node) for node in soup.select(_CAMPAIGN_BODIES)}
    for scope in scopes:
        # Ordinary article bodies can also wrap author widgets and toolbars.
        # Short div copy is evidence only in the adapter's campaign scopes.
        selector = "p, h2, h3, h4, h5, h6"
        if id(scope) in campaign_bodies:
            selector += ", div, span, li"
        blocks = scope.select(selector)
        if scope.name in {"p", "h2", "h3", "h4", "h5", "h6"}:
            blocks.insert(0, scope)
        for node in blocks:
            if node.find_parent(["figure", "figcaption"]):
                continue
            if node.name in {"div", "span", "li"} and node.find(list(_BLOCKS)):
                continue
            expected = _key(node.get_text())
            if node.name in {"div", "span", "li"}:
                minimum = 12
            else:
                minimum = (
                    40 if node.name == "p" and not node.find_parent(class_="caption__text") else 4
                )
            if len(expected) >= minimum and expected not in actual:
                return True
    return False
