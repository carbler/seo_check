import asyncio
import pytest
import pandas as pd
from unittest.mock import patch
from seo_check.analyzer import SEOAnalyzer
from seo_check.config import SEOConfig
from seo_check.checks.indexability import analyze_indexability
from seo_check.checks.robots import analyze_robots_txt
from seo_check.checks.duplicates import analyze_duplicate_content
from seo_check.checks.mixed_content import analyze_mixed_content
from seo_check.checks.anchors import analyze_anchor_text
from seo_check.checks.headers import analyze_response_headers
from seo_check.checks.url_quality import analyze_url_quality
from seo_check.checks.hreflang import analyze_hreflang

@pytest.fixture
def analyzer():
    return SEOAnalyzer(SEOConfig())

def test_analyzer_happy_path(analyzer):
    """Test analyzer with complete data."""
    data = {
        'url': ['https://example.com/1', 'https://example.com/2'],
        'status': [200, 404],
        'h1': ['Header 1', ''],
        'title': ['Title 1', 'Title 2'],
        'meta_desc': ['Desc 1', ''],
        'canonical': ['https://example.com/1', 'https://example.com/2'],
        'img_alt': ['Alt 1', ''],
        'img_src': ['img1.jpg', 'img2.jpg'],
        'links_url': ['https://example.com/2', 'https://google.com'],
        'size': [1000, 1000],
        'download_latency': [0.1, 0.2]
    }
    df = pd.DataFrame(data)
    metrics = analyzer.analyze(df)

    assert metrics['http']['total'] == 2
    assert len(metrics['http']['broken_links']) == 1
    # Updated expectation: 404 pages are filtered out from semantic checks, so no H1/Meta errors reported
    assert len(metrics['h1']['no_h1']) == 0
    assert len(metrics['meta']['no_meta']) == 0
    assert metrics['issues'] is not None

def test_analyzer_score_fairness(analyzer):
    """Test that 404 pages do not trigger semantic penalties (H1, Title, etc)."""
    from seo_check.analyzer import SEOScorer
    scorer = SEOScorer(analyzer.config)
    
    # Create scenario: 5 good pages, 5 broken pages (404)
    # The broken pages naturally lack H1, Meta, etc.
    data = {
        'url': [f'http://site.com/{i}' for i in range(10)],
        'status': [200]*5 + [404]*5,
        'h1': ['My Header']*5 + ['']*5,
        'title': ['My Title']*5 + ['']*5,
        'meta_desc': ['My Desc']*5 + ['']*5,
        'canonical': [f'http://site.com/{i}' for i in range(10)], # Assume canonical exists or doesn't matter for this test
        'img_alt': ['Alt']*10,
        'img_src': ['img.jpg']*10,
        'size': [1000]*10,
        'download_latency': [0.1]*10
    }
    df = pd.DataFrame(data)
    metrics = analyzer.analyze(df)
    
    # Check intermediate metrics
    assert metrics['http']['error_rate_4xx'] == 50.0
    # Semantic metrics should be clean (0% missing because only 200 pages are checked)
    assert metrics['h1']['missing_pct'] == 0.0
    assert metrics['title']['missing_pct'] == 0.0
    assert metrics['meta']['missing_pct'] == 0.0
    
    # Check final score
    score, rating, penalties = scorer.calculate(metrics)
    
    # Penalties should ONLY contain Broken Links
    # And NOT "Missing H1", "Missing Titles", etc.
    penalty_names = [p.split(' (>')[0].split(' (')[0] for p in penalties]
    assert "Broken Links" in penalty_names
    assert "Missing H1" not in penalty_names
    assert "Missing Titles" not in penalty_names
    assert "Missing Meta Desc" not in penalty_names

def test_analyzer_missing_columns(analyzer):
    """Test analyzer with missing columns (simulating restricted crawl)."""
    # Only URL and Status, missing everything else
    data = {
        'url': ['https://example.com/1'],
        'status': [200]
    }
    df = pd.DataFrame(data)

    # Should not raise KeyError
    metrics = analyzer.analyze(df)

    # Check fallback values
    assert metrics['h1']['missing_pct'] == 100
    assert len(metrics['h1']['no_h1']) == 1
    assert metrics['title']['missing_pct'] == 100
    assert len(metrics['title']['no_title']) == 1
    assert metrics['meta']['missing_pct'] == 100
    assert len(metrics['meta']['no_meta']) == 1

    # Check categorization
    assert len(metrics['issues']['warnings']) > 0  # Should trigger warnings for missing tags

def test_analyzer_empty_dataframe(analyzer):
    """Test analyzer with empty dataframe."""
    df = pd.DataFrame()
    # Depending on implementation, load_data returns None or empty DF.
    # But analyze expects DF.
    metrics = analyzer.analyze(df)

    assert metrics['http']['total'] == 0
    assert metrics['h1']['total'] == 0


# ---------------------------------------------------------------------------
# New checks — unit tests
# ---------------------------------------------------------------------------

def test_indexability_noindex_detection():
    """Pages with meta_robots='noindex' should be flagged."""
    df = pd.DataFrame({
        'url': ['https://example.com/a', 'https://example.com/b', 'https://example.com/c'],
        'status': [200, 200, 200],
        'meta_robots': ['noindex, nofollow', 'index, follow', ''],
    })
    result = analyze_indexability(df)
    assert 'https://example.com/a' in result['noindex_pages']
    assert 'https://example.com/b' not in result['noindex_pages']
    assert 'https://example.com/a' in result['nofollow_pages']
    assert result['noindex_pct'] == pytest.approx(100 / 3, rel=0.01)


def test_indexability_x_robots_noindex():
    """Pages with X-Robots-Tag: noindex should appear in x_robots_noindex."""
    df = pd.DataFrame({
        'url': ['https://example.com/x', 'https://example.com/y'],
        'status': [200, 200],
        'resp_headers_X-Robots-Tag': ['noindex', ''],
    })
    result = analyze_indexability(df)
    assert 'https://example.com/x' in result['x_robots_noindex']
    assert 'https://example.com/x' in result['noindex_pages']
    assert 'https://example.com/y' not in result['x_robots_noindex']


def test_robots_disallow():
    """URLs blocked by robots.txt should appear in disallowed_urls."""
    df = pd.DataFrame({
        'url': ['https://example.com/', 'https://example.com/private/'],
        'status': [200, 200],
    })
    with patch('urllib.robotparser.RobotFileParser.read'):
        with patch('urllib.robotparser.RobotFileParser.can_fetch', side_effect=lambda ua, url: '/private/' not in url):
            result = analyze_robots_txt(df, 'https://example.com', user_agent='*')

    assert result['robots_fetched'] is True
    assert 'https://example.com/private/' in result['disallowed_urls']
    assert 'https://example.com/' not in result['disallowed_urls']
    assert result['disallowed_count'] == 1


def test_duplicate_content_detection():
    """Two pages sharing the same body text hash should be flagged."""
    shared_text = 'a ' * 600  # 600 words, well over 100 chars
    df = pd.DataFrame({
        'url': ['https://example.com/p1', 'https://example.com/p2', 'https://example.com/p3'],
        'status': [200, 200, 200],
        'page_body_text': [shared_text, shared_text, 'completely different content ' * 50],
    })
    result = analyze_duplicate_content(df)
    assert len(result['duplicate_groups']) == 1
    group = list(result['duplicate_groups'].values())[0]
    assert 'https://example.com/p1' in group
    assert 'https://example.com/p2' in group
    assert 'https://example.com/p3' not in result['duplicate_urls']
    assert result['duplicate_pct'] == pytest.approx(200 / 3, rel=0.01)


def test_duplicate_content_skips_short_pages():
    """Pages with fewer than 100 characters should not be considered for duplicate check."""
    df = pd.DataFrame({
        'url': ['https://example.com/empty1', 'https://example.com/empty2'],
        'status': [200, 200],
        'page_body_text': ['short', 'short'],
    })
    result = analyze_duplicate_content(df)
    assert result['duplicate_urls'] == []
    assert result['duplicate_pct'] == 0.0


def test_mixed_content_https_page_with_http_image():
    """An HTTPS page embedding an HTTP image should be flagged as mixed content."""
    df = pd.DataFrame({
        'url': ['https://example.com/page', 'https://example.com/clean'],
        'status': [200, 200],
        'img_src': ['http://cdn.example.com/img.jpg', 'https://cdn.example.com/img.jpg'],
        'links_url': ['', ''],
    })
    result = analyze_mixed_content(df)
    assert result['mixed_content_count'] == 1
    assert result['mixed_content_pages'][0]['url'] == 'https://example.com/page'
    assert 'http://cdn.example.com/img.jpg' in result['mixed_content_pages'][0]['http_resources']


def test_mixed_content_http_page_ignored():
    """HTTP pages should not be checked for mixed content."""
    df = pd.DataFrame({
        'url': ['http://example.com/page'],
        'status': [200],
        'img_src': ['http://cdn.example.com/img.jpg'],
        'links_url': [''],
    })
    result = analyze_mixed_content(df)
    assert result['mixed_content_count'] == 0


def test_anchor_text_generic_detection():
    """Internal links with generic anchor text should be detected."""
    df = pd.DataFrame({
        'url': ['https://example.com/page'],
        'status': [200],
        'links_url': ['https://example.com/other@@https://example.com/about'],
        'links_text': ['click here@@About Us'],
        'links_nofollow': ['False@@False'],
    })
    result = analyze_anchor_text(df, 'https://example.com')
    assert result['total_internal_links'] == 2
    assert result['generic_pct'] == pytest.approx(50.0, rel=0.01)
    assert any(a['anchor'] == 'click here' for a in result['generic_anchor_links'])


def test_anchor_text_nofollow_internal():
    """Internal links with nofollow should be detected."""
    df = pd.DataFrame({
        'url': ['https://example.com/page'],
        'status': [200],
        'links_url': ['https://example.com/other'],
        'links_text': ['Read article'],
        'links_nofollow': ['True'],
    })
    result = analyze_anchor_text(df, 'https://example.com')
    assert len(result['nofollow_internal_links']) == 1
    assert result['nofollow_internal_pct'] == pytest.approx(100.0, rel=0.01)


def test_response_headers_no_compression():
    """HTML pages without Content-Encoding should be flagged as lacking compression."""
    df = pd.DataFrame({
        'url': ['https://example.com/', 'https://example.com/page'],
        'status': [200, 200],
        'resp_headers_Content-Type': ['text/html; charset=utf-8', 'text/html'],
        'resp_headers_Content-Encoding': ['gzip', ''],
        'resp_headers_Cache-Control': ['max-age=3600', 'max-age=3600'],
    })
    result = analyze_response_headers(df)
    assert 'https://example.com/page' in result['no_compression_urls']
    assert 'https://example.com/' not in result['no_compression_urls']
    assert result['no_compression_pct'] == pytest.approx(50.0, rel=0.01)


def test_url_quality_underscores():
    """URLs with underscores in the path should be flagged."""
    df = pd.DataFrame({
        'url': ['https://example.com/my_page', 'https://example.com/my-page'],
        'status': [200, 200],
    })
    result = analyze_url_quality(df)
    assert 'https://example.com/my_page' in result['urls_with_underscores']
    assert 'https://example.com/my-page' not in result['urls_with_underscores']


def test_url_quality_deep_urls():
    """URLs deeper than 4 levels should be flagged."""
    df = pd.DataFrame({
        'url': ['https://example.com/a/b/c/d/e', 'https://example.com/a/b'],
        'status': [200, 200],
    })
    result = analyze_url_quality(df)
    assert 'https://example.com/a/b/c/d/e' in result['deep_urls']
    assert 'https://example.com/a/b' not in result['deep_urls']


def test_hreflang_multilingual_without_hreflang():
    """A site with language-code URLs but no hreflang should set missing_hreflang=True."""
    df = pd.DataFrame({
        'url': [f'https://example.com/en/page{i}' for i in range(10)]
             + [f'https://example.com/es/page{i}' for i in range(10)],
        'status': [200] * 20,
    })
    result = analyze_hreflang(df)
    assert result['appears_multilingual'] is True
    assert result['has_hreflang'] is False
    assert result['missing_hreflang'] is True


def test_hreflang_monolingual_no_hreflang():
    """A monolingual site without hreflang should NOT set missing_hreflang=True."""
    df = pd.DataFrame({
        'url': [f'https://example.com/page{i}' for i in range(10)],
        'status': [200] * 10,
    })
    result = analyze_hreflang(df)
    assert result['appears_multilingual'] is False
    assert result['missing_hreflang'] is False
