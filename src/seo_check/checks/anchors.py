"""Anchor text checks — generic anchor text and nofollow on internal links."""
from typing import Dict, Any, List
import pandas as pd
from urllib.parse import urlparse
from ..utils import to_list


_GENERIC_ANCHORS = {
    'click here', 'here', 'read more', 'more', 'link', 'this', 'page',
    'leer más', 'aquí', 'ver más', 'learn more', 'continue', 'go',
}


def _is_internal(link_url: str, base_netloc: str) -> bool:
    """Returns True if link_url belongs to the same netloc as base_netloc."""
    if not link_url:
        return False
    if link_url.startswith('/') or link_url.startswith('#'):
        return True
    try:
        return urlparse(link_url).netloc == base_netloc
    except Exception:
        return False


def analyze_anchor_text(df: pd.DataFrame, base_url: str) -> Dict[str, Any]:
    """Analyzes anchor text quality and nofollow usage on internal links.

    Operates on df_valid (status=200 only) passed from analyzer.

    Args:
        df: Filtered DataFrame (200 OK pages).
        base_url: Site root URL used to determine internal vs external links.

    Returns:
        Dict with generic_anchor_links, generic_pct, total_internal_links,
        nofollow_internal_links, nofollow_internal_pct.
    """
    base_netloc = urlparse(base_url).netloc

    has_links_url = 'links_url' in df.columns
    has_links_text = 'links_text' in df.columns
    has_nofollow = 'links_nofollow' in df.columns

    if not has_links_url:
        return {
            'generic_anchor_links': [],
            'generic_pct': 0.0,
            'total_internal_links': 0,
            'nofollow_internal_links': [],
            'nofollow_internal_pct': 0.0,
        }

    generic_anchor_links: List[Dict[str, str]] = []
    nofollow_internal_links: List[Dict[str, str]] = []
    total_internal = 0

    for _, row in df.iterrows():
        page_url = str(row.get('url', ''))
        link_urls = to_list(row.get('links_url'))
        link_texts = to_list(row.get('links_text')) if has_links_text else []
        link_nofollows = to_list(row.get('links_nofollow')) if has_nofollow else []

        for i, lurl in enumerate(link_urls):
            if not isinstance(lurl, str):
                continue
            if not _is_internal(lurl, base_netloc):
                continue

            total_internal += 1

            # Generic anchor check
            anchor = (link_texts[i] if i < len(link_texts) else '').strip().lower()
            if anchor in _GENERIC_ANCHORS:
                generic_anchor_links.append({
                    'page_url': page_url,
                    'link_url': lurl,
                    'anchor': anchor,
                })

            # Nofollow check
            nofollow_val = str(link_nofollows[i] if i < len(link_nofollows) else '').strip().lower()
            is_nofollow = nofollow_val in ('true', '1', 'nofollow', 'yes')
            if is_nofollow:
                nofollow_internal_links.append({
                    'page_url': page_url,
                    'link_url': lurl,
                })

    generic_pct = (len(generic_anchor_links) / total_internal * 100) if total_internal > 0 else 0.0
    nofollow_pct = (len(nofollow_internal_links) / total_internal * 100) if total_internal > 0 else 0.0

    return {
        'generic_anchor_links': generic_anchor_links,
        'generic_pct': generic_pct,
        'total_internal_links': total_internal,
        'nofollow_internal_links': nofollow_internal_links,
        'nofollow_internal_pct': nofollow_pct,
    }
