import pytest

from super_scraper.inputs import collect_urls, normalize_url


def test_bom_file_comments_and_dedup_preserve_queries(tmp_path):
    file = tmp_path / "urls.txt"
    file.write_text(
        "# comment\n\nhttps://example.com/a#section\nhttps://example.com/a?q=2\n",
        encoding="utf-8-sig",
    )
    assert collect_urls(["https://example.com/a#first"], file) == [
        "https://example.com/a",
        "https://example.com/a?q=2",
    ]


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/test",
        "javascript:alert(1)",
        "example.com",
        "http://",
        "https://a:99999",
        "https://a:abc",
        "https://a b/",
        "http://u:p@host/a",
    ],
)
def test_reject_invalid_url(url):
    with pytest.raises(ValueError):
        normalize_url(url)


def test_invalid_individual_url_is_kept_for_error_reporting():
    assert collect_urls(["https://example.com/a", "bad-url"], None) == [
        "https://example.com/a",
        "bad-url",
    ]


def test_empty_input_and_bad_file_fail_globally(tmp_path):
    with pytest.raises(ValueError):
        collect_urls([], None)
    with pytest.raises(OSError):
        collect_urls([], tmp_path / "missing")
