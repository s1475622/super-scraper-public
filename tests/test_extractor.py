import pytest

from super_scraper.extractor import extract_article
from super_scraper.models import ScrapeError

CHINESE_PARAGRAPHS = [
    "台灣的山區步道有豐富的自然景觀，登山前應先確認天氣與路線。準備充足的飲水、食物及地圖，能讓旅途更加順利。",
    "不同季節的林相各有特色，春季可以欣賞新芽，秋季則適合觀察色彩變化。沿途請尊重環境，將垃圾帶下山。",
    "行程規劃應配合自己的體力，預留足夠的休息與折返時間。結伴同行時，應以隊伍中速度最慢的成員為準。",
]


@pytest.fixture
def article_html():
    body = "".join(f"<p>{p}</p>" for p in CHINESE_PARAGRAPHS)
    return f"""<!doctype html><html lang="zh-Hant"><head>
    <meta charset="utf-8"><title>登山準備指南</title>
    <meta name="author" content="林小明">
    <meta property="article:published_time" content="2026-10-18T09:00:00+08:00">
    <link rel="canonical" href="https://example.com/hiking">
    </head><body><nav><a href="/shop">購物車會員中心</a></nav>
    <main><article><h1>登山準備指南</h1>{body}</article></main>
    <div id="comments"><p>這是留言區廣告，購買快速瘦身產品。</p></div>
    <footer>網站版權聲明</footer></body></html>"""


def test_chinese_body_preserves_paragraphs_and_excludes_noise(article_html):
    result = extract_article(article_html.encode(), "https://example.com/hiking")
    for paragraph in CHINESE_PARAGRAPHS:
        assert paragraph in result.text
    assert "\n" in result.text
    assert "購物車" not in result.text
    assert "版權聲明" not in result.text
    assert "瘦身產品" not in result.text
    assert result.title == "登山準備指南"
    assert result.author == "林小明"
    assert result.published_date == "2026-10-18"
    assert result.char_count >= 150
    assert "登山" in result.markdown


def test_missing_metadata_stays_unknown():
    result = extract_article(
        "<article><p>這是一篇很短的文章。</p></article>", "https://example.com/a"
    )
    assert result.author is None
    assert result.published_date is None
    assert result.char_count == 10
    assert "short_content" in result.warnings


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html><body></body></html>",
        '<html><head><meta property="og:description" content="只有預覽摘要"></head></html>',
    ],
)
def test_empty_or_og_only_is_not_reconstructed_as_full_body(html):
    with pytest.raises(ScrapeError, match="no_content"):
        extract_article(html, "https://example.com/a")


def test_login_wall_is_flagged():
    html = "<main><h1>Sign in to continue</h1><p>Subscribe to read the full article.</p></main>"
    result = extract_article(html, "https://example.com/a")
    assert "possible_access_wall" in result.warnings


def test_legacy_chinese_encoding_is_not_corrupted():
    html = '<html><head><meta charset="big5"></head><body><article><p>繁體中文測試內容。</p></article></body></html>'
    result = extract_article(html.encode("big5"), "https://example.com/a")
    assert "繁體中文測試內容。" in result.text


def test_dated_url_without_publication_metadata_does_not_invent_a_date():
    html = (
        "<html><body><article><h1>A normal article</h1><p>"
        + "Useful article content. " * 20
        + "</p></article></body></html>"
    )
    result = extract_article(html, "https://example.com/2025/01/12/a")
    assert result.published_date is None


def test_long_login_page_with_password_form_is_flagged():
    html = """<html><head><title>Log in to your account</title></head><body>
    <main><h1>Log in to your account</h1><p>Please log in to view this article.
    Your account provides access to all subscriber content and saved reading lists.</p>
    <p>If you forgot your password, use the reset link below to recover access to your account.
    Our support team can help you with subscription and billing questions.</p>
    <form><input type="email"><input type="password"><button>Log in</button></form></main>
    </body></html>"""
    result = extract_article(html, "https://example.com/account")
    assert result.char_count >= 100
    assert "possible_access_wall" in result.warnings
