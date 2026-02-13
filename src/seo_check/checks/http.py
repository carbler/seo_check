from typing import Dict, Any
import pandas as pd

def analyze_http_status(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes HTTP status codes, redirects, and broken links."""
    total = len(df)
    if 'status' not in df.columns:
            return {
                'stats': {},
                'redirects': [],
                'broken_links': [],
                'server_errors': [],
                'total': total,
                'error_rate_4xx': 0,
                'error_rate_5xx': 0
            }

    stats = df['status'].value_counts()

    redirects_3xx = df[df['status'].between(300, 399)]
    errors_4xx = df[df['status'].between(400, 499)]
    errors_5xx = df[df['status'].between(500, 599)]

    redirect_list = redirects_3xx[['url', 'status']].to_dict('records') if not redirects_3xx.empty else []
    broken_links = errors_4xx[['url', 'status']].to_dict('records') if not errors_4xx.empty else []
    server_errors = errors_5xx[['url', 'status']].to_dict('records') if not errors_5xx.empty else []

    return {
        'stats': stats.to_dict(),
        'redirects': redirect_list,
        'broken_links': broken_links,
        'server_errors': server_errors,
        'total': total,
        'error_rate_4xx': (len(errors_4xx) / total) * 100 if total > 0 else 0,
        'error_rate_5xx': (len(errors_5xx) / total) * 100 if total > 0 else 0
    }
