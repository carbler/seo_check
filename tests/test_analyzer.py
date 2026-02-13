import pytest
import pandas as pd
from seo_check.analyzer import SEOAnalyzer
from seo_check.config import SEOConfig

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
    assert len(metrics['h1']['no_h1']) == 1
    assert len(metrics['meta']['no_meta']) == 1
    assert metrics['issues'] is not None

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
