"""Response headers check — compression, cache-control, and X-Robots-Tag quality."""
from typing import Dict, Any
import pandas as pd


def analyze_response_headers(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes HTTP response headers for compression and cache quality.

    Only considers HTML pages (Content-Type contains 'text/html') with status 200.
    Checks:
    - Compression: Content-Encoding should contain 'gzip' or 'br'.
    - Cache-Control: should not be 'no-store' and should contain 'max-age' or 'public'.

    Args:
        df: Full crawl DataFrame (will filter internally to HTML 200 pages).

    Returns:
        Dict with no_compression_urls, no_compression_pct, bad_cache_urls, bad_cache_pct.
    """
    # Build HTML-only, status-200 subset
    df_html = df.copy()

    if 'status' in df_html.columns:
        df_html = df_html[df_html['status'] == 200]

    content_type_col = 'resp_headers_Content-Type'
    if content_type_col in df_html.columns:
        df_html = df_html[
            df_html[content_type_col].fillna('').str.contains('text/html', case=False, na=False)
        ]

    no_compression_urls: list = []
    bad_cache_urls: list = []

    encoding_col = 'resp_headers_Content-Encoding'
    cache_col = 'resp_headers_Cache-Control'

    has_encoding = encoding_col in df_html.columns
    has_cache = cache_col in df_html.columns

    for _, row in df_html.iterrows():
        url = str(row.get('url', ''))

        if has_encoding:
            encoding_val = str(row.get(encoding_col, '') or '').lower()
            if 'gzip' not in encoding_val and 'br' not in encoding_val:
                no_compression_urls.append(url)
        else:
            # Column absent → assume no compression for all pages
            no_compression_urls.append(url)

        if has_cache:
            cache_val = str(row.get(cache_col, '') or '').lower()
            is_bad = (
                not cache_val
                or 'no-store' in cache_val
                or ('max-age' not in cache_val and 'public' not in cache_val)
            )
            if is_bad:
                bad_cache_urls.append(url)
        else:
            bad_cache_urls.append(url)

    total_html = len(df_html)
    no_compression_pct = (len(no_compression_urls) / total_html * 100) if total_html > 0 else 0.0
    bad_cache_pct = (len(bad_cache_urls) / total_html * 100) if total_html > 0 else 0.0

    return {
        'no_compression_urls': no_compression_urls,
        'no_compression_pct': no_compression_pct,
        'bad_cache_urls': bad_cache_urls,
        'bad_cache_pct': bad_cache_pct,
    }
