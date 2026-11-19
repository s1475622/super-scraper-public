"""Rewritten campaign structures, without publisher article copy."""

import pytest
from bs4 import BeautifulSoup

from super_scraper.content import has_content_gaps
from super_scraper.extractor import extract_article

LESSONS = [f"第{i}堂課說明產品使用方式與適用情境，分析時應保留這段說明文字。" for i in range(1, 7)]
NOTE = "這是頁尾的調查註解，記錄調查方法與不同受測者之間可能存在的差異。" * 3


@pytest.mark.parametrize("root", ["main", 'div class="article-body"'])
def test_div_copy_in_trusted_scope_cannot_be_replaced_by_footnotes(root):
    tag = root.split()[0]
    html = f"<{root}>" + "".join(f"<div><span>{x}</span></div>" for x in LESSONS)
    html += f"<p>{NOTE}</p></{tag}>"
    result = extract_article(html, "https://example.com/education")
    for lesson in LESSONS:
        assert lesson in result.text
        assert lesson in result.markdown
    assert "incomplete_content" not in result.warnings


def test_div_tail_is_checked_even_when_leading_inline_text_is_present():
    soup = BeautifulSoup(
        '<div class="fla-body"><div class="sec-teach"><div><span>簡短標題</span>'
        "這段完整的說明位於行內標籤後方，不能只檢查前面的標題。</div></div></div>",
        "html.parser",
    )
    assert has_content_gaps(soup, "簡短標題")


@pytest.mark.parametrize("root", ["article", 'div class="article-body"'])
def test_ordinary_body_does_not_promote_nonparagraph_author_widgets(root):
    tag = root.split()[0]
    soup = BeautifulSoup(
        f'<{root}><p>這是完整報導的主要段落。</p><div class="author-bio">'
        f"作者最近發表的文章與個人資料不應因為位於文章標籤內，就被誤認成缺少的內文。</div></{tag}>",
        "html.parser",
    )
    assert not has_content_gaps(soup, "這是完整報導的主要段落。")


def test_campaign_lessons_and_answers_exclude_trial_dialog_and_navigation():
    sections = "".join(
        f'<div class="sec-{i}"><div class="sec-head"><div>課程{i}</div></div>'
        f'<div class="click-hint">點擊看更多</div><div class="para">{lesson}</div></div>'
        for i, lesson in enumerate(LESSONS, 1)
    )
    html = (
        '<html><body><header>品牌會員中心</header><div class="fla-body">'
        '<div class="fla-wrapper"><div class="container">'
        '<div class="nav-top">回首頁</div><div class="sec-tab">切換分頁</div>'
        '<div class="fla-main"><div>保養教學總覽</div>'
        '<div class="search-block"><div id="mainTitle">輸入中的動畫片段</div></div>'
        '<a class="btn-white">立即破解迷思 領試用</a></div>'
        f'<div class="sec-teach">{sections}'
        '<div class="sec-3-acc"><a><span>課程問答</span><span class="more">看解答</span></a>'
        f'<div class="tab-content"><p>{NOTE}</p></div></div>'
        '<a class="sec-btn">實體銷售據點</a></div>'
        '<div class="fla-lightbox"><p>恭喜您已成功領取試用品</p>'
        "<p>登入會員領試用</p></div></div></div></div><footer>客服中心</footer></body></html>"
    )
    result = extract_article(html, "https://www.lrp.com.tw/events/sensi2019/index.html")
    for phrase in ["保養教學總覽", "課程問答", NOTE, *LESSONS]:
        assert phrase in result.text
        assert phrase in result.markdown
    for noise in [
        "品牌會員中心",
        "輸入中的動畫片段",
        "回首頁",
        "切換分頁",
        "點擊看更多",
        "看解答",
        "實體銷售據點",
        "領試用",
        "恭喜您",
        "客服中心",
    ]:
        assert noise not in result.text
        assert noise not in result.markdown
    assert result.warnings == []
