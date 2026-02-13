from typing import Dict, Any
import pandas as pd

def analyze_url_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes URL structure and depth."""
    if 'url' in df.columns:
        # Calculate depth based on segments
        df['depth'] = df['url'].astype(str).apply(lambda x: x.rstrip('/').count('/') - 2) # Subtract scheme segments
        # Ensure depth is at least 0
        df['depth'] = df['depth'].clip(lower=0)
        
        avg_depth = df['depth'].mean()
        max_depth = df['depth'].max()
        depth_dist = df['depth'].value_counts().sort_index().to_dict()
    else:
        avg_depth = 0
        max_depth = 0
        depth_dist = {}

    return {
        'avg_depth': avg_depth,
        'max_depth': max_depth,
        'depth_dist': depth_dist
    }
