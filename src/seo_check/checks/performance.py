from typing import Dict, Any
import pandas as pd
from ..config import SEOConfig

def analyze_performance(df: pd.DataFrame, config: SEOConfig) -> Dict[str, Any]:
    """Analyzes performance metrics (speed, size)."""
    if 'download_latency' in df.columns:
        slow_pages = df[df['download_latency'] > config.slow_page_threshold]['url'].tolist()
        avg_time = df['download_latency'].mean()
    else:
        slow_pages = []
        avg_time = 0

    huge_pages = []
    avg_size = 0
    if 'size' in df.columns:
        avg_size = df['size'].mean()
        huge_pages = df[df['size'] > config.max_page_size_bytes]['url'].tolist()

    return {
        'slow_pages': slow_pages,
        'avg_time': avg_time,
        'avg_size_bytes': avg_size,
        'huge_pages': huge_pages
    }
