"""Hreflang check — detects multilingual sites missing hreflang annotations."""
import re
from typing import Dict, Any
import pandas as pd


_LANG_CODE_RE = re.compile(
    r'/(?:en|es|fr|de|it|pt|nl|pl|ru|ja|ko|zh|ar|sv|da|fi|nb|tr|cs|hu|ro|bg|hr|sk|sl|lt|lv|et)(?:/|$|-)',
    re.IGNORECASE,
)


def analyze_hreflang(df: pd.DataFrame) -> Dict[str, Any]:
    """Detects whether the site appears multilingual and whether hreflang is present.

    A site is considered multilingual if > 10 % of URLs contain a language-code segment
    (e.g. /en/, /es/, /fr/).

    Args:
        df: Full crawl DataFrame (all status codes).

    Returns:
        Dict with appears_multilingual, has_hreflang, hreflang_count,
        missing_hreflang (bool, True when multilingual site lacks hreflang).
    """
    total = len(df)
    if total == 0:
        return {
            'appears_multilingual': False,
            'has_hreflang': False,
            'hreflang_count': 0,
            'missing_hreflang': False,
        }

    # --- Detect multilingual URLs ---
    lang_url_count = 0
    for url in df.get('url', pd.Series(dtype=str)):
        if _LANG_CODE_RE.search(str(url)):
            lang_url_count += 1

    appears_multilingual = (lang_url_count / total) > 0.10

    # --- Detect hreflang presence ---
    hreflang_count = 0

    # Check HTTP Link header (e.g. servers that inject hreflang as HTTP header)
    link_col = 'resp_headers_Link'
    if link_col in df.columns:
        for val in df[link_col].fillna(''):
            if 'hreflang' in str(val).lower():
                hreflang_count += 1

    # advertools stores <link rel="alternate" hreflang="..."> in the 'alt_hreflang' column
    # (@@-separated values per page, e.g. "en@@es@@x-default").
    # Also fall back to any column whose name contains 'hreflang' for forward compatibility.
    hreflang_cols = [c for c in df.columns if 'hreflang' in c.lower()]
    for col in hreflang_cols:
        non_empty = df[col].dropna()
        non_empty = non_empty[non_empty.astype(str).str.strip() != '']
        hreflang_count += len(non_empty)

    has_hreflang = hreflang_count > 0
    missing_hreflang = appears_multilingual and not has_hreflang

    return {
        'appears_multilingual': appears_multilingual,
        'has_hreflang': has_hreflang,
        'hreflang_count': hreflang_count,
        'missing_hreflang': missing_hreflang,
    }
