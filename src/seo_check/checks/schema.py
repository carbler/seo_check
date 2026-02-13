from typing import Dict, Any
import pandas as pd

def analyze_schema_presence(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes JSON-LD schema presence."""
    total = len(df)
    
    # Check for 'jsonld' column or any flattened 'jsonld_' columns
    jsonld_cols = [c for c in df.columns if c == 'jsonld' or c.startswith('jsonld_')]
    
    if jsonld_cols:
        # A page has schema if any of the jsonld columns is not null
        has_schema = df[jsonld_cols].notna().any(axis=1)
        present_count = has_schema.sum()
        missing_urls = df[~has_schema]['url'].tolist()
    else:
        missing_urls = df['url'].tolist()
        present_count = 0

    return {
        'present_count': present_count,
        'missing_urls': missing_urls,
        'total': total
    }
