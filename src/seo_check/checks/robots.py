"""Robots.txt check — fetches and validates robots.txt, detecting disallowed crawled URLs."""
import logging
import urllib.robotparser
from typing import Dict, Any
import pandas as pd


def analyze_robots_txt(df: pd.DataFrame, base_url: str, user_agent: str = '*') -> Dict[str, Any]:
    """Fetches robots.txt from base_url and checks which crawled URLs are disallowed.

    Args:
        df: Full crawl DataFrame (all status codes).
        base_url: Site root URL (e.g. 'https://example.com').
        user_agent: User-agent string to test against robots.txt rules.

    Returns:
        Dict with robots_txt_url, robots_fetched, disallowed_urls, disallowed_count.
    """
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    robots_txt_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_txt_url)

    robots_fetched = False
    disallowed_urls: list = []

    try:
        rp.read()
        robots_fetched = True
    except Exception as exc:
        logging.warning(f"Could not fetch robots.txt from {robots_txt_url}: {exc}")
        return {
            'robots_txt_url': robots_txt_url,
            'robots_fetched': False,
            'disallowed_urls': [],
            'disallowed_count': 0,
        }

    for _, row in df.iterrows():
        url = str(row.get('url', ''))
        if not url:
            continue
        try:
            if not rp.can_fetch(user_agent, url):
                disallowed_urls.append(url)
        except Exception:
            pass

    return {
        'robots_txt_url': robots_txt_url,
        'robots_fetched': robots_fetched,
        'disallowed_urls': disallowed_urls,
        'disallowed_count': len(disallowed_urls),
    }
