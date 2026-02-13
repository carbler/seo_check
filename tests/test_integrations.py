import pytest
import pandas as pd
from seo_check.analyzer import SEOAnalyzer
from seo_check.config import SEOConfig

@pytest.fixture
def analyzer():
    return SEOAnalyzer(SEOConfig())

def test_analyzer_with_integrations(analyzer):
    """Test analyzer with GSC and Lighthouse data."""
    # Mock Crawl Data
    data = {
        'url': ['https://example.com/page1', 'https://example.com/page2'],
        'status': [200, 200],
        'title': ['Page 1', 'Page 2'],
        'meta_desc': ['Desc 1', 'Desc 2'],
        'h1': ['H1 1', 'H1 2'],
        'img_src': [[], []],
        'img_alt': [[], []],
        'canonical': ['https://example.com/page1', 'https://example.com/page2'],
        'links_url': [[], []],
        'size': [1000, 1000],
        'download_latency': [0.1, 0.1]
    }
    df = pd.DataFrame(data)

    # Mock GSC Data
    gsc_data = {
        'https://example.com/page1': {'clicks': 100, 'impressions': 1000, 'ctr': 0.1, 'position': 5.5},
        'https://example.com/page2': {'clicks': 0, 'impressions': 10, 'ctr': 0.0, 'position': 50.0}
    }

    # Mock Lighthouse Data (Global for now, or per URL if we implement that later)
    lighthouse_data = {
        'performance_score': 0.85,
        'lcp_ms': 2500
    }

    metrics = analyzer.analyze(df, gsc_data=gsc_data, lighthouse_data=lighthouse_data)

    # Verify Integrations are present in output
    assert metrics['integrations']['gsc'] == gsc_data
    assert metrics['integrations']['lighthouse'] == lighthouse_data

    # Verify Page Details have GSC data
    page1_details = metrics['page_details']['https://example.com/page1']
    assert page1_details['gsc']['clicks'] == 100
    assert page1_details['gsc']['position'] == 5.5

    page2_details = metrics['page_details']['https://example.com/page2']
    assert page2_details['gsc']['clicks'] == 0
