from typing import Dict, Any
import pandas as pd

def analyze_social_tags(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes Open Graph tags."""
    total = len(df)
    
    # Common columns for social titles/descriptions
    title_cols = ['og:title', 'og_title', 'twitter:title']
    desc_cols = ['og:description', 'og_description', 'twitter:description']
    img_cols = ['og:image', 'og_image', 'twitter:image']

    present_titles = df.columns.intersection(title_cols)
    present_descs = df.columns.intersection(desc_cols)
    present_imgs = df.columns.intersection(img_cols)

    if not present_titles.empty:
        has_title = df[present_titles].notna().any(axis=1)
        og_title_count = has_title.sum()
        missing_urls = df[~has_title]['url'].tolist()
    else:
        og_title_count = 0
        missing_urls = df['url'].tolist()

    og_desc_count = df[present_descs].notna().any(axis=1).sum() if not present_descs.empty else 0
    og_image_count = df[present_imgs].notna().any(axis=1).sum() if not present_imgs.empty else 0

    return {
        'og_title_count': int(og_title_count),
        'og_desc_count': int(og_desc_count),
        'og_image_count': int(og_image_count),
        'missing_urls': missing_urls,
        'total': total
    }
