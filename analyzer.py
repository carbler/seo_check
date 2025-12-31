import pandas as pd
import logging
from urllib.parse import urlparse
from utils import to_list
from config import SEOConfig

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
            return None

    def analyze(self, df: pd.DataFrame) -> dict:
        """Performs comprehensive analysis on the dataframe."""
        metrics = {}

        # Guard clause for empty dataframe or missing URL column
        if df.empty or 'url' not in df.columns:
            return self._get_empty_metrics()

        metrics['http'] = self._analyze_http_status(df)
        metrics['h1'] = self._analyze_h1_tags(df)
        metrics['title'] = self._analyze_titles(df)
        metrics['meta'] = self._analyze_meta_desc(df)
        metrics['canonical'] = self._analyze_canonical(df)
        metrics['images'] = self._analyze_images(df)
        metrics['links'] = self._analyze_links(df)
        metrics['security'] = self._analyze_security(df)
        metrics['others'] = self._analyze_others(df)
        metrics['content'] = self._analyze_content(df)

        # New Semrush-style categorizations
        metrics['issues'] = self._categorize_issues(metrics)
        metrics['page_details'] = self._get_page_level_analysis(df, metrics)

        return metrics

    def _analyze_http_status(self, df):
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

        redirect_list = redirects_3xx[['url', 'status']].to_dict('records')
        broken_links = errors_4xx[['url', 'status']].to_dict('records')
        server_errors = errors_5xx[['url', 'status']].to_dict('records')

        return {
            'stats': stats.to_dict(),
            'redirects': redirect_list,
            'broken_links': broken_links,
            'server_errors': server_errors,
            'total': total,
            'error_rate_4xx': (len(errors_4xx) / total) * 100 if total > 0 else 0,
            'error_rate_5xx': (len(errors_5xx) / total) * 100 if total > 0 else 0
        }

    def _analyze_h1_tags(self, df):
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

    def _analyze_titles(self, df):
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

        short_titles = df[df['title'].str.len() < self.config.title_min_length]['url'].tolist()
        long_titles = df[df['title'].str.len() > self.config.title_max_length]['url'].tolist()

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

    def _analyze_meta_desc(self, df):
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

        short_meta = df[df[col_name].str.len() < self.config.meta_desc_min_length]['url'].tolist()
        long_meta = df[df[col_name].str.len() > self.config.meta_desc_max_length]['url'].tolist()

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

    def _analyze_canonical(self, df):
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

    def _analyze_images(self, df):
        if 'img_alt' not in df.columns:
            return {
                'missing_alt_details': [],
                'total_images': 0,
                'missing_alt_count': 0,
                'missing_pct': 0
            }

        total_imgs = 0
        missing_alt_count = 0
        missing_alt_urls = []

        for index, row in df.iterrows():
            srcs = to_list(row.get('img_src'))
            alts = to_list(row.get('img_alt'))

            page_imgs = len(srcs)
            if page_imgs == 0: continue

            total_imgs += page_imgs

            empty_in_list = len([x for x in alts if not x or not x.strip()])
            diff = max(0, len(srcs) - len(alts))

            page_missing = empty_in_list + diff

            if page_missing > 0:
                missing_alt_count += page_missing
                missing_alt_urls.append({'url': row['url'], 'count': page_missing})

        return {
            'missing_alt_details': missing_alt_urls,
            'total_images': total_imgs,
            'missing_alt_count': missing_alt_count,
            'missing_pct': (missing_alt_count / total_imgs * 100) if total_imgs > 0 else 0
        }

    def _analyze_links(self, df):
        total_internal = 0
        total_external = 0

        if 'links_url' not in df.columns:
            return {'internal': 0, 'external': 0, 'ratio': 0}

        # Determine target domain from config to check internal/external
        target_domain = urlparse(self.config.base_url).netloc
        # If config is just "example.com" without scheme, urlparse might put it in path.
        if not target_domain and self.config.base_url:
             if not self.config.base_url.startswith(('http://', 'https://')):
                 target_domain = self.config.base_url.split('/')[0]
             else:
                 target_domain = self.config.base_url

        for links in df['links_url']:
            links = to_list(links)
            for l in links:
                if not isinstance(l, str): continue

                if target_domain and target_domain in l:
                    total_internal += 1
                elif l.startswith('http'):
                    total_external += 1
                elif l.startswith('/') or l.startswith('#'):
                    # Relative links are internal
                    total_internal += 1

        ratio = (total_internal / total_external) if total_external > 0 else total_internal

        return {
            'internal': total_internal,
            'external': total_external,
            'ratio': ratio
        }

    def _analyze_security(self, df):
        non_https = df[~df['url'].str.startswith('https://')]['url'].tolist()

        return {
            'non_https': non_https,
            'secure_pct': ((len(df) - len(non_https)) / len(df) * 100) if len(df) > 0 else 0
        }

    def _analyze_others(self, df):
        results = {}
        total = len(df)

        results['og'] = {
            'title': df['og_title'].notna().sum() if 'og_title' in df.columns else 0,
            'desc': df['og_description'].notna().sum() if 'og_description' in df.columns else 0,
            'image': df['og_image'].notna().sum() if 'og_image' in df.columns else 0,
            'total': total
        }

        results['schema'] = {
            'present': df['jsonld'].notna().sum() if 'jsonld' in df.columns else 0,
            'total': total
        }

        if 'download_latency' in df.columns:
            slow_pages = df[df['download_latency'] > self.config.slow_page_threshold]['url'].tolist()
            avg_time = df['download_latency'].mean()
        else:
            slow_pages = []
            avg_time = 0

        # New: Size Analysis
        huge_pages = []
        avg_size = 0
        if 'size' in df.columns:
            avg_size = df['size'].mean()
            huge_pages = df[df['size'] > self.config.max_page_size_bytes]['url'].tolist()

        results['performance'] = {
            'slow_pages': slow_pages,
            'avg_time': avg_time,
            'avg_size_bytes': avg_size,
            'huge_pages': huge_pages
        }

        if 'url' in df.columns:
            df['depth'] = df['url'].astype(str).apply(lambda x: x.count('/'))
            avg_depth = df['depth'].mean()
            max_depth = df['depth'].max()
            depth_dist = df['depth'].value_counts().sort_index().to_dict()
        else:
            avg_depth = 0
            max_depth = 0
            depth_dist = {}

        results['urls'] = {
            'avg_depth': avg_depth,
            'max_depth': max_depth,
            'depth_dist': depth_dist
        }

        return results

    def _analyze_content(self, df):
        """Analyzes content quality (Word count, Text Ratio)."""
        low_word_count = []
        low_text_ratio = []

        # Check for custom extracted 'page_body_text' or standard 'body_text'
        col_name = 'page_body_text' if 'page_body_text' in df.columns else 'body_text'

        if col_name in df.columns:
            for _, row in df.iterrows():
                # Advertools puts extracted text in one string column if using selectors.
                text_content = str(row.get(col_name, ''))

                # Word Count
                words = len(text_content.split())
                if words < self.config.min_word_count:
                    low_word_count.append({'url': row['url'], 'count': words})

                # Ratio
                # Approximating HTML size from 'size' column (bytes) vs text length
                html_size = row.get('size', 0)
                text_size = len(text_content)

                if html_size > 0:
                    ratio = (text_size / html_size) * 100
                    if ratio < self.config.text_ratio_threshold:
                        low_text_ratio.append({'url': row['url'], 'ratio': ratio})

        return {
            'low_word_count': low_word_count,
            'low_text_ratio': low_text_ratio
        }

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
            'others': {
                'og': {'title': 0, 'desc': 0, 'image': 0, 'total': 0},
                'schema': {'present': 0, 'total': 0},
                'performance': {'slow_pages': [], 'avg_time': 0, 'avg_size_bytes': 0, 'huge_pages': []},
                'urls': {'avg_depth': 0, 'max_depth': 0, 'depth_dist': {}}
            },
            'content': {'low_word_count': [], 'low_text_ratio': []},
            'issues': {'errors': [], 'warnings': [], 'notices': []},
            'page_details': {}
        }
        return metrics

    def _categorize_issues(self, metrics):
        """Categorize findings into Errors, Warnings, and Notices."""
        errors = []
        warnings = []
        notices = []
        definitions = self.get_issue_definitions()

        # Helper to standardize items
        def add_issue(list_ref, name, items):
            if items:
                # Convert Dict items (Duplicates) to list of objects
                # dict format: {'Title': ['url1', 'url2']}
                # target format: [{'value': 'Title', 'urls': ['url1', 'url2']}]
                final_items = []
                if isinstance(items, dict):
                    for k, v in items.items():
                        final_items.append({'value': k, 'urls': v})
                else:
                    final_items = items

                list_ref.append({
                    'name': name,
                    'count': len(items) if isinstance(items, list) else len(items.keys()),
                    'details': final_items, # Renamed from 'items' to 'details'
                    'description': definitions.get(name, "")
                })

        # Errors (Critical)
        add_issue(errors, 'Broken Links (4xx)', metrics['http']['broken_links'])
        add_issue(errors, 'Server Errors (5xx)', metrics['http']['server_errors'])
        add_issue(errors, 'Duplicate Titles', metrics['title']['duplicates'])
        add_issue(errors, 'Non-HTTPS Pages', metrics['security']['non_https'])

        # Warnings (Important)
        add_issue(warnings, 'Missing H1 Tags', metrics['h1']['no_h1'])
        add_issue(warnings, 'Duplicate H1 Content', metrics['h1']['duplicate_h1'])
        add_issue(warnings, 'Missing Meta Descriptions', metrics['meta']['no_meta'])
        add_issue(warnings, 'Duplicate Meta Descriptions', metrics['meta']['duplicates'])
        add_issue(warnings, 'Missing Titles', metrics['title']['no_title'])
        add_issue(warnings, 'Titles Too Long', metrics['title']['long'])
        add_issue(warnings, 'Images Missing Alt Text', metrics['images']['missing_alt_details'])
        add_issue(warnings, 'Slow Load Time', metrics['others']['performance']['slow_pages'])
        add_issue(warnings, 'Huge Page Size', metrics['others']['performance']['huge_pages'])
        add_issue(warnings, 'Low Word Count', metrics['content']['low_word_count'])

        # Notices (Info/Optimization)
        add_issue(notices, 'Redirects (3xx)', metrics['http']['redirects'])
        add_issue(notices, 'Titles Too Short', metrics['title']['short'])
        add_issue(notices, 'Meta Desc Too Short', metrics['meta']['short'])
        add_issue(notices, 'Meta Desc Too Long', metrics['meta']['long'])
        add_issue(notices, 'Missing Canonical', metrics['canonical']['no_canonical'])
        add_issue(notices, 'Low Text-HTML Ratio', metrics['content']['low_text_ratio'])

        return {'errors': errors, 'warnings': warnings, 'notices': notices}

    def _get_page_level_analysis(self, df, metrics):
        """Generates a detailed per-page analysis."""
        page_details = {}

        # Pre-process issues mapping: URL -> List of issues
        url_issues = {}

        all_issues = metrics['issues']['errors'] + metrics['issues']['warnings'] + metrics['issues']['notices']

        for issue_group in all_issues:
            name = issue_group['name']
            items = issue_group['details'] # Renamed from 'items' to 'details'

            # Items are now standardized lists of objects or strings
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
                    if 'count' in entry: extra = f" ({entry['count']})"
                    if 'ratio' in entry: extra = f" ({entry['ratio']:.1f}%)"
                    if 'status' in entry: extra = f" ({entry['status']})"

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
            title = str(row.get('title', ''))[:50]
            meta = str(row.get('meta_desc', ''))[:50]
            h1 = str(row.get('h1', ''))[:50]

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
            og_title = row.get('og_title', '')
            og_desc = row.get('og_description', '')
            og_image = row.get('og_image', '')
            jsonld = row.get('jsonld', '')

            page_details[url] = {
                'status': status,
                'title': title,
                'h1': h1,
                'words': words,
                'size': size_bytes,
                'issues': issues_list,
                'meta_desc': meta,
                'canonical': str(row.get('canonical', '')),
                'status_code': row.get('status', 0),
                'load_time': row.get('download_latency', 0),
                'og_title': str(og_title) if pd.notna(og_title) else '',
                'og_desc': str(og_desc) if pd.notna(og_desc) else '',
                'og_image': str(og_image) if pd.notna(og_image) else '',
                'jsonld': str(jsonld) if pd.notna(jsonld) else ''
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
            "Huge Page Size": f"Page size exceeds {self.config.max_page_size_bytes / 1024 / 1024:.1f} MB. Heavy pages hurt mobile performance."
        }


class SEOScorer:
    """Calculates the SEO score based on analysis metrics."""

    def __init__(self, config: SEOConfig):
        self.config = config

    def calculate(self, metrics: dict):
        score = 100
        penalties_log = []

        # 1. Broken Links (Critical)
        broken_rate = metrics['http']['error_rate_4xx']
        if broken_rate > self.config.critical_threshold:
            penalty = 25
            score -= penalty
            penalties_log.append(f"Broken Links (> {self.config.critical_threshold}%): -{penalty}")
        elif broken_rate > 0:
            penalty = broken_rate * 2
            penalty = min(penalty, 25)
            score -= penalty
            penalties_log.append(f"Broken Links ({broken_rate:.1f}%): -{penalty:.1f}")

        # 2. H1
        h1_miss = metrics['h1']['missing_pct']
        if h1_miss > self.config.warning_threshold:
            penalty = 15
            score -= penalty
            penalties_log.append(f"Missing H1 (> {self.config.warning_threshold}%): -{penalty}")
        elif h1_miss > 0:
            penalty = h1_miss
            penalty = min(penalty, 15)
            score -= penalty
            penalties_log.append(f"Missing H1 ({h1_miss:.1f}%): -{penalty:.1f}")

        # 3. Titles
        title_miss = metrics['title']['missing_pct']
        if title_miss > 0:
            penalty = title_miss * 5
            penalty = min(penalty, 20)
            score -= penalty
            penalties_log.append(f"Missing Titles ({title_miss:.1f}%): -{penalty:.1f}")

        dup_title = metrics['title']['duplicate_pct']
        if dup_title > self.config.warning_threshold:
            penalty = 10
            score -= penalty
            penalties_log.append(f"Duplicate Titles (> {self.config.warning_threshold}%): -{penalty}")

        # 4. Meta Desc
        meta_miss = metrics['meta']['missing_pct']
        if meta_miss > self.config.warning_threshold:
            penalty = 10
            score -= penalty
            penalties_log.append(f"Missing Meta Desc (> {self.config.warning_threshold}%): -{penalty}")
        elif meta_miss > 0:
            penalty = meta_miss * 0.5
            score -= penalty
            penalties_log.append(f"Missing Meta Desc ({meta_miss:.1f}%): -{penalty:.1f}")

        # 5. Images
        img_miss = metrics['images']['missing_pct']
        if img_miss > self.config.warning_threshold:
            penalty = 10
            score -= penalty
            penalties_log.append(f"Missing Alt Text (> {self.config.warning_threshold}%): -{penalty}")

        # 6. Security (HTTPS)
        non_https_pct = (len(metrics['security']['non_https']) / metrics['http']['total'] * 100) if metrics['http']['total'] > 0 else 0
        if non_https_pct > 0:
            penalty = 10
            score -= penalty
            penalties_log.append(f"Insecure Pages (HTTP): -{penalty}")

        # 7. Huge Pages
        huge_page_count = len(metrics['others']['performance']['huge_pages'])
        if huge_page_count > 0:
            penalty = huge_page_count * 2
            penalty = min(penalty, 10)
            score -= penalty
            penalties_log.append(f"Huge Pages (> 2MB): -{penalty}")

        score = max(0, score)

        if score >= 90: rating = "EXCELLENT ✅"
        elif score >= 75: rating = "GOOD ✓"
        elif score >= 60: rating = "AVERAGE ⚠️"
        elif score >= 40: rating = "POOR ❌"
        else: rating = "CRITICAL 🔴"

        return score, rating, penalties_log
