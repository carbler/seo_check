import asyncio
import json
import logging
import pandas as pd
import numpy as np
from urllib.parse import urlparse, urljoin

from .config import SEOConfig
from .utils import to_list

# Existing checks
from .checks.http import analyze_http_status
from .checks.meta import analyze_h1_tags, analyze_titles, analyze_meta_desc, analyze_canonical
from .checks.content import analyze_images, analyze_content_quality
from .checks.performance import analyze_performance
from .checks.security import analyze_security
from .checks.links import analyze_links
from .checks.social import analyze_social_tags
from .checks.schema import analyze_schema_presence
from .checks.structure import analyze_url_structure

# New checks
from .checks.indexability import analyze_indexability
from .checks.robots import analyze_robots_txt
from .checks.headers import analyze_response_headers
from .checks.duplicates import analyze_duplicate_content
from .checks.images_broken import analyze_broken_images
from .checks.anchors import analyze_anchor_text
from .checks.mixed_content import analyze_mixed_content
from .checks.url_quality import analyze_url_quality
from .checks.hreflang import analyze_hreflang

class SEOAnalyzer:
    """Analyzes the crawled data to identify SEO issues."""

    def __init__(self, config: SEOConfig):
        self.config = config

    def load_data(self, crawl_file: str) -> pd.DataFrame:
        """Loads crawled data into a DataFrame."""
        try:
            df = pd.read_json(crawl_file, lines=True)
            return df
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            return pd.DataFrame() # Return empty DF instead of None

    def analyze(self, df: pd.DataFrame, gsc_data: dict = {}, lighthouse_data: dict = {}) -> dict:
        """Performs comprehensive analysis on the dataframe."""
        metrics = {}

        # Guard clause for empty dataframe or missing URL column
        if df.empty or 'url' not in df.columns:
            return self._get_empty_metrics()

        # Create a filtered dataframe for semantic checks (only valid 200 OK pages)
        # This prevents 404/500 pages from triggering "Missing H1", "Duplicate Title", etc.
        df_valid = df[df['status'] == 200].copy() if 'status' in df.columns else df

        # Execute Checks
        try:
            # --- Existing checks ---
            metrics['http'] = analyze_http_status(df)
            metrics['h1'] = analyze_h1_tags(df_valid)
            metrics['title'] = analyze_titles(df_valid, self.config)
            metrics['meta'] = analyze_meta_desc(df_valid, self.config)
            metrics['canonical'] = analyze_canonical(df_valid)
            metrics['images'] = analyze_images(df_valid)
            metrics['links'] = analyze_links(df, self.config)
            metrics['security'] = analyze_security(df)
            metrics['performance'] = analyze_performance(df_valid, self.config)
            metrics['social'] = analyze_social_tags(df_valid)
            metrics['schema'] = analyze_schema_presence(df_valid)
            metrics['structure'] = analyze_url_structure(df)
            metrics['content'] = analyze_content_quality(df_valid, self.config)

            # --- New checks (technical — full df) ---
            metrics['indexability'] = analyze_indexability(df)
            metrics['robots'] = analyze_robots_txt(df, self.config.base_url, self.config.user_agent)
            metrics['headers'] = analyze_response_headers(df)
            metrics['hreflang'] = analyze_hreflang(df)

            # --- New checks (semantic — df_valid only) ---
            metrics['duplicates'] = analyze_duplicate_content(df_valid)
            metrics['anchors'] = analyze_anchor_text(df_valid, self.config.base_url)
            metrics['mixed_content'] = analyze_mixed_content(df_valid)
            metrics['url_quality'] = analyze_url_quality(df_valid)

            # --- Async checks ---
            try:
                loop = asyncio.get_running_loop()
                # Already inside an event loop (e.g. FastAPI) — run in thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, analyze_broken_images(df_valid))
                    metrics['broken_images'] = future.result()
            except RuntimeError:
                # No running loop — safe to call asyncio.run directly
                metrics['broken_images'] = asyncio.run(analyze_broken_images(df_valid))

        except Exception as e:
            logging.error(f"Error during analysis checks: {e}")
            # Continue with whatever metrics we gathered or empty ones
            pass

        # Integrations
        metrics['integrations'] = {
            'gsc': gsc_data if gsc_data else {},
            'lighthouse': lighthouse_data if lighthouse_data else {}
        }

        # New Semrush-style categorizations
        metrics['issues'] = self._categorize_issues(metrics)
        metrics['page_details'] = self._get_page_level_analysis(df, metrics, gsc_data)

        return metrics

    def _get_empty_metrics(self):
        """Returns empty structure to prevent crashes."""
        empty_stats = {
            'stats': {}, 'redirects': [], 'broken_links': [], 'server_errors': [],
            'total': 0, 'error_rate_4xx': 0, 'error_rate_5xx': 0
        }
        empty_tags = {
            'no_h1': [], 'multiple_h1': [], 'duplicate_h1': {}, 'total': 0, 'missing_pct': 0,
            'no_title': [], 'short': [], 'long': [], 'duplicates': {}, 'duplicate_pct': 0,
            'no_meta': [], 'no_canonical': [], 'diff': [],
            'missing_alt_details': [], 'total_images': 0, 'missing_alt_count': 0
        }
        # Populate basic structure
        metrics = {
            'http': empty_stats,
            'h1': empty_tags,
            'title': empty_tags,
            'meta': empty_tags,
            'canonical': empty_tags,
            'images': empty_tags,
            'links': {'internal': 0, 'external': 0, 'ratio': 0},
            'security': {'non_https': [], 'secure_pct': 0},
            'performance': {'slow_pages': [], 'avg_time': 0, 'avg_size_bytes': 0, 'huge_pages': []},
            'social': {'og_title_count': 0, 'og_desc_count': 0, 'og_image_count': 0, 'total': 0},
            'schema': {'present_count': 0, 'total': 0},
            'structure': {'avg_depth': 0, 'max_depth': 0, 'depth_dist': {}},
            'content': {'low_word_count': [], 'low_text_ratio': []},
            # New checks
            'indexability': {'noindex_pages': [], 'nofollow_pages': [], 'x_robots_noindex': [], 'noindex_pct': 0},
            'robots': {'robots_txt_url': '', 'robots_fetched': False, 'disallowed_urls': [], 'disallowed_count': 0},
            'headers': {'no_compression_urls': [], 'no_compression_pct': 0, 'bad_cache_urls': [], 'bad_cache_pct': 0},
            'duplicates': {'duplicate_groups': {}, 'duplicate_urls': [], 'duplicate_pct': 0},
            'anchors': {'generic_anchor_links': [], 'generic_pct': 0, 'total_internal_links': 0,
                        'nofollow_internal_links': [], 'nofollow_internal_pct': 0},
            'broken_images': {'broken_images': [], 'broken_count': 0, 'total_images': 0, 'broken_pct': 0},
            'mixed_content': {'mixed_content_pages': [], 'mixed_content_count': 0, 'mixed_content_pct': 0},
            'url_quality': {'urls_with_underscores': [], 'urls_with_uppercase': [], 'urls_with_params': [],
                            'urls_with_special_chars': [], 'deep_urls': [], 'any_issue_pct': 0},
            'hreflang': {'appears_multilingual': False, 'has_hreflang': False, 'hreflang_count': 0, 'missing_hreflang': False},
            'issues': {'errors': [], 'warnings': [], 'notices': []},
            'page_details': {},
            'integrations': {'gsc': {}, 'lighthouse': {}}
        }
        return metrics

    def _categorize_issues(self, metrics):
        """Categorize findings into Errors, Warnings, and Notices."""
        errors = []
        warnings = []
        notices = []
        definitions = self.get_issue_definitions()

        # Helper to standardize items
        def add_issue(list_ref, name, items, priority_boost=False):
            if items:
                final_items = []
                if isinstance(items, dict):
                    for k, v in items.items():
                        final_items.append({'value': k, 'urls': v})
                else:
                    final_items = items

                issue_obj = {
                    'name': name,
                    'count': len(items) if isinstance(items, list) else len(items.keys()),
                    'details': final_items,
                    'description': definitions.get(name, "")
                }
                
                if priority_boost:
                    issue_obj['priority'] = 'high'
                
                list_ref.append(issue_obj)

        # Errors (Critical)
        add_issue(errors, 'Broken Links (4xx)', metrics['http']['broken_links'])
        add_issue(errors, 'Server Errors (5xx)', metrics['http']['server_errors'])
        add_issue(errors, 'Duplicate Titles', metrics['title']['duplicates'])
        add_issue(errors, 'Non-HTTPS Pages', metrics['security']['non_https'])

        if not metrics['security'].get('ssl_valid', True):
            add_issue(errors, 'Invalid SSL Certificate', [metrics['security'].get('ssl_error', 'Verification failed')], priority_boost=True)

        # New: Indexability errors
        if metrics.get('indexability', {}).get('noindex_pages'):
            add_issue(errors, 'Noindex Pages', metrics['indexability']['noindex_pages'], priority_boost=True)
        if metrics.get('indexability', {}).get('x_robots_noindex'):
            add_issue(errors, 'X-Robots-Tag Noindex', metrics['indexability']['x_robots_noindex'])

        # New: Robots.txt disallowed URLs
        if metrics.get('robots', {}).get('disallowed_urls'):
            add_issue(errors, 'Robots.txt Disallowed URLs', metrics['robots']['disallowed_urls'])

        # New: Duplicate content — group format so the UI shows which pages share content
        dup_groups = metrics.get('duplicates', {}).get('duplicate_groups', {})
        if dup_groups:
            dup_pct = metrics.get('duplicates', {}).get('duplicate_pct', 0)
            group_dict = {
                f"Group {i + 1} — {len(urls)} pages with identical content": urls
                for i, (_, urls) in enumerate(dup_groups.items())
            }
            if dup_pct > self.config.duplicate_content_threshold:
                add_issue(errors, 'Duplicate Content', group_dict)

        # New: Mixed content
        if metrics.get('mixed_content', {}).get('mixed_content_pages'):
            mixed_details = [
                {'url': p['url'], 'note': f"{len(p['http_resources'])} HTTP resource(s): {p['http_resources'][0]}{'…' if len(p['http_resources']) > 1 else ''}"}
                for p in metrics['mixed_content']['mixed_content_pages']
            ]
            add_issue(errors, 'Mixed Content (HTTP on HTTPS)', mixed_details)

        # Warnings (Important)
        add_issue(warnings, 'Missing H1 Tags', metrics['h1']['no_h1'])
        add_issue(warnings, 'Duplicate H1 Content', metrics['h1']['duplicate_h1'])
        add_issue(warnings, 'Missing Meta Descriptions', metrics['meta']['no_meta'])
        add_issue(warnings, 'Duplicate Meta Descriptions', metrics['meta']['duplicates'])
        add_issue(warnings, 'Missing Titles', metrics['title']['no_title'])
        add_issue(warnings, 'Titles Too Long', metrics['title']['long'])
        add_issue(warnings, 'Images Missing Alt Text', metrics['images']['missing_alt_details'])
        add_issue(warnings, 'Slow Load Time', metrics['performance']['slow_pages'])
        add_issue(warnings, 'Huge Page Size', metrics['performance']['huge_pages'])
        add_issue(warnings, 'Low Word Count', metrics['content']['low_word_count'])

        # New warnings
        if metrics.get('indexability', {}).get('nofollow_pages'):
            add_issue(warnings, 'Nofollow Pages (meta)', metrics['indexability']['nofollow_pages'])

        if dup_groups and metrics.get('duplicates', {}).get('duplicate_pct', 0) <= self.config.duplicate_content_threshold:
            group_dict = {
                f"Group {i + 1} — {len(urls)} pages with identical content": urls
                for i, (_, urls) in enumerate(dup_groups.items())
            }
            add_issue(warnings, 'Duplicate Content', group_dict)

        if metrics.get('broken_images', {}).get('broken_images'):
            broken_details = [
                {'url': b.get('img_src', ''), 'status': b.get('status', 0)}
                for b in metrics['broken_images']['broken_images']
            ]
            add_issue(warnings, 'Broken Images', broken_details)

        if metrics.get('headers', {}).get('no_compression_pct', 0) > self.config.compression_threshold:
            add_issue(warnings, 'Missing HTTP Compression', metrics['headers']['no_compression_urls'])

        if metrics.get('headers', {}).get('bad_cache_pct', 0) > self.config.cache_threshold:
            add_issue(warnings, 'Poor Cache-Control Headers', metrics['headers']['bad_cache_urls'])

        if metrics.get('anchors', {}).get('nofollow_internal_links'):
            nofollow_details = [
                {'url': a['page_url'], 'note': f"nofollow → {a['link_url']}"}
                for a in metrics['anchors']['nofollow_internal_links']
            ]
            add_issue(warnings, 'Nofollow on Internal Links', nofollow_details)

        if metrics.get('hreflang', {}).get('missing_hreflang'):
            add_issue(warnings, 'Missing Hreflang (Multilingual Site)', ['Site appears multilingual but has no hreflang annotations'])

        # New: Generic anchors (warning if > threshold)
        if metrics.get('anchors', {}).get('generic_pct', 0) > self.config.generic_anchor_threshold:
            generic_details = [
                {'url': a['page_url'], 'note': f"anchor \"{a['anchor']}\" → {a['link_url']}"}
                for a in metrics['anchors']['generic_anchor_links']
            ]
            add_issue(warnings, 'Generic Anchor Text on Internal Links', generic_details)

        # Notices (Info/Optimization)
        add_issue(notices, 'Redirects (3xx)', metrics['http']['redirects'])
        add_issue(notices, 'Titles Too Short', metrics['title']['short'])
        add_issue(notices, 'Meta Desc Too Short', metrics['meta']['short'])
        add_issue(notices, 'Meta Desc Too Long', metrics['meta']['long'])
        add_issue(notices, 'Missing Canonical', metrics['canonical']['no_canonical'])
        add_issue(notices, 'Low Text-HTML Ratio', metrics['content']['low_text_ratio'])

        # New Notices for Social/Schema
        if metrics['schema']['missing_urls']:
            add_issue(notices, 'Missing JSON-LD Schema', metrics['schema']['missing_urls'])

        if metrics['social']['missing_urls']:
            add_issue(notices, 'Missing Open Graph Tags', metrics['social']['missing_urls'])

        # New URL quality notices (surface each sub-category if present)
        uq = metrics.get('url_quality', {})
        if uq.get('urls_with_underscores'):
            add_issue(notices, 'URLs with Underscores', uq['urls_with_underscores'])
        if uq.get('urls_with_uppercase'):
            add_issue(notices, 'URLs with Uppercase Letters', uq['urls_with_uppercase'])
        if uq.get('urls_with_params'):
            add_issue(notices, 'URLs with Excessive Query Parameters', uq['urls_with_params'])
        if uq.get('urls_with_special_chars'):
            add_issue(notices, 'URLs with Encoded Special Characters', uq['urls_with_special_chars'])
        if uq.get('deep_urls'):
            add_issue(notices, 'Deep URL Structure (>4 levels)', uq['deep_urls'])

        # Generic anchors notice (if below warning threshold but still present)
        if 0 < metrics.get('anchors', {}).get('generic_pct', 0) <= self.config.generic_anchor_threshold:
            generic_details = [
                {'url': a['page_url'], 'note': f"anchor \"{a['anchor']}\" → {a['link_url']}"}
                for a in metrics['anchors']['generic_anchor_links']
            ]
            add_issue(notices, 'Generic Anchor Text on Internal Links', generic_details)

        # Hreflang notice for monolingual sites
        if not metrics.get('hreflang', {}).get('appears_multilingual') and \
                not metrics.get('hreflang', {}).get('has_hreflang'):
            add_issue(notices, 'No Hreflang Detected', ['Site appears monolingual — hreflang not required but confirm intentional'])

        return {'errors': errors, 'warnings': warnings, 'notices': notices}

    def _get_page_level_analysis(self, df, metrics, gsc_data=None):
        """Generates a detailed per-page analysis."""
        page_details = {}

        # Pre-process issues mapping: URL -> List of issues
        url_issues = {}

        all_issues = metrics['issues']['errors'] + metrics['issues']['warnings'] + metrics['issues']['notices']

        for issue_group in all_issues:
            name = issue_group['name']
            items = issue_group['details']

            # Case 1: Duplicates [{'value': '...', 'urls': [...]}]
            if items and isinstance(items[0], dict) and 'urls' in items[0]:
                for entry in items:
                    for url in entry['urls']:
                        if url not in url_issues: url_issues[url] = []
                        url_issues[url].append(f"{name}: '{str(entry['value'])[:30]}...'")

            # Case 2: List of objects with 'url' key
            elif items and isinstance(items[0], dict) and 'url' in items[0]:
                for entry in items:
                    url = entry['url']
                    extra = ""
                    if 'note' in entry: extra = f": {entry['note']}"
                    elif 'count' in entry: extra = f" ({entry['count']})"
                    elif 'ratio' in entry: extra = f" ({entry['ratio']:.1f}%)"
                    elif 'status' in entry: extra = f" (HTTP {entry['status']})"

                    if url not in url_issues: url_issues[url] = []
                    url_issues[url].append(f"{name}{extra}")

            # Case 3: List of strings (URLs)
            elif items and isinstance(items[0], str):
                for url in items:
                    if url not in url_issues: url_issues[url] = []
                    url_issues[url].append(name)


        # Iterate all pages
        for _, row in df.iterrows():
            url = row['url']

            title = str(row.get('title', ''))
            meta = str(row.get('meta_desc', ''))
            h1 = str(row.get('h1', ''))

            # Words
            col_name = 'page_body_text' if 'page_body_text' in df.columns else 'body_text'
            words = len(str(row.get(col_name, '')).split())

            # Size
            size_bytes = row.get('size', 0)

            status = "✅ Good"
            issues_list = url_issues.get(url, [])

            if any(i in [e['name'] for e in metrics['issues']['errors']] for i in [x.split(':')[0] for x in issues_list]):
                status = "🔴 Critical"
            elif any(i in [e['name'] for e in metrics['issues']['warnings']] for i in [x.split(':')[0] for x in issues_list]):
                status = "⚠️ Warning"
            elif issues_list:
                status = "🔵 Notice"

            # Social & Schema Data
            # Check for both 'og:image' and 'og_image' styles
            og_image = row.get('og:image', row.get('og_image', ''))
            
            # Fix: Handle NaN/Empty values properly
            if pd.isna(og_image) or str(og_image).lower() == 'nan' or str(og_image).strip() == '':
                og_image = ''
                # Attempt fallback
                img_srcs = to_list(row.get('img_src'))
                if img_srcs and len(img_srcs) > 0:
                    fallback = img_srcs[0]
                    if pd.notna(fallback) and str(fallback).lower() != 'nan':
                        og_image = fallback

            # Ensure absolute URL
            if og_image and not str(og_image).startswith(('http', '//')):
                og_image = urljoin(url, str(og_image))

            og_title = row.get('og:title', row.get('og_title', ''))
            og_desc = row.get('og:description', row.get('og_description', ''))
            
            # Clean nan strings from extracted data
            title = str(title) if pd.notna(title) and str(title).lower() != 'nan' else ''
            meta = str(meta) if pd.notna(meta) and str(meta).lower() != 'nan' else ''
            h1 = str(h1) if pd.notna(h1) and str(h1).lower() != 'nan' else ''
            og_title = str(og_title) if pd.notna(og_title) and str(og_title).lower() != 'nan' else ''
            og_desc = str(og_desc) if pd.notna(og_desc) else ''
            if str(og_desc).lower() == 'nan': og_desc = ''

            # JSON-LD Reconstruction
            jsonld_data = {}
            for col in df.columns:
                if col.startswith('jsonld_'):
                    val = row.get(col)
                    is_valid = False
                    if isinstance(val, (list, pd.Series, np.ndarray)):
                        is_valid = len(val) > 0
                    elif pd.notna(val) and val != '':
                        is_valid = True

                    if is_valid:
                        key = col.replace('jsonld_', '')
                        jsonld_data[key] = val

            if jsonld_data:
                jsonld = json.dumps(jsonld_data, indent=2, default=str)
            else:
                jsonld = ''
            
            # Integration Data
            gsc_metrics = {}
            if gsc_data:
                # Basic exact match for now. In real world, we might need normalizing trailing slashes.
                gsc_metrics = gsc_data.get(url, gsc_data.get(url.rstrip('/'), {}))

            # URL Depth
            depth = row.get('depth', 0)
            
            # HTTPS Check
            is_https = url.startswith('https://')
            ssl_valid = metrics['security']['ssl_valid'] if is_https else False
            ssl_error = metrics['security']['ssl_error'] if is_https and not ssl_valid else ""
            
            if is_https and not ssl_valid:
                if url not in url_issues: url_issues[url] = []
                url_issues[url].append(f"Invalid SSL Certificate: {ssl_error}")

            # H1 Count
            h1s = to_list(row.get('h1', ''))
            h1_count = len([h for h in h1s if str(h).strip()])

            # Title & Meta length
            title_len = len(title)
            meta_len = len(meta)

            # Images
            img_srcs = to_list(row.get('img_src'))
            img_alts = to_list(row.get('img_alt'))
            total_images = len(img_srcs)
            missing_alt = max(0, total_images - len([a for a in img_alts if str(a).strip()]))

            # Technical Details (Server, Error messages)
            server = row.get('resp_headers_Server', '')
            error_msg = row.get('resp_headers_X-Amz-Error-Message', '')
            if not error_msg:
                error_msg = row.get('resp_headers_X-Amz-Error-Code', '')

            # --- New per-page fields ---
            meta_robots_val = str(row.get('meta_robots', '') or '').lower()
            x_robots_val = str(row.get('resp_headers_X-Robots-Tag', '') or '').lower()
            is_noindex = 'noindex' in meta_robots_val or 'noindex' in x_robots_val
            is_page_nofollow = 'nofollow' in meta_robots_val
            is_x_robots_noindex = 'noindex' in x_robots_val
            robots_disallowed = url in metrics.get('robots', {}).get('disallowed_urls', [])

            has_compression = url not in metrics.get('headers', {}).get('no_compression_urls', [])
            has_cache_control = url not in metrics.get('headers', {}).get('bad_cache_urls', [])

            dup_urls = metrics.get('duplicates', {}).get('duplicate_urls', [])
            dup_groups = metrics.get('duplicates', {}).get('duplicate_groups', {})
            has_duplicate_content = url in dup_urls
            duplicate_hash = next((h for h, urls in dup_groups.items() if url in urls), None)
            # URLs that share the same content as this page (excluding self)
            duplicate_with = [u for u in dup_groups.get(duplicate_hash, []) if u != url] if duplicate_hash else []

            broken_img_srcs = {b.get('img_src', '') for b in metrics.get('broken_images', {}).get('broken_images', [])}
            page_img_srcs = set(to_list(row.get('img_src')))
            broken_images_count = len(page_img_srcs & broken_img_srcs)

            mixed_urls = {p['url'] for p in metrics.get('mixed_content', {}).get('mixed_content_pages', [])}
            has_mixed_content = url in mixed_urls

            page_details[url] = {
                'status': status,
                'title': title,
                'title_len': title_len,
                'h1': h1,
                'h1_count': h1_count,
                'words': words,
                'size': size_bytes,
                'depth': int(depth),
                'is_https': is_https,
                'ssl_valid': ssl_valid,
                'ssl_error': ssl_error,
                'meta_len': meta_len,
                'total_images': total_images,
                'missing_alt': missing_alt,
                'server': str(server) if pd.notna(server) else '',
                'error_msg': str(error_msg) if pd.notna(error_msg) else '',
                'issues': issues_list,
                'meta_desc': meta,
                'canonical': str(row.get('canonical', '')),
                'status_code': row.get('status', 0),
                'load_time': row.get('download_latency', 0),
                'og_title': str(og_title) if pd.notna(og_title) else '',
                'og_desc': str(og_desc) if pd.notna(og_desc) else '',
                'og_image': str(og_image) if pd.notna(og_image) else '',
                'jsonld': jsonld,
                'has_schema': jsonld != '',
                'gsc': gsc_metrics,
                # New fields
                'noindex': is_noindex,
                'x_robots_noindex': is_x_robots_noindex,
                'page_nofollow': is_page_nofollow,
                'robots_disallowed': robots_disallowed,
                'has_compression': has_compression,
                'has_cache_control': has_cache_control,
                'has_duplicate_content': has_duplicate_content,
                'duplicate_with': duplicate_with,
                'broken_images_count': broken_images_count,
                'has_mixed_content': has_mixed_content,
            }

        return page_details

    def get_issue_definitions(self):
        """Returns a glossary of issue definitions."""
        return {
            "Broken Links (4xx)": "Links pointing to pages that do not exist (404 errors). User experience and crawlability are negatively affected.",
            "Server Errors (5xx)": "The server failed to fulfill a valid request. Indicates server instability.",
            "Duplicate Titles": "Multiple pages share the same Title Tag. Search engines may not know which page to rank.",
            "Non-HTTPS Pages": "Pages served over insecure HTTP connection. Google prioritizes HTTPS.",
            "Missing H1 Tags": "Pages without a main Heading 1. H1 is crucial for understanding page topic.",
            "Duplicate H1 Content": "Multiple pages share the same H1. Can indicate duplicate content.",
            "Missing Meta Descriptions": "No summary provided for search results. Lower CTR potential.",
            "Duplicate Meta Descriptions": "Multiple pages use the same description. Bad for uniqueness.",
            "Missing Titles": "Page has no <title> tag. Critical for SEO ranking.",
            "Titles Too Long": f"Title exceeds {self.config.title_max_length} chars. Will be truncated in SERPs.",
            "Images Missing Alt Text": "Images without textual description. Bad for accessibility and Image SEO.",
            "Slow Load Time": f"Page took longer than {self.config.slow_page_threshold}s to respond.",
            "Low Word Count": f"Page has less than {self.config.min_word_count} words. May be considered 'Thin Content'.",
            "Redirects (3xx)": "Page redirects to another URL. Too many redirects waste crawl budget.",
            "Titles Too Short": f"Title is less than {self.config.title_min_length} chars. May not be descriptive enough.",
            "Meta Desc Too Short": "Description is too brief to entice clicks.",
            "Meta Desc Too Long": "Description will be cut off in search results.",
            "Missing Canonical": "No canonical tag found. Search engines may struggle with duplicate versions.",
            "Low Text-HTML Ratio": "Page code is bloated compared to visible text. Can indicate code efficiency issues.",
            "Huge Page Size": f"Page size exceeds {self.config.max_page_size_bytes / 1024 / 1024:.1f} MB. Heavy pages hurt mobile performance.",
            "Missing JSON-LD Schema": "No structured data found. Rich snippets in search results may not be available.",
            "Missing Open Graph Tags": "Open Graph tags are missing. Social media shares may not display correctly.",
            "Invalid SSL Certificate": "The website's SSL certificate is expired, invalid, or untrusted. This is a major security risk and hurts SEO rankings.",
            # New issue definitions
            "Noindex Pages": "Pages with 'noindex' directive in meta_robots. Google will not index these pages. Verify they are intentionally excluded.",
            "X-Robots-Tag Noindex": "Pages with 'noindex' in the X-Robots-Tag HTTP header. Google will not index these pages.",
            "Nofollow Pages (meta)": "Pages with 'nofollow' in meta_robots. Google will not follow links from these pages, wasting internal PageRank.",
            "Robots.txt Disallowed URLs": "Crawled URLs that are blocked by robots.txt. Googlebot cannot access these pages; verify the disallow rules are intentional.",
            "Duplicate Content": "Pages sharing identical body text content. Duplicate content dilutes ranking authority and confuses Google about which URL to rank.",
            "Mixed Content (HTTP on HTTPS)": "HTTPS pages loading resources (images, links) over HTTP. Chrome blocks mixed content, causing page errors and security warnings.",
            "Broken Images": "Image URLs returning 4xx/5xx status codes. Broken images damage UX and signal poor site maintenance to crawlers.",
            "Missing HTTP Compression": f"HTML pages served without gzip or Brotli compression (>{self.config.compression_threshold}% of pages). Compression significantly reduces page size and improves Core Web Vitals.",
            "Poor Cache-Control Headers": f"Pages missing or using restrictive Cache-Control headers (>{self.config.cache_threshold}% of pages). Proper caching reduces load times for repeat visitors.",
            "Nofollow on Internal Links": "Internal links with rel='nofollow' waste PageRank by preventing flow between your own pages.",
            "Missing Hreflang (Multilingual Site)": "The site appears to target multiple languages based on URL patterns, but no hreflang annotations were found. This causes Google to serve the wrong language to users.",
            "Generic Anchor Text on Internal Links": "Internal links using generic anchors like 'click here', 'read more', etc. Descriptive anchor text passes more semantic signal to search engines.",
            "URLs with Underscores": "URLs containing underscores in the path. Google treats underscores as word joiners, not separators. Use hyphens instead.",
            "URLs with Uppercase Letters": "URLs with uppercase letters in the path. This can cause duplicate content issues if the same page is accessible via both cases.",
            "URLs with Excessive Query Parameters": "URLs with more than 2 query parameters. Complex parameter URLs can confuse crawlers and dilute link equity.",
            "URLs with Encoded Special Characters": "URLs containing percent-encoded special characters in the path (e.g. %20, %3A). Clean, readable URLs are preferred.",
            "Deep URL Structure (>4 levels)": "URLs with more than 4 path levels. Deep URLs signal lower importance to search engines and receive less PageRank.",
            "No Hreflang Detected": "No hreflang annotations found. For monolingual sites this is expected, but confirm there are no international versions.",
        }


class SEOScorer:
    """Calculates the SEO score based on analysis metrics."""

    def __init__(self, config: SEOConfig):
        self.config = config

    def calculate(self, metrics: dict):
        score = 100.0
        penalties_log = []
        http_metrics = metrics['http']

        # 1. Broken Links (Critical)
        broken_rate = http_metrics['error_rate_4xx']
        if broken_rate > self.config.critical_threshold:
            penalty = self.config.penalty_broken_link
            score -= penalty
            penalties_log.append(f"Broken Links (> {self.config.critical_threshold}%): -{penalty}")
        elif broken_rate > 0:
            # Proportional penalty if below threshold but present
            penalty = (broken_rate / self.config.critical_threshold) * self.config.penalty_broken_link
            penalty = min(penalty, self.config.penalty_broken_link)
            score -= penalty
            penalties_log.append(f"Broken Links ({broken_rate:.1f}%): -{penalty:.1f}")

        # Note: Content penalties are now based on valid pages (status 200) only,
        # thanks to filtering in SEOAnalyzer.analyze().

        # 2. H1
        h1_miss = metrics['h1']['missing_pct']
        if h1_miss > self.config.warning_threshold:
            penalty = self.config.penalty_missing_h1
            score -= penalty
            penalties_log.append(f"Missing H1 (> {self.config.warning_threshold}%): -{penalty:.1f}")
        elif h1_miss > 0:
            penalty = (h1_miss / self.config.warning_threshold) * self.config.penalty_missing_h1
            penalty = min(penalty, self.config.penalty_missing_h1)
            score -= penalty
            penalties_log.append(f"Missing H1 ({h1_miss:.1f}%): -{penalty:.1f}")

        # 3. Titles
        title_miss = metrics['title']['missing_pct']
        if title_miss > 0:
            penalty = (title_miss / 100.0) * self.config.penalty_missing_title
            penalty = max(penalty, 2.0) 
            score -= penalty
            penalties_log.append(f"Missing Titles ({title_miss:.1f}%): -{penalty:.1f}")

        dup_title = metrics['title']['duplicate_pct']
        if dup_title > self.config.warning_threshold:
            penalty = self.config.penalty_duplicate_title
            score -= penalty
            penalties_log.append(f"Duplicate Titles (> {self.config.warning_threshold}%): -{penalty}")

        # 4. Meta Desc
        meta_miss = metrics['meta']['missing_pct']
        if meta_miss > self.config.warning_threshold:
            penalty = self.config.penalty_missing_meta
            score -= penalty
            penalties_log.append(f"Missing Meta Desc (> {self.config.warning_threshold}%): -{penalty:.1f}")
        elif meta_miss > 0:
            penalty = (meta_miss / self.config.warning_threshold) * (self.config.penalty_missing_meta / 2.0)
            score -= penalty
            penalties_log.append(f"Missing Meta Desc ({meta_miss:.1f}%): -{penalty:.1f}")

        # 5. Images
        img_miss = metrics['images']['missing_pct']
        if img_miss > self.config.warning_threshold:
            penalty = self.config.penalty_missing_alt
            score -= penalty
            penalties_log.append(f"Missing Alt Text (> {self.config.warning_threshold}%): -{penalty}")

        # 6. Security (HTTPS & SSL)
        non_https_pct = (len(metrics['security']['non_https']) / http_metrics['total'] * 100) if http_metrics['total'] > 0 else 0
        if non_https_pct > 0:
            penalty = (non_https_pct / 100.0) * self.config.penalty_insecure_http
            score -= penalty
            penalties_log.append(f"Insecure Pages (HTTP): -{penalty:.1f}")
        
        if not metrics['security'].get('ssl_valid', True):
            penalty = self.config.penalty_invalid_ssl
            score -= penalty
            penalties_log.append(f"Invalid SSL Certificate: -{penalty}")

        # 7. Huge Pages
        huge_page_count = len(metrics['performance']['huge_pages'])
        if huge_page_count > 0:
            total_pages = http_metrics['total']
            huge_pct = (huge_page_count / total_pages * 100) if total_pages > 0 else 0
            penalty = (huge_pct / 100.0) * self.config.penalty_huge_page
            penalty = max(penalty, 2.0) # Min penalty if any huge
            score -= penalty
            penalties_log.append(f"Huge Pages (> 2MB): -{penalty:.1f}")

        # 8. Indexability
        noindex_pct = metrics.get('indexability', {}).get('noindex_pct', 0)
        if noindex_pct > self.config.noindex_threshold:
            penalty = self.config.penalty_noindex_page
            score -= penalty
            penalties_log.append(f"Noindex Pages (>{self.config.noindex_threshold}%): -{penalty}")
        elif noindex_pct > 0:
            penalty = (noindex_pct / self.config.noindex_threshold) * self.config.penalty_noindex_page
            score -= penalty
            penalties_log.append(f"Noindex Pages ({noindex_pct:.1f}%): -{penalty:.1f}")

        nofollow_pages = metrics.get('indexability', {}).get('nofollow_pages', [])
        if nofollow_pages:
            total_pages = http_metrics['total'] or 1
            nofollow_pct = len(nofollow_pages) / total_pages * 100
            penalty = min((nofollow_pct / 100.0) * self.config.penalty_page_nofollow, self.config.penalty_page_nofollow)
            score -= penalty
            penalties_log.append(f"Nofollow Pages ({nofollow_pct:.1f}%): -{penalty:.1f}")

        # 9. Robots.txt disallowed URLs
        disallowed_count = metrics.get('robots', {}).get('disallowed_count', 0)
        if disallowed_count > 0:
            total_pages = http_metrics['total'] or 1
            disallowed_pct = disallowed_count / total_pages * 100
            if disallowed_pct > self.config.critical_threshold:
                penalty = self.config.penalty_robots_disallow
            else:
                penalty = max(5.0, (disallowed_pct / self.config.critical_threshold) * self.config.penalty_robots_disallow)
            score -= penalty
            penalties_log.append(f"Robots.txt Disallowed ({disallowed_count} URLs): -{penalty:.1f}")

        # 10. Response Headers
        no_compression_pct = metrics.get('headers', {}).get('no_compression_pct', 0)
        if no_compression_pct > self.config.compression_threshold:
            penalty = self.config.penalty_no_compression
            score -= penalty
            penalties_log.append(f"No HTTP Compression (>{self.config.compression_threshold}%): -{penalty}")
        elif no_compression_pct > 0:
            penalty = (no_compression_pct / self.config.compression_threshold) * self.config.penalty_no_compression
            score -= penalty
            penalties_log.append(f"No HTTP Compression ({no_compression_pct:.1f}%): -{penalty:.1f}")

        bad_cache_pct = metrics.get('headers', {}).get('bad_cache_pct', 0)
        if bad_cache_pct > self.config.cache_threshold:
            penalty = self.config.penalty_bad_cache
            score -= penalty
            penalties_log.append(f"Poor Cache-Control (>{self.config.cache_threshold}%): -{penalty}")
        elif bad_cache_pct > 0:
            penalty = (bad_cache_pct / self.config.cache_threshold) * self.config.penalty_bad_cache
            score -= penalty
            penalties_log.append(f"Poor Cache-Control ({bad_cache_pct:.1f}%): -{penalty:.1f}")

        # 11. Duplicate Content
        dup_pct = metrics.get('duplicates', {}).get('duplicate_pct', 0)
        if dup_pct > self.config.duplicate_content_threshold:
            penalty = self.config.penalty_duplicate_content
            score -= penalty
            penalties_log.append(f"Duplicate Content (>{self.config.duplicate_content_threshold}%): -{penalty}")
        elif dup_pct > 0:
            penalty = (dup_pct / self.config.duplicate_content_threshold) * self.config.penalty_duplicate_content
            score -= penalty
            penalties_log.append(f"Duplicate Content ({dup_pct:.1f}%): -{penalty:.1f}")

        # 12. Broken Images
        broken_img_pct = metrics.get('broken_images', {}).get('broken_pct', 0)
        if broken_img_pct > self.config.broken_image_threshold:
            penalty = self.config.penalty_broken_image
            score -= penalty
            penalties_log.append(f"Broken Images (>{self.config.broken_image_threshold}%): -{penalty}")
        elif broken_img_pct > 0:
            penalty = (broken_img_pct / self.config.broken_image_threshold) * self.config.penalty_broken_image
            score -= penalty
            penalties_log.append(f"Broken Images ({broken_img_pct:.1f}%): -{penalty:.1f}")

        # 13. Mixed Content
        mixed_content_count = metrics.get('mixed_content', {}).get('mixed_content_count', 0)
        if mixed_content_count > 0:
            total_pages = http_metrics['total'] or 1
            mixed_pct = mixed_content_count / total_pages * 100
            penalty = min((mixed_pct / 100.0) * self.config.penalty_mixed_content, self.config.penalty_mixed_content)
            penalty = max(penalty, 2.0)
            score -= penalty
            penalties_log.append(f"Mixed Content ({mixed_content_count} pages): -{penalty:.1f}")

        # 14. URL Quality (only if > threshold % of pages affected)
        url_quality_pct = metrics.get('url_quality', {}).get('any_issue_pct', 0)
        if url_quality_pct > self.config.url_quality_threshold:
            penalty = self.config.penalty_url_quality
            score -= penalty
            penalties_log.append(f"URL Quality Issues (>{self.config.url_quality_threshold}%): -{penalty}")

        # 15. Anchor text — generic anchors
        generic_anchor_pct = metrics.get('anchors', {}).get('generic_pct', 0)
        if generic_anchor_pct > self.config.generic_anchor_threshold:
            penalty = self.config.penalty_generic_anchors
            score -= penalty
            penalties_log.append(f"Generic Anchor Text (>{self.config.generic_anchor_threshold}%): -{penalty}")

        # 16. Nofollow on internal links
        nofollow_internal_pct = metrics.get('anchors', {}).get('nofollow_internal_pct', 0)
        if nofollow_internal_pct > 0:
            total_internal = metrics.get('anchors', {}).get('total_internal_links', 1) or 1
            nofollow_count = len(metrics.get('anchors', {}).get('nofollow_internal_links', []))
            penalty = min((nofollow_internal_pct / 100.0) * self.config.penalty_nofollow_internal, self.config.penalty_nofollow_internal)
            score -= penalty
            penalties_log.append(f"Nofollow Internal Links ({nofollow_count}): -{penalty:.1f}")

        score = max(0.0, score)

        if score >= 90: rating = "EXCELLENT ✅"
        elif score >= 75: rating = "GOOD ✓"
        elif score >= 60: rating = "AVERAGE ⚠️"
        elif score >= 40: rating = "POOR ❌"
        else: rating = "CRITICAL 🔴"

        return score, rating, penalties_log
