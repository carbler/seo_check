import pandas as pd
import numpy as np
import logging
from urllib.parse import urlparse, urljoin
from .config import SEOConfig
from .utils import to_list
import json

# Import new checks
from .checks.http import analyze_http_status
from .checks.meta import analyze_h1_tags, analyze_titles, analyze_meta_desc, analyze_canonical
from .checks.content import analyze_images, analyze_content_quality
from .checks.performance import analyze_performance
from .checks.security import analyze_security
from .checks.links import analyze_links
from .checks.social import analyze_social_tags
from .checks.schema import analyze_schema_presence
from .checks.structure import analyze_url_structure

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
                    if 'count' in entry: extra = f" ({entry['count']})" if 'count' in entry else ""
                    if 'ratio' in entry: extra = f" ({entry['ratio']:.1f}%)" if 'ratio' in entry else ""
                    if 'status' in entry: extra = f" ({entry['status']})" if 'status' in entry else ""

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
                'gsc': gsc_metrics
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
            "Invalid SSL Certificate": "The website's SSL certificate is expired, invalid, or untrusted. This is a major security risk and hurts SEO rankings."
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

        score = max(0.0, score)

        if score >= 90: rating = "EXCELLENT ✅"
        elif score >= 75: rating = "GOOD ✓"
        elif score >= 60: rating = "AVERAGE ⚠️"
        elif score >= 40: rating = "POOR ❌"
        else: rating = "CRITICAL 🔴"

        return score, rating, penalties_log
