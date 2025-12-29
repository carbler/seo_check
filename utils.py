import logging
import sys
import pandas as pd
from config import LOG_FILE

def setup_logging():
    """Sets up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def print_header():
    print("\n" + "="*60)
    print("  TUWORKER.COM - COMPLETE SEO ANALYSIS")
    print("="*60 + "\n")

def print_section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}\n")

def to_list(val):
    """Helper to ensure value is a list."""
    if isinstance(val, list):
        return val
    if pd.isna(val) or val == '':
        return []
    # If it's a string that looks like a list representation (rare in JL but possible)
    # or just a single string
    return [str(val)]
