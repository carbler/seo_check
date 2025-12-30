import pandas as pd
import logging
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
        metrics['http'] = self._analyze_http_status(df)
        metrics['h1'] = self._analyze_h1_tags(df)
        metrics['title'] = self._analyze_titles(df)
        metrics['meta'] = self._analyze_meta_desc(df)
        metrics['canonical'] = self._analyze_canonical(df)
        metrics['images'] = self._analyze_images(df)
        metrics['links'] = self._analyze_links(df)
        metrics['security'] = self._analyze_security(df)
        metrics['others'] = self._analyze_others(df)
        return metrics

    def _analyze_http_status(self, df):
        total = len(df)
        if 'status' not in df.columns:
             return {'stats': {}, 'errors': []}

        stats = df['status'].value_counts()

        errors_4xx = df[df['status'].between(400, 499)]
        errors_5xx = df[df['status'].between(500, 599)]

        broken_links = errors_4xx[['url', 'status']].to_dict('records')
        server_errors = errors_5xx[['url', 'status']].to_dict('records')

        return {
            'stats': stats.to_dict(),
            'broken_links': broken_links,
            'server_errors': server_errors,
            'total': total,
            'error_rate_4xx': (len(errors_4xx) / total) * 100 if total > 0 else 0,
            'error_rate_5xx': (len(errors_5xx) / total) * 100 if total > 0 else 0
        }

    def _analyze_h1_tags(self, df):
        total = len(df)
        if 'h1' not in df.columns:
            return {'no_h1': df['url'].tolist(), 'multiple_h1': [], 'duplicate_h1': [], 'total': total, 'missing_pct': 100}

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
            return {'missing': total, 'short': [], 'long': [], 'duplicates': {}, 'total': total}

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
             return {'missing': total, 'short': [], 'long': [], 'duplicates': {}, 'total': total}

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
             return {'missing': [], 'diff': [], 'total': total}

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
            return {'missing_alt_details': [], 'total_images': 0, 'missing_alt_count': 0, 'missing_pct': 0}

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

        for links in df['links_url']:
            links = to_list(links)
            for l in links:
                if 'tuworker.com' in l:
                    total_internal += 1
                elif l.startswith('http'):
                    total_external += 1

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

        results['performance'] = {
            'slow_pages': slow_pages,
            'avg_time': avg_time
        }

        if 'url' in df.columns:
            df['depth'] = df['url'].astype(str).apply(lambda x: x.count('/'))
            avg_depth = df['depth'].mean()
            max_depth = df['depth'].max()
        else:
            avg_depth = 0
            max_depth = 0

        results['urls'] = {
            'avg_depth': avg_depth,
            'max_depth': max_depth
        }

        return results

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

        score = max(0, score)

        if score >= 90: rating = "EXCELLENT ✅"
        elif score >= 75: rating = "GOOD ✓"
        elif score >= 60: rating = "AVERAGE ⚠️"
        elif score >= 40: rating = "POOR ❌"
        else: rating = "CRITICAL 🔴"

        return score, rating, penalties_log
