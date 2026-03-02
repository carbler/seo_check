"""URL quality check — flags underscores, uppercase, params, special chars, deep URLs."""
import re
from typing import Dict, Any, List
import pandas as pd
from urllib.parse import urlparse, parse_qs


_SPECIAL_CHAR_RE = re.compile(r'%[0-9A-Fa-f]{2}')
_ALLOWED_ENCODED = {'%2F', '%2f'}


def _url_path(url: str) -> str:
    """Returns just the path component of a URL."""
    try:
        return urlparse(url).path
    except Exception:
        return ''


def _url_depth(url: str) -> int:
    """Returns URL depth (number of path segments)."""
    path = _url_path(url)
    return len([s for s in path.split('/') if s])


def analyze_url_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Checks URL structure quality for SEO best practices.

    Operates on df_valid (status=200 only) passed from analyzer.
    Flags:
    - Underscores in path (prefer hyphens)
    - Uppercase letters in path
    - Query parameters (>2 params)
    - Special encoded characters in path
    - Deep URLs (depth > 4)

    Args:
        df: Filtered DataFrame (200 OK pages).

    Returns:
        Dict with urls_with_underscores, urls_with_uppercase, urls_with_params,
        urls_with_special_chars, deep_urls, any_issue_pct.
    """
    urls_with_underscores: List[str] = []
    urls_with_uppercase: List[str] = []
    urls_with_params: List[str] = []
    urls_with_special_chars: List[str] = []
    deep_urls: List[str] = []

    for _, row in df.iterrows():
        url = str(row.get('url', ''))
        if not url:
            continue

        try:
            parsed = urlparse(url)
        except Exception:
            continue

        path = parsed.path

        if '_' in path:
            urls_with_underscores.append(url)

        # Check uppercase (ignore scheme and netloc)
        if path != path.lower():
            urls_with_uppercase.append(url)

        # Query params
        params = parse_qs(parsed.query)
        if len(params) > 2:
            urls_with_params.append(url)

        # Special encoded chars (excluding %2F which is a slash)
        encoded_matches = _SPECIAL_CHAR_RE.findall(path)
        non_slash_encoded = [m for m in encoded_matches if m.upper() not in _ALLOWED_ENCODED]
        if non_slash_encoded:
            urls_with_special_chars.append(url)

        # Depth
        if _url_depth(url) > 4:
            deep_urls.append(url)

    total = len(df)
    # "any issue" set — unique URLs with at least one problem
    any_issue_urls = set(
        urls_with_underscores
        + urls_with_uppercase
        + urls_with_params
        + urls_with_special_chars
        + deep_urls
    )
    any_issue_pct = (len(any_issue_urls) / total * 100) if total > 0 else 0.0

    return {
        'urls_with_underscores': urls_with_underscores,
        'urls_with_uppercase': urls_with_uppercase,
        'urls_with_params': urls_with_params,
        'urls_with_special_chars': urls_with_special_chars,
        'deep_urls': deep_urls,
        'any_issue_pct': any_issue_pct,
    }
