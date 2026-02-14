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
