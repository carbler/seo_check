from typing import Dict, Any
import pandas as pd
from ..utils import to_list
from ..config import SEOConfig

def analyze_images(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes image alt attributes."""
    if 'img_alt' not in df.columns:
        return {
            'missing_alt_details': [],
            'total_images': 0,
            'missing_alt_count': 0,
            'missing_pct': 0
        }

    total_imgs = 0
    missing_alt_count = 0
    missing_alt_urls = []

    for index, row in df.iterrows():
        srcs = to_list(row.get('img_src'))
        alts = to_list(row.get('img_alt'))

        page_imgs = len(srcs)
        if page_imgs == 0: continue

        total_imgs += page_imgs

        empty_in_list = len([x for x in alts if not x or not x.strip()])
        diff = max(0, len(srcs) - len(alts))

        page_missing = empty_in_list + diff

        if page_missing > 0:
            missing_alt_count += page_missing
            missing_alt_urls.append({'url': row['url'], 'count': page_missing})

    return {
        'missing_alt_details': missing_alt_urls,
        'total_images': total_imgs,
        'missing_alt_count': missing_alt_count,
        'missing_pct': (missing_alt_count / total_imgs * 100) if total_imgs > 0 else 0
    }

def analyze_content_quality(df: pd.DataFrame, config: SEOConfig) -> Dict[str, Any]:
    """Analyzes content quality (Word count, Text Ratio)."""
    low_word_count = []
    low_text_ratio = []

    # Check for custom extracted 'page_body_text' or standard 'body_text'
    col_name = 'page_body_text' if 'page_body_text' in df.columns else 'body_text'

    if col_name in df.columns:
        for _, row in df.iterrows():
            # Advertools puts extracted text in one string column if using selectors.
            text_content = str(row.get(col_name, ''))

            # Word Count
            words = len(text_content.split())
            if words < config.min_word_count:
                low_word_count.append({'url': row['url'], 'count': words})

            # Ratio
            # Approximating HTML size from 'size' column (bytes) vs text length
            html_size = row.get('size', 0)
            text_size = len(text_content)

            if html_size > 0:
                ratio = (text_size / html_size) * 100
                if ratio < config.text_ratio_threshold:
                    low_text_ratio.append({'url': row['url'], 'ratio': ratio})

    return {
        'low_word_count': low_word_count,
        'low_text_ratio': low_text_ratio
    }
