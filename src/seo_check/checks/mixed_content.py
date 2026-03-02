"""Mixed content check — detects HTTP resources embedded in HTTPS pages."""
from typing import Dict, Any, List
import pandas as pd
from ..utils import to_list


def analyze_mixed_content(df: pd.DataFrame) -> Dict[str, Any]:
    """Detects mixed content: HTTP resources (images, links) on HTTPS pages.

    Operates on df_valid (status=200 only) passed from analyzer.

    Args:
        df: Filtered DataFrame (200 OK pages).

    Returns:
        Dict with mixed_content_pages, mixed_content_count, mixed_content_pct.
    """
    mixed_content_pages: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        url = str(row.get('url', ''))
        if not url.startswith('https://'):
            continue

        http_resources: List[str] = []

        for src in to_list(row.get('img_src')):
            if isinstance(src, str) and src.startswith('http://'):
                http_resources.append(src)

        for lurl in to_list(row.get('links_url')):
            if isinstance(lurl, str) and lurl.startswith('http://'):
                http_resources.append(lurl)

        if http_resources:
            mixed_content_pages.append({
                'url': url,
                'http_resources': http_resources,
            })

    total = len(df)
    mixed_content_pct = (len(mixed_content_pages) / total * 100) if total > 0 else 0.0

    return {
        'mixed_content_pages': mixed_content_pages,
        'mixed_content_count': len(mixed_content_pages),
        'mixed_content_pct': mixed_content_pct,
    }
