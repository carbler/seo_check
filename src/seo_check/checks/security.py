from typing import Dict, Any, List
import pandas as pd
import socket
import ssl
from urllib.parse import urlparse
import logging

try:
    import certifi
    HAS_CERTIFI = True
except ImportError:
    HAS_CERTIFI = False

def analyze_security(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyzes HTTPS usage and certificate validity."""
    non_https = df[~df['url'].str.startswith('https://')]['url'].tolist()
    
    if df.empty:
        return {'non_https': [], 'secure_pct': 0, 'ssl_valid': False, 'ssl_error': 'No data'}

    sample_url = df['url'].iloc[0]
    hostname = urlparse(sample_url).netloc
    
    ssl_valid = True
    ssl_error = ""

    if sample_url.startswith('https://'):
        try:
            # Use certifi if available for better compatibility on macOS/Windows
            if HAS_CERTIFI:
                context = ssl.create_default_context(cafile=certifi.where())
            else:
                context = ssl.create_default_context()
            
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    ssock.getpeercert()
        except ssl.SSLCertVerificationError as e:
            ssl_valid = False
            ssl_error = f"Certificate Verification Failed: {e.reason}"
            logging.error(f"SSL Verification failed for {hostname}: {e}")
        except Exception as e:
            # For other network errors, don't necessarily mark SSL as invalid if it's just a timeout
            ssl_valid = False
            ssl_error = str(e)
            logging.error(f"SSL Check error for {hostname}: {e}")

    return {
        'non_https': non_https,
        'secure_pct': ((len(df) - len(non_https)) / len(df) * 100) if len(df) > 0 else 0,
        'ssl_valid': ssl_valid,
        'ssl_error': ssl_error
    }
