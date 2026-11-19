"""Rewritten structures from the extended media and brand investigation."""

import pytest
from bs4 import BeautifulSoup

from super_scraper.content import has_content_gaps, prepare_content
from super_scraper.extractor import extract_article

LEAD = "這篇專題介紹電影工作者的經歷，從創作選擇到幕後合作都有詳細記錄。文章的導言與各個段落應完整保留，才有足夠資訊用於後續分析。"
END = "在經歷各種挑戰之後，受訪者認為持續合作與技術傳承十分重要。最後一段仍然屬於原始報導，不能因為中間出現表格或推薦元件而被略過。"


def test_declared_body_enclosing_embedded_article_is_not_replaced_by_widget():
    html = (
        f'<div id="article-body"><div><p>{LEAD}</p>'
        "<article><h2>補充年表</h2><p>這只是文章中間的補充資料表。</p></article>"
        f"<p>{END}</p></div></div>"
    )
    result = extract_article(html, "https://example.com/feature")
    assert LEAD in result.text
    assert END in result.text
    assert "補充年表" in result.text
    assert result.text.count("補充年表") == 1


def test_declared_body_with_embedded_widget_does_not_widen_to_sibling_story():
    html = (
        f'<main><div id="article-body"><p>{LEAD}</p>'
        f"<article><h2>補充資料</h2></article><p>{END}</p></div>"
        '<section><div class="post-content"><p>不相關的另一篇文章，不能合併。</p></div></section></main>'
    )
    result = extract_article(html, "https://example.com/feature")
    assert LEAD in result.text
    assert END in result.text
    assert "不相關的另一篇文章" not in result.text


@pytest.mark.parametrize(
    "attributes",
    [
        'data-section="article-content-editor"',
        'id="newsContent"',
        'data-gu-name="body"',
        'class="post-content-container"',
    ],
)
def test_publisher_editor_root_excludes_recommendations_outside_it(attributes):
    html = (
        f"<main><article><header>閱讀次數與會員工具</header><div {attributes}>"
        f"<p>{LEAD}</p><p>{END}</p></div>"
        "<section><h2>其他新聞推薦</h2><p>不同文章的內容不屬於這篇報導。</p></section>"
        "</article></main>"
    )
    result = extract_article(html, "https://example.com/news")
    assert LEAD in result.text
    assert END in result.text
    assert "其他新聞推薦" not in result.text
    assert "不同文章" not in result.markdown


def test_donation_and_newsletter_widgets_are_not_article_paragraphs():
    html = (
        f'<article><div class="entry-content"><p>{LEAD}</p><p>{END}</p>'
        '<div class="coffee-btn-wrapper"><p>請我們喝杯咖啡</p></div>'
        '<div class="tn-modal"><h2>選擇贊助金額</h2><p>取消 確認</p></div>'
        '<div class="googlenews_Content"><p>追蹤我們的新聞</p></div>'
        '<div class="newsLetter_articleContent"><p>訂閱免費電子報</p></div>'
        '<div class="article-tags-area">關鍵字: 專題、電影</div>'
        "</div></article>"
    )
    result = extract_article(html, "https://example.com/feature")
    assert LEAD in result.text
    assert END in result.text
    for noise in ("喝杯咖啡", "贊助金額", "追蹤我們", "免費電子報", "關鍵字:"):
        assert noise not in result.text


def test_unrecognized_campaign_layout_warns_instead_of_certifying_footnotes():
    lessons = "".join(
        f'<div class="slide"><span>第{i}堂保養與使用方式需要完整保留的教學資訊。</span></div>'
        for i in range(1, 9)
    )
    html = (
        '<html><body><header>品牌導覽</header><div class="campaign-layout">'
        f"<div><span>品牌教育內容</span>{lessons}</div>"
        "<p>根據品牌公開的產品調查結果，使用感受會因為個人條件與使用情境而不同。這段僅為頁尾的研究註解，不能代替整個頁面的主要資訊。</p>"
        "</div><footer>聯絡我們</footer></body></html>"
    )
    result = extract_article(html, "https://example.com/campaign")
    assert (
        all(f"第{i}堂保養" in result.text for i in range(1, 9))
        or "incomplete_content" in result.warnings
    )


@pytest.mark.parametrize(
    "widget",
    [
        '<div class="article-page__RelatedBlock-sc-example"><h2>其他文章推薦</h2><p>無關新聞摘要。</p></div>',
        '<astro-island component-url="https://example.com/assets/ArticleCard.hash.js"><p>無關新聞摘要。</p></astro-island>',
        '<div data-further-topic-cta=""><h2>延伸閱讀</h2><a href="/other">無關新聞摘要。</a></div>',
        '<div class="docsanddownloads"><p>下載整篇文章文字以供使用</p></div><div class="presscontacts">媒體聯絡人</div>',
    ],
)
def test_embedded_related_cards_and_press_downloads_are_not_article_copy(widget):
    html = f'<div id="article-body"><p>{LEAD}</p>{widget}<p>{END}</p></div>'
    result = extract_article(html, "https://example.com/article")
    assert LEAD in result.text
    assert END in result.text
    for phrase in ("其他文章推薦", "無關新聞摘要", "下載整篇文章", "媒體聯絡人"):
        assert phrase not in result.text


@pytest.mark.parametrize("target", ["one", "two"])
def test_infinite_scroll_uses_requested_post_instead_of_merging_other_articles(target):
    posts = "".join(
        f'<section data-type="post" data-url="https://example.com/{name}">'
        f'<div class="post-content-container"><h2>{name}的獨立文章標題</h2>'
        f"<p>{LEAD}</p><p>{END}</p></div></section>"
        for name in ("one", "two")
    )
    result = extract_article(f"<html><body>{posts}</body></html>", f"https://example.com/{target}")
    assert f"{target}的獨立文章標題" in result.text
    other = "two" if target == "one" else "one"
    assert f"{other}的獨立文章標題" not in result.text
    assert result.text.count(LEAD) == 1


def test_bold_question_followed_by_line_break_keeps_question_and_answer():
    introduction = (
        "The product development team studied different materials over several years. "
        "Each prototype was evaluated for comfort and durability during repeated laboratory trials. "
    )
    answer = (
        "The design combines a flexible internal structure with a precisely controlled outer layer. "
        "Engineers can adjust each section independently to support different movements and activities. "
    )
    html = (
        '<html><body><div id="main">'
        + "".join(f"<p>{introduction}</p>" for _ in range(4))
        + f"<p><strong>How does the technology work?</strong><br>{answer}</p>"
        + "".join(f"<p>{introduction}</p>" for _ in range(3))
        + f"<p><strong>When will the product release?</strong><br>{answer}</p>"
        + "</div></body></html>"
    )
    result = extract_article(html, "https://example.com/release")
    assert "How does the technology work?" in result.text
    assert "When will the product release?" in result.text
    assert answer.strip() in result.text
    assert any(
        line.startswith("### ") and "How does the technology work?" in line
        for line in result.markdown.splitlines()
    )


def test_declared_div_paragraph_omission_is_detected():
    soup = BeautifulSoup(
        f'<article><div class="pagebody-copy">{LEAD}</div>'
        f'<div class="pagebody-copy">{END}</div></article>',
        "html.parser",
    )
    prepare_content(soup)
    assert has_content_gaps(soup, LEAD)


def test_main_id_container_is_preferred_to_external_rail_body():
    html = (
        f'<div id="main"><p>{LEAD}</p><p>{END}</p></div>'
        '<div class="rail"><div class="post-content">無關側欄推薦</div></div>'
    )
    result = extract_article(html, "https://example.com/release")
    assert LEAD in result.text
    assert END in result.text
    assert "無關側欄推薦" not in result.text


@pytest.mark.parametrize(
    "attributes",
    [
        'id="compass-fit-123"',
        'class="pansc-entity-placement"',
        'id="recirc"',
        'class="gliaplayer-container"',
    ],
)
def test_ad_and_recirculation_widgets_do_not_pollute_the_article(attributes):
    html = (
        f'<div id="article-body"><p>{LEAD}</p><div {attributes}>'
        "<h3>另一則推薦內容</h3><p>廣告或其他文章的文字不應該併入正文。</p></div>"
        f"<p>{END}</p></div>"
    )
    result = extract_article(html, "https://example.com/feature")
    assert LEAD in result.text
    assert END in result.text
    assert "另一則推薦內容" not in result.text
