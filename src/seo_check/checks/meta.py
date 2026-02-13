from typing import Dict, Any, List
import pandas as pd
from ..utils import to_list
from ..config import SEOConfig

def analyze_h1_tags(df: pd.DataFrame, config: SEOConfig = None) -> Dict[str, Any]:
    """Analyzes H1 tags usage."""
    total = len(df)
    if 'h1' not in df.columns:
        return {
            'no_h1': df['url'].tolist(),
            'multiple_h1': [],
            'duplicate_h1': {},
            'total': total,
            'missing_pct': 100
        }

    no_h1 = []
    multiple_h1 = []
    h1_values = []

    for _, row in df.iterrows():
        h1s = to_list(row.get('h1'))
        h1s = [h for h in h1s if h.strip()]

        if not h1s:
            no_h1.append(row['url'])
        elif len(h1s) > 1:
            multiple_h1.append(row['url'])
            h1_values.extend([{'h1': h, 'url': row['url']} for h in h1s])
        else:
            h1_values.append({'h1': h1s[0], 'url': row['url']})

    h1_df = pd.DataFrame(h1_values)
    if not h1_df.empty:
        duplicates = h1_df[h1_df.duplicated(subset=['h1'], keep=False)]
        duplicate_groups = duplicates.groupby('h1')['url'].apply(list).to_dict()
    else:
        duplicate_groups = {}

    return {
        'no_h1': no_h1,
        'multiple_h1': multiple_h1,
        'duplicate_h1': duplicate_groups,
        'total': total,
        'missing_pct': (len(no_h1) / total) * 100 if total > 0 else 0
    }

def analyze_titles(df: pd.DataFrame, config: SEOConfig) -> Dict[str, Any]:
    """Analyzes page titles."""
    total = len(df)
    if 'title' not in df.columns:
        return {
            'no_title': df['url'].tolist(),
            'short': [],
            'long': [],
            'duplicates': {},
            'total': total,
            'missing_pct': 100,
            'duplicate_pct': 0
        }

    no_title = df[df['title'].isna() | (df['title'] == '')]['url'].tolist()

    short_titles = df[df['title'].str.len() < config.title_min_length]['url'].tolist()
    long_titles = df[df['title'].str.len() > config.title_max_length]['url'].tolist()

    duplicates = df[df.duplicated(subset=['title'], keep=False) & df['title'].notna() & (df['title'] != '')]
    duplicate_groups = duplicates.groupby('title')['url'].apply(list).to_dict()

    return {
        'no_title': no_title,
        'short': short_titles,
        'long': long_titles,
        'duplicates': duplicate_groups,
        'total': total,
        'missing_pct': (len(no_title) / total) * 100 if total > 0 else 0,
        'duplicate_pct': (len(duplicates) / total) * 100 if total > 0 else 0
    }

def analyze_meta_desc(df: pd.DataFrame, config: SEOConfig) -> Dict[str, Any]:
    """Analyzes meta descriptions."""
    total = len(df)
    col_name = 'meta_desc'
    if col_name not in df.columns:
            return {
                'no_meta': df['url'].tolist(),
                'short': [],
                'long': [],
                'duplicates': {},
                'total': total,
                'missing_pct': 100
            }

    no_meta = df[df[col_name].isna() | (df[col_name] == '')]['url'].tolist()

    short_meta = df[df[col_name].str.len() < config.meta_desc_min_length]['url'].tolist()
    long_meta = df[df[col_name].str.len() > config.meta_desc_max_length]['url'].tolist()

    duplicates = df[df.duplicated(subset=[col_name], keep=False) & df[col_name].notna() & (df[col_name] != '')]
    duplicate_groups = duplicates.groupby(col_name)['url'].apply(list).to_dict()

    return {
        'no_meta': no_meta,
        'short': short_meta,
        'long': long_meta,
        'duplicates': duplicate_groups,
        'total': total,
        'missing_pct': (len(no_meta) / total) * 100 if total > 0 else 0
    }

def analyze_canonical(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes canonical tags."""
    total = len(df)
    if 'canonical' not in df.columns:
            return {
                'no_canonical': df['url'].tolist(),
                'diff': [],
                'total': total,
                'missing_pct': 100
            }

    no_canonical = df[df['canonical'].isna()]['url'].tolist()

    diff_canonical = df[(df['url'] != df['canonical']) & df['canonical'].notna()]
    diff_list = diff_canonical[['url', 'canonical']].to_dict('records')

    return {
        'no_canonical': no_canonical,
        'diff': diff_list,
        'total': total,
        'missing_pct': (len(no_canonical) / total) * 100 if total > 0 else 0
    }
