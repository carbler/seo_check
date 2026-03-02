"""Indexability check — detects noindex/nofollow directives via meta_robots and X-Robots-Tag."""
from typing import Dict, Any
import pandas as pd
from ..utils import to_list


def analyze_indexability(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes indexability signals: meta_robots and X-Robots-Tag headers.

    Uses the full DataFrame (including non-200 pages) because we want to detect
    accidental noindex on any crawled URL, not just valid pages.
    """
    noindex_pages: list = []
    nofollow_pages: list = []
    x_robots_noindex: list = []

    has_meta_robots = 'meta_robots' in df.columns
    has_x_robots = 'resp_headers_X-Robots-Tag' in df.columns

    for _, row in df.iterrows():
        url = str(row.get('url', ''))

        if has_meta_robots:
            meta_robots_val = str(row.get('meta_robots', '') or '').lower()
            if 'noindex' in meta_robots_val:
                noindex_pages.append(url)
            if 'nofollow' in meta_robots_val:
                nofollow_pages.append(url)

        if has_x_robots:
            x_robots_val = str(row.get('resp_headers_X-Robots-Tag', '') or '').lower()
            if 'noindex' in x_robots_val and url not in x_robots_noindex:
                x_robots_noindex.append(url)
                # Also add to noindex_pages if not already there from meta
                if url not in noindex_pages:
                    noindex_pages.append(url)

    total = len(df)
    noindex_pct = (len(noindex_pages) / total * 100) if total > 0 else 0.0

    return {
        'noindex_pages': noindex_pages,
        'nofollow_pages': nofollow_pages,
        'x_robots_noindex': x_robots_noindex,
        'noindex_pct': noindex_pct,
    }
