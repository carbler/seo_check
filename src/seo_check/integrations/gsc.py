import csv
from typing import Dict, Optional, Any
import urllib.parse

def load_gsc_pages_csv(path: str) -> Dict[str, Dict[str, float]]:
    """Load a Search Console 'Pages' performance export CSV.

    Expected columns (case-insensitive):
    - page/url
    - clicks (optional)
    - impressions (optional)
    - ctr (optional)
    - position (optional)
    """
    metrics: Dict[str, Dict[str, float]] = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f: # utf-8-sig handles BOM
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return {}
            
            field_map = {name.strip().lower(): name for name in reader.fieldnames if name}

            page_col = _first_present(field_map, ["page", "url", "top pages"])
            if not page_col:
                return {}
                
            clicks_col = _first_present(field_map, ["clicks"])
            impressions_col = _first_present(field_map, ["impressions"])
            ctr_col = _first_present(field_map, ["ctr"])
            position_col = _first_present(field_map, ["position", "average position", "avg position"])

            for row in reader:
                raw_page = (row.get(page_col) or "").strip()
                if not raw_page:
                    continue
                
                # Simple normalization to match crawl data
                # Assuming crawl data has full URLs. GSC export usually has full URLs too.
                
                clicks = _to_float(row.get(clicks_col) if clicks_col else None)
                impressions = _to_float(row.get(impressions_col) if impressions_col else None)
                ctr = _to_float(row.get(ctr_col) if ctr_col else None, percent=True)
                position = _to_float(row.get(position_col) if position_col else None)

                metrics[raw_page] = {
                    "clicks": clicks or 0.0,
                    "impressions": impressions or 0.0,
                    "ctr": ctr or 0.0,
                    "position": position or 0.0
                }

    except Exception as e:
        print(f"Error loading GSC CSV: {e}")
        return {}
    
    return metrics

def _first_present(field_map: Dict[str, str], candidates: list[str]) -> Optional[str]:
    for key in candidates:
        col = field_map.get(key)
        if col:
            return col
    return None

def _to_float(value: Optional[str], percent: bool = False) -> Optional[float]:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    s = s.replace(",", "")
    if percent and s.endswith("%"):
        s = s[:-1].strip()
        try:
            return float(s) / 100.0
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None
