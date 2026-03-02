"""Duplicate content check — detects pages sharing identical body text hashes."""
import hashlib
import re
from typing import Dict, Any
import pandas as pd


# advertools joins multiple text nodes with '@@' — strip them out before hashing
_ADVERTOOLS_SEP_RE = re.compile(r'\s*@@\s*')

# Minimum length of *cleaned* text before we consider a page for dedup.
# Keeps near-empty pages (login screens, redirect stubs, etc.) out of the comparison.
_MIN_CLEAN_CHARS = 150


def _clean_for_hash(raw: str) -> str:
    """Replace advertools @@ separators and collapse whitespace."""
    text = _ADVERTOOLS_SEP_RE.sub(' ', raw)
    return ' '.join(text.split()).lower().strip()


def analyze_duplicate_content(df: pd.DataFrame) -> Dict[str, Any]:
    """Detects duplicate page content by MD5-hashing the full cleaned body text.

    Why full-text hash instead of a snippet:
    - Scrapy's ``body ::text`` selector includes ``<script>`` tag content, so the
      first N characters of extracted text are usually shared nav + inline JavaScript
      (same on every page of a site). Hashing only the first N chars produces false
      positives for every page.
    - The full text differs between pages as long as they have *any* unique content,
      so the full-text MD5 is reliable and avoids template-pollution false positives.
    - True duplicates (pages where every word is identical) still produce the same hash.

    Operates on df_valid (status=200 only) passed from analyzer.

    Args:
        df: Filtered DataFrame (200 OK pages).

    Returns:
        Dict with duplicate_groups, duplicate_urls, duplicate_pct.
    """
    col_name = 'page_body_text' if 'page_body_text' in df.columns else 'body_text'

    if col_name not in df.columns:
        return {
            'duplicate_groups': {},
            'duplicate_urls': [],
            'duplicate_pct': 0.0,
        }

    hash_map: dict = {}

    for _, row in df.iterrows():
        url = str(row.get('url', ''))
        raw_text = str(row.get(col_name, '') or '')

        cleaned = _clean_for_hash(raw_text)
        if len(cleaned) < _MIN_CLEAN_CHARS:
            continue

        # Hash the full cleaned text — not a snippet — to avoid false positives
        # caused by shared nav / inline JavaScript at the start of every page.
        content_hash = hashlib.md5(cleaned.encode('utf-8', errors='replace')).hexdigest()

        if content_hash not in hash_map:
            hash_map[content_hash] = []
        hash_map[content_hash].append(url)

    # Keep only groups with more than one URL
    duplicate_groups = {h: urls for h, urls in hash_map.items() if len(urls) > 1}

    duplicate_urls: list = []
    for urls in duplicate_groups.values():
        duplicate_urls.extend(urls)
    duplicate_urls = list(dict.fromkeys(duplicate_urls))

    total = len(df)
    duplicate_pct = (len(duplicate_urls) / total * 100) if total > 0 else 0.0

    return {
        'duplicate_groups': duplicate_groups,
        'duplicate_urls': duplicate_urls,
        'duplicate_pct': duplicate_pct,
    }
