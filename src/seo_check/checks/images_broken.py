"""Broken images check — verifies image URLs return successful HTTP responses."""
import asyncio
import logging
from typing import Dict, Any, List
import pandas as pd

from ..utils import to_list

_MAX_IMAGES = 200
_TIMEOUT = 5.0


async def _check_images(image_urls: List[str]) -> List[Dict[str, Any]]:
    """HEAD-checks image URLs concurrently, returns list of broken ones."""
    try:
        import httpx
    except ImportError:
        logging.warning("httpx not installed — skipping broken image check.")
        return []

    broken: List[Dict[str, Any]] = []
    semaphore = asyncio.Semaphore(20)

    async def check_one(img_url: str) -> None:
        async with semaphore:
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=_TIMEOUT) as client:
                    resp = await client.head(img_url)
                    if resp.status_code >= 400:
                        broken.append({'img_src': img_url, 'status': resp.status_code})
            except Exception:
                broken.append({'img_src': img_url, 'status': 0})

    await asyncio.gather(*[check_one(u) for u in image_urls])
    return broken


async def analyze_broken_images(df: pd.DataFrame) -> Dict[str, Any]:
    """Checks all unique absolute image URLs found in the crawl for broken responses.

    Operates on df_valid (status=200 only) passed from analyzer.
    Caps verification at _MAX_IMAGES to keep analysis fast.

    Args:
        df: Filtered DataFrame (200 OK pages).

    Returns:
        Dict with broken_images, broken_count, total_images, broken_pct.
    """
    if 'img_src' not in df.columns:
        return {
            'broken_images': [],
            'broken_count': 0,
            'total_images': 0,
            'broken_pct': 0.0,
        }

    # Collect unique absolute image URLs
    seen: set = set()
    for _, row in df.iterrows():
        for src in to_list(row.get('img_src')):
            if isinstance(src, str) and src.startswith('http') and src not in seen:
                seen.add(src)

    all_images = list(seen)
    sampled = all_images[:_MAX_IMAGES]
    total_images = len(all_images)

    broken = await _check_images(sampled)

    broken_count = len(broken)
    broken_pct = (broken_count / len(sampled) * 100) if sampled else 0.0

    return {
        'broken_images': broken,
        'broken_count': broken_count,
        'total_images': total_images,
        'broken_pct': broken_pct,
    }
