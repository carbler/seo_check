import logging
import sys
import pandas as pd

def setup_logging(log_file: str):
    """Sets up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def print_header():
    print("\n" + "="*60)
    print("  SEO ANALYZER - COMPLETE ANALYSIS")
    print("="*60 + "\n")

def print_section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}\n")

def to_list(val):
    """
    Helper to ensure value is a list.
    Handles advertools '@@' separator for multi-value fields.
    """
    if isinstance(val, list):
        return val

    if pd.isna(val) or val == '':
        return []

    # Advertools uses '@@' to join multiple values in a single string column
    val_str = str(val)
    if '@@' in val_str:
        return val_str.split('@@')

    return [val_str]
