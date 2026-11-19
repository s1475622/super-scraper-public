"""Rewritten copy in DOM structures observed in the public-site investigation."""

import pytest

from super_scraper.extractor import extract_article

INTRO = "這份保養清單整理各種膚質的產品資訊，包含成分、質地與使用方法。閱讀時可以逐項比較，並依據自己的需求選擇合適的保養步驟。"
DESCRIPTION = "這款測試配方的質地輕盈，使用時能均勻推開，適合日常保養。產品介紹應與標題及價格一起保留，方便分析不同產品的特點與使用心得。"


def page(body):
    return f"""<html lang="zh-Hant"><head><title>保養產品實測清單</title></head>
    <body><nav>網站導覽，不屬於文章。</nav><main>{body}</main>
    <footer>網站版權聲明</footer></body></html>"""


def test_listicle_keeps_all_slides_intro_and_order_without_related_cards():
    slides = "".join(
        f'<section data-journey-listicle-slide="true"><div class="listicle-slides">'
        f'<h2 data-theme-key="listicle-slide-item-title">保養推薦{i}：測試品牌{i}精華液</h2>'
        f"<div><p>{DESCRIPTION}第{i}款的特點請完整保留。</p><p>30ml，NT${1000 + i}</p></div>"
        "</div></section>"
        for i in range(1, 5)
    )
    html = page(
        f'<div data-journey-body="listicle"><p>{INTRO}</p>{slides}</div>'
        '<div data-block="transporter"><h2>推薦閱讀</h2><p>不相關的推薦文章摘要。</p></div>'
    )
    result = extract_article(html, "https://example.com/listicle")
    assert INTRO in result.text
    for i in range(1, 5):
        title = f"保養推薦{i}：測試品牌{i}精華液"
        assert title in result.text
        assert f"第{i}款的特點請完整保留。" in result.text
        assert title in result.markdown
    assert result.text.index("測試品牌1") < result.text.index("測試品牌4")
    assert "不相關的推薦" not in result.text
    assert "incomplete_content" not in result.warnings


def test_embedded_gallery_retains_product_names_and_reviews():
    cards = "".join(
        f'<div data-theme-key="embedded-gallery-item-wrapper"><div data-fp-embedded-gallery-product="true">'
        f'<img src="/{i}.jpg"><p>測試產品{i}保濕修護精華</p><div><p>評審{i}：{DESCRIPTION}</p></div>'
        "</div></div>"
        for i in range(1, 4)
    )
    html = page(
        f'<div data-journey-body="longform-article"><p>{INTRO}</p>'
        f'<div class="embedded-gallery-grid">{cards}</div></div>'
        "<aside><p>側欄促銷內容</p></aside>"
    )
    result = extract_article(html, "https://example.com/awards")
    for i in range(1, 4):
        assert f"測試產品{i}保濕修護精華" in result.text
        assert f"評審{i}：{DESCRIPTION}" in result.text
    assert "側欄促銷" not in result.text
    assert "![]" not in result.markdown


def test_fragmented_body_preserves_aria_headings_and_does_not_duplicate_nested_roots():
    pieces = "".join(
        f'<div class="body__container"><div class="body__inner-container">'
        f'<div role="heading" aria-level="3"><strong>{i}.測試品牌{i}修護精華</strong></div>'
        f"<p>NT${1000 + i}</p><p>{DESCRIPTION}</p></div></div>"
        for i in range(1, 4)
    )
    html = page(
        f'<article><div class="article-body"><p>{INTRO}</p>{pieces}</div>'
        '<div class="article-body__footer"><h2>推薦文章</h2><p>另一篇不相關文章。</p></div></article>'
    )
    result = extract_article(html, "https://example.com/serum")
    for i in range(1, 4):
        title = f"{i}.測試品牌{i}修護精華"
        assert result.text.count(title) == 1
        assert any(
            line.startswith("### ") and title in line for line in result.markdown.splitlines()
        )
    assert INTRO in result.text
    assert "不相關文章" not in result.text


def test_structured_body_preserves_inline_text_and_table_cells():
    html = page(
        '<div itemprop="articleBody"><h2>產品比較</h2>'
        "<p>保濕<strong>精華</strong>適合日常使用。</p>"
        "<table><tr><th>產品</th><th>容量</th></tr>"
        "<tr><td>測試精華</td><td>30ml</td></tr></table></div>"
    )
    result = extract_article(html, "https://example.com/compare")
    assert "保濕精華適合日常使用。" in result.text
    assert "測試精華" in result.text
    assert "30ml" in result.text
    assert "|" in result.markdown


def test_unrecognized_layout_warns_if_substantial_semantic_blocks_are_lost():
    slides = "".join(
        f'<section class="listicle-slides"><h2>清單商品{i}</h2><p>{DESCRIPTION}</p></section>'
        for i in range(1, 5)
    )
    result = extract_article(page(f"<p>{INTRO}</p>{slides}"), "https://example.com/unusual")
    all_present = all(f"清單商品{i}" in result.text for i in range(1, 5))
    assert all_present or "incomplete_content" in result.warnings


def test_related_links_are_removed_without_deleting_following_real_paragraph():
    html = page(
        f'<div itemprop="articleBody"><p>{INTRO}</p>'
        '<p><a href="/other">延伸閱讀：不相關的產品推薦清單</a></p>'
        f"<p>{DESCRIPTION}</p></div>"
    )
    result = extract_article(html, "https://example.com/article")
    assert "延伸閱讀" not in result.text
    assert DESCRIPTION in result.text


@pytest.mark.parametrize("layout", ["article", "main"])
def test_sidebar_with_fake_article_body_is_not_selected(layout):
    html = (
        f"<html><body><{layout}><h1>真正文章</h1><p>{INTRO}</p><p>{DESCRIPTION}</p>"
        f'</{layout}><aside><div class="article-body"><h2>側欄推薦</h2>'
        "<p>這不是正文，請勿混入。</p></div></aside></body></html>"
    )
    result = extract_article(html, "https://example.com/news")
    assert INTRO in result.text
    assert "側欄推薦" not in result.text


def test_nested_editor_body_excludes_modal_and_repeated_photo_captions():
    html = page(
        f'<article class="article-content"><section class="article-content__editor">'
        f"<p>{INTRO}</p><p>{DESCRIPTION}</p></section>"
        f"<figure><figcaption>{INTRO}</figcaption></figure>"
        '<div class="account-modal"><h2>登入簽到送禮券</h2><p>每日會員優惠。</p></div></article>'
    )
    result = extract_article(html, "https://example.com/news")
    assert result.text.count(INTRO) == 1
    assert "登入簽到" not in result.text
    assert "incomplete_content" not in result.warnings


def test_related_slide_is_removed_but_last_product_and_following_content_remain():
    html = page(
        f'<div data-journey-body="listicle"><p>{INTRO}</p>'
        f'<section data-journey-listicle-slide="true"><h2>商品15</h2><p>{DESCRIPTION}</p></section>'
        '<section data-journey-listicle-slide="true"><h2>【延伸閱讀】</h2>'
        '<p><a href="/other">不相關推薦文章</a></p></section></div>'
    )
    result = extract_article(html, "https://example.com/listicle")
    assert "商品15" in result.text
    assert DESCRIPTION in result.text
    assert "不相關推薦" not in result.text


def test_image_credit_is_removed_without_losing_product_title():
    html = page(
        f'<div class="body__inner-container"><figure><img src="/a.jpg">'
        '<span class="caption__credit">Photo Credit Person</span></figure>'
        f'<div role="heading" aria-level="3">測試精華液</div><p>{DESCRIPTION}</p></div>'
    )
    result = extract_article(html, "https://example.com/serum")
    assert "測試精華液" in result.text
    assert "Photo Credit Person" not in result.text


def test_explicit_app_and_social_promotions_do_not_replace_article_paragraphs():
    html = page(
        f'<div itemprop="articleBody"><p>{DESCRIPTION}</p>'
        '<p>看新聞天天中獎 <a data-desc="APP載點" href="https://example.com/app">點我下載APP</a></p>'
        '<p>快來追蹤 <a href="https://www.instagram.com/test/" '
        'data-vars-ga-call-to-action="點選連結看更多美妝資訊">點選連結看更多美妝資訊</a></p>'
        f"<p>{INTRO}</p></div>"
    )
    result = extract_article(html, "https://example.com/article")
    assert DESCRIPTION in result.text
    assert INTRO in result.text
    assert "天天中獎" not in result.text
    assert "快來追蹤" not in result.text


def test_complete_plain_article_does_not_expand_to_photo_caption_blocks():
    html = page(
        f'<div itemprop="articleBody"><p>{INTRO}</p><p>{DESCRIPTION}</p>'
        '<figure><img src="/a.jpg"><figcaption>額外的照片拍攝說明，並非正文段落。</figcaption></figure>'
        "</div>"
    )
    result = extract_article(html, "https://example.com/news")
    assert INTRO in result.text
    assert DESCRIPTION in result.text
    assert "額外的照片拍攝說明" not in result.text


def test_image_paragraph_with_reporter_credit_does_not_trigger_false_body_expansion():
    html = page(
        f'<article class="article-content"><section class="article-content__editor">'
        f"<p>{INTRO}</p><p>{DESCRIPTION}</p>"
        '<p><img src="/a.jpg">這是照片的拍攝地點與人物說明，並不是額外的新聞段落，'
        "不應重複混進正文分析。記者測試／攝影</p></section></article>"
    )
    result = extract_article(html, "https://example.com/news")
    assert INTRO in result.text
    assert DESCRIPTION in result.text
    assert "拍攝地點" not in result.text
    assert "incomplete_content" not in result.warnings


def test_generic_rail_cannot_override_primary_article():
    html = (
        f"<html><body><main><article><p>{INTRO}</p><p>{DESCRIPTION}</p></article></main>"
        '<div class="rail"><div class="article-body"><h2>側欄推薦商品</h2>'
        "<p>這不是文章的正文內容。</p></div></div></body></html>"
    )
    result = extract_article(html, "https://example.com/news")
    assert INTRO in result.text
    assert DESCRIPTION in result.text
    assert "側欄推薦商品" not in result.text


def test_editorial_intro_and_conclusion_outside_nested_body_are_preserved():
    conclusion = "結語提醒讀者依照膚質調整使用方式，並且逐步觀察產品使用後的反應。這段結論是文章的一部分，必須與導言及正文一起保留。"
    html = page(
        f'<article><p>{INTRO}</p><div class="article-body"><p>{DESCRIPTION}</p></div>'
        f"<p>{conclusion}</p></article>"
    )
    result = extract_article(html, "https://example.com/article")
    for paragraph in (INTRO, DESCRIPTION, conclusion):
        assert paragraph in result.text
    assert "incomplete_content" not in result.warnings


@pytest.mark.parametrize(
    "promo",
    [
        '<a data-desc="APP載點" href="/app">下載APP</a>',
        '<a href="https://www.instagram.com/test/" data-vars-ga-call-to-action="快來追蹤">追蹤</a>',
    ],
)
def test_promotional_link_does_not_delete_editorial_text_in_same_paragraph(promo):
    warning = "這款產品含有可能引發過敏的成分，使用前應先確認成分表，若有特殊需求請詢問專業人員。這段資訊與讀者的使用判斷有關，應完整保留。"
    result = extract_article(
        page(f'<div itemprop="articleBody"><p>{INTRO}</p><p>{warning} {promo}</p></div>'),
        "https://example.com/article",
    )
    assert warning in result.text
    assert "incomplete_content" not in result.warnings


def test_editorial_product_caption_is_preserved_without_photo_credit():
    caption = "粉紅質地來自配方中的維他命，推開後呈現清爽的使用感。"
    html = page(
        f'<div class="body__inner-container"><h2>測試品牌精華液</h2><p>{INTRO}</p>'
        f'<p>{DESCRIPTION}</p><figure><img src="/serum.jpg">'
        f'<span class="caption__text"><p>{caption}</p></span>'
        '<span class="caption__credit">Photo credit Test</span></figure></div>'
    )
    result = extract_article(html, "https://example.com/serum")
    assert caption in result.text
    assert caption in result.markdown
    assert "Photo credit" not in result.text


@pytest.mark.parametrize(
    "widget",
    [
        '<div class="piano-inline-content-module"><h2>別錯過精彩內容</h2><p>無關推薦文章</p>'
        "<div>登入獲得個人化推薦</div></div>",
        '<div aria-label="推薦文章輪播" role="region"><h2>無關推薦文章</h2></div>',
        '<div id="taboola-below-article-thumbnails"><div class="trc_rbox_container">'
        '<span role="heading">你可能感興趣</span><p>無關推薦文章</p><span>by Taboola</span></div></div>',
    ],
)
def test_dynamic_recommendations_inserted_inside_body_are_removed(widget):
    html = page(
        f'<div itemprop="articleBody"><p>{INTRO}</p>{widget}'
        f"<h2>最後一款測試商品</h2><p>{DESCRIPTION}</p></div>"
    )
    result = extract_article(html, "https://example.com/beauty")
    assert INTRO in result.text
    assert DESCRIPTION in result.text
    assert "最後一款測試商品" in result.text
    for noise in ("無關推薦文章", "個人化推薦", "Taboola", "你可能感興趣"):
        assert noise not in result.text
        assert noise not in result.markdown
