from typing import Dict, Any
import pandas as pd
from urllib.parse import urlparse
from ..utils import to_list
from ..config import SEOConfig

def analyze_links(df: pd.DataFrame, config: SEOConfig) -> Dict[str, Any]:
    """Analyzes internal vs external link ratio."""
    total_internal = 0
    total_external = 0

    if 'links_url' not in df.columns:
        return {'internal': 0, 'external': 0, 'ratio': 0}

    # Determine target domain from config to check internal/external
    target_domain = urlparse(config.base_url).netloc
    # If config is just "example.com" without scheme, urlparse might put it in path.
    if not target_domain and config.base_url:
            if not config.base_url.startswith(('http://', 'https://')):
                target_domain = config.base_url.split('/')[0]
            else:
                target_domain = config.base_url

    for links in df['links_url']:
        links = to_list(links)
        for l in links:
            if not isinstance(l, str): continue

            if target_domain and target_domain in l:
                total_internal += 1
            elif l.startswith('http'):
                total_external += 1
            elif l.startswith('/') or l.startswith('#'):
                # Relative links are internal
                total_internal += 1

    ratio = (total_internal / total_external) if total_external > 0 else total_internal

    return {
        'internal': total_internal,
        'external': total_external,
        'ratio': ratio
    }
