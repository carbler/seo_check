import advertools as adv
import pandas as pd
import numpy as np
import os
import sys
import json
import logging
import time
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

# Site to Analyze
BASE_URL = 'https://tuworker.com'
SITEMAP_URL = 'https://tuworker.com/sitemap-0.xml'

# Crawl Configuration
USER_AGENT = 'TuWorkerBot/1.0 (+https://tuworker.com/bot)'
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 0.5  # seconds between requests
ROBOTSTXT_OBEY = True
FOLLOW_LINKS = True  # Follow internal links
MAX_DEPTH = 10  # Maximum depth
TIMEOUT = 7200  # 2 hours max

# Output Files
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CRAWL_FILE = f'tuworker_crawl_{TIMESTAMP}.jl'
LOG_FILE = f'tuworker_crawl_{TIMESTAMP}.log'
REPORT_FILE = f'tuworker_report_{TIMESTAMP}.md'

# Thresholds (% of pages with issues)
CRITICAL_THRESHOLD = 5   # >5% = critical
WARNING_THRESHOLD = 10   # >10% = warning

# Integrations (Disabled as per request)
ENABLE_GSC = False
ENABLE_GA = False
GSC_PROPERTY = 'https://tuworker.com'
GA_VIEW_ID = ''

# =============================================================================
# UTILS
# =============================================================================

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

# =============================================================================
# STEP 1: CRAWLING
# =============================================================================

def execute_crawl():
    """Executes the crawl using advertools."""
    print("🕷️  STARTING CRAWL OF TUWORKER.COM")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚙️  Configuration:")
    print(f"   • User-Agent: {USER_AGENT}")
    print(f"   • Follow links: {FOLLOW_LINKS}")
    print(f"   • Obey robots.txt: {ROBOTSTXT_OBEY}")
    print(f"   • Max depth: {MAX_DEPTH}")
    print("   • No page limit")

    custom_settings = {
        'LOG_FILE': LOG_FILE,
        'ROBOTSTXT_OBEY': ROBOTSTXT_OBEY,
        'USER_AGENT': USER_AGENT,
        'CONCURRENT_REQUESTS': CONCURRENT_REQUESTS,
        'DOWNLOAD_DELAY': DOWNLOAD_DELAY,
        'CLOSESPIDER_TIMEOUT': TIMEOUT,
        'DEPTH_LIMIT': MAX_DEPTH,
        'HTTPERROR_ALLOW_ALL': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'REDIRECT_ENABLED': True,
    }

    start_time = time.time()
    print("\n⏳ Crawling in progress... (Check log file for details)")

    try:
        adv.crawl(
            BASE_URL,
            output_file=CRAWL_FILE,
            follow_links=FOLLOW_LINKS,
            custom_settings=custom_settings
        )
    except Exception as e:
        logging.error(f"Crawl failed: {e}")
        return None

    duration = time.time() - start_time
    print(f"✓ Crawl completed in {duration:.2f} seconds")
    return CRAWL_FILE

# =============================================================================
# STEP 2: DATA ANALYSIS
# =============================================================================

def load_data(crawl_file):
    """Loads crawled data into a DataFrame."""
    try:
        df = pd.read_json(crawl_file, lines=True)
        return df
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        return None

def analyze_http_status(df):
    """Analyzes HTTP status codes."""
    total = len(df)
    if 'status' not in df.columns:
         return {'stats': {}, 'errors': []}

    stats = df['status'].value_counts()

    # Identify errors
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

def analyze_h1_tags(df):
    """Analyzes H1 tags."""
    total = len(df)
    if 'h1' not in df.columns:
        return {'no_h1': df['url'].tolist(), 'multiple_h1': [], 'duplicate_h1': [], 'total': total, 'missing_pct': 100}

    no_h1 = []
    multiple_h1 = []
    h1_values = []

    for _, row in df.iterrows():
        h1s = to_list(row.get('h1'))
        h1s = [h for h in h1s if h.strip()] # Clean empty strings

        if not h1s:
            no_h1.append(row['url'])
        elif len(h1s) > 1:
            multiple_h1.append(row['url'])
            # Add all to list for duplicate check? Or just first?
            # Usually H1 should be unique per page.
            h1_values.extend([{'h1': h, 'url': row['url']} for h in h1s])
        else:
            h1_values.append({'h1': h1s[0], 'url': row['url']})

    # Duplicates logic
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

def analyze_titles(df):
    """Analyzes Title tags."""
    total = len(df)
    if 'title' not in df.columns:
        return {'missing': total, 'short': [], 'long': [], 'duplicates': {}, 'total': total}

    no_title = df[df['title'].isna() | (df['title'] == '')]['url'].tolist()

    # Length checks
    short_titles = df[df['title'].str.len() < 30]['url'].tolist()
    long_titles = df[df['title'].str.len() > 60]['url'].tolist()

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

def analyze_meta_desc(df):
    """Analyzes Meta Descriptions."""
    total = len(df)
    col_name = 'meta_desc'
    if col_name not in df.columns:
         return {'missing': total, 'short': [], 'long': [], 'duplicates': {}, 'total': total}

    no_meta = df[df[col_name].isna() | (df[col_name] == '')]['url'].tolist()

    short_meta = df[df[col_name].str.len() < 120]['url'].tolist()
    long_meta = df[df[col_name].str.len() > 160]['url'].tolist()

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

def analyze_canonical(df):
    """Analyzes Canonical tags."""
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

def analyze_images(df):
    """Analyzes Images (Alt text)."""
    # Fix: Handle lists for img_src and img_alt
    if 'img_alt' not in df.columns:
        return {'missing_alt_details': [], 'total_images': 0, 'missing_alt_count': 0, 'missing_pct': 0}

    total_imgs = 0
    missing_alt_count = 0
    missing_alt_urls = []

    for index, row in df.iterrows():
        # Clean lists
        srcs = to_list(row.get('img_src'))
        alts = to_list(row.get('img_alt'))

        # Filter empty strings/NaNs from srcs list if any
        # But usually we iterate.
        # Assumption: arrays are parallel?
        # Scrapy default behavior: If you extract 'img::attr(src)' and 'img::attr(alt)',
        # it returns two lists. They might NOT be aligned if one img has no alt and another does?
        # Actually, if we use advertools generic spider, it extracts all matches.
        # If we have 5 imgs and 3 alts, we can't map them 1:1 easily without context.
        # Approximation: Check number of empty/missing alts relative to srcs?
        # Or count empty strings in `alts` list?

        # If alts list is shorter than srcs list, we have missing alts?
        # If alts list contains empty strings?

        page_imgs = len(srcs)
        if page_imgs == 0: continue

        total_imgs += page_imgs

        # Count explicit empty alts ("")
        empty_in_list = len([x for x in alts if not x or not x.strip()])

        # Count missing alts (difference in length)
        # Note: This assumes scrape captured all alts corresponding to srcs.
        # If scrape missed alt attribute entirely, it might not be in the list?
        # Or it might be None?
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

def analyze_links(df):
    """Analyzes Internal/External Links."""
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

def analyze_security(df):
    """Analyzes Security (HTTPS)."""
    # HTTPS Check
    non_https = df[~df['url'].str.startswith('https://')]['url'].tolist()

    return {
        'non_https': non_https,
        'secure_pct': ((len(df) - len(non_https)) / len(df) * 100) if len(df) > 0 else 0
    }

def analyze_others(df):
    """Analyzes other elements (OG, Schema, Performance)."""
    results = {}
    total = len(df)

    # OG
    results['og'] = {
        'title': df['og_title'].notna().sum() if 'og_title' in df.columns else 0,
        'desc': df['og_description'].notna().sum() if 'og_description' in df.columns else 0,
        'image': df['og_image'].notna().sum() if 'og_image' in df.columns else 0,
        'total': total
    }

    # Schema (jsonld)
    results['schema'] = {
        'present': df['jsonld'].notna().sum() if 'jsonld' in df.columns else 0,
        'total': total
    }

    # Performance
    if 'download_latency' in df.columns:
        slow_pages = df[df['download_latency'] > 3]['url'].tolist()
        avg_time = df['download_latency'].mean()
    else:
        slow_pages = []
        avg_time = 0

    results['performance'] = {
        'slow_pages': slow_pages,
        'avg_time': avg_time
    }

    # URL Structure
    if 'url' in df.columns:
        # Avoid error if url is not string (should be string)
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

# =============================================================================
# STEP 3: SCORE CALCULATION
# =============================================================================

def calculate_score(metrics):
    score = 100
    penalties_log = []

    # 1. Broken Links (Critical)
    broken_rate = metrics['http']['error_rate_4xx']
    if broken_rate > CRITICAL_THRESHOLD:
        penalty = 25
        score -= penalty
        penalties_log.append(f"Broken Links (> {CRITICAL_THRESHOLD}%): -{penalty}")
    elif broken_rate > 0:
        penalty = broken_rate * 2
        penalty = min(penalty, 25)
        score -= penalty
        penalties_log.append(f"Broken Links ({broken_rate:.1f}%): -{penalty:.1f}")

    # 2. H1
    h1_miss = metrics['h1']['missing_pct']
    if h1_miss > WARNING_THRESHOLD:
        penalty = 15
        score -= penalty
        penalties_log.append(f"Missing H1 (> {WARNING_THRESHOLD}%): -{penalty}")
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
    if dup_title > WARNING_THRESHOLD:
        penalty = 10
        score -= penalty
        penalties_log.append(f"Duplicate Titles (> {WARNING_THRESHOLD}%): -{penalty}")

    # 4. Meta Desc
    meta_miss = metrics['meta']['missing_pct']
    if meta_miss > WARNING_THRESHOLD:
        penalty = 10
        score -= penalty
        penalties_log.append(f"Missing Meta Desc (> {WARNING_THRESHOLD}%): -{penalty}")
    elif meta_miss > 0:
        penalty = meta_miss * 0.5
        score -= penalty
        penalties_log.append(f"Missing Meta Desc ({meta_miss:.1f}%): -{penalty:.1f}")

    # 5. Images
    img_miss = metrics['images']['missing_pct']
    if img_miss > WARNING_THRESHOLD:
        penalty = 10
        score -= penalty
        penalties_log.append(f"Missing Alt Text (> {WARNING_THRESHOLD}%): -{penalty}")

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

# =============================================================================
# STEP 4: REPORTING
# =============================================================================

def generate_report(metrics, score, rating, penalties, filename):

    http = metrics['http']
    h1 = metrics['h1']
    titles = metrics['title']
    meta = metrics['meta']
    canonical = metrics['canonical']
    images = metrics['images']
    links = metrics['links']
    security = metrics['security']
    others = metrics['others']

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# 🔍 TuWorker.com - Technical SEO Analysis\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Base URL**: {BASE_URL}  \n")
        f.write(f"**Pages Analyzed**: {http['total']}\n\n")
        f.write(f"---\n\n")

        f.write(f"## 📊 Executive Summary\n\n")
        f.write(f"**SEO SCORE: {score:.1f}/100 - {rating}**\n\n")

        f.write("### Key Metrics\n")
        f.write("| Metric | Value | Status |\n")
        f.write("|--------|-------|--------|\n")
        f.write(f"| Total URLs | {http['total']} | - |\n")
        f.write(f"| OK Pages (200) | {http.get('stats', {}).get(200, 0)} | {'✅' if http['error_rate_4xx'] < 5 else '⚠️'} |\n")
        f.write(f"| Broken Links (4xx) | {len(http['broken_links'])} | {'✅' if http['error_rate_4xx'] < 5 else '❌'} {http['error_rate_4xx']:.1f}% |\n")
        f.write(f"| With H1 | {h1['total'] - len(h1['no_h1'])} | {100-h1['missing_pct']:.1f}% |\n")
        f.write(f"| With Title | {titles['total'] - len(titles['no_title'])} | {100-titles['missing_pct']:.1f}% |\n")
        f.write(f"| With Meta Desc | {meta['total'] - len(meta['no_meta'])} | {100-meta['missing_pct']:.1f}% |\n")
        f.write(f"| Images w/ Alt | {images['total_images'] - images['missing_alt_count']} | {100-images['missing_pct']:.1f}% |\n")
        f.write(f"| Secure (HTTPS) | {len(security['non_https'])} non-https | {security['secure_pct']:.1f}% |\n\n")

        f.write("### Score Penalties\n")
        for p in penalties:
            f.write(f"- {p}\n")
        f.write("\n---\n\n")

        f.write("## 🔴 Broken Links (4xx)\n")
        if http['broken_links']:
            for link in http['broken_links'][:20]:
                f.write(f"- {link['url']} ({link['status']})\n")
            if len(http['broken_links']) > 20:
                f.write(f"- ... and {len(http['broken_links']) - 20} more.\n")
        else:
            f.write("None detected ✅\n")
        f.write("\n")

        f.write("## 🔤 H1 Tags\n")
        f.write(f"- Pages without H1: {len(h1['no_h1'])}\n")
        f.write(f"- Duplicate H1 Groups: {len(h1['duplicate_h1'])}\n")
        if h1['no_h1']:
            f.write("\n**Sample Pages without H1:**\n")
            for url in h1['no_h1'][:10]:
                f.write(f"- {url}\n")
        f.write("\n")

        f.write("## 📄 Title Tags\n")
        f.write(f"- Pages without Title: {len(titles['no_title'])}\n")
        f.write(f"- Too Short (<30): {len(titles['short'])}\n")
        f.write(f"- Too Long (>60): {len(titles['long'])}\n")
        if titles['long']:
             f.write("\n**Sample Long Titles:**\n")
             for url in titles['long'][:5]:
                 f.write(f"- {url}\n")
        f.write("\n")

        f.write("## 📝 Meta Descriptions\n")
        f.write(f"- Missing: {len(meta['no_meta'])}\n")
        f.write(f"- Too Short (<120): {len(meta['short'])}\n")
        f.write(f"- Too Long (>160): {len(meta['long'])}\n")
        f.write("\n")

        f.write("## 🔗 Links Structure\n")
        f.write(f"- Internal Links: {links['internal']}\n")
        f.write(f"- External Links: {links['external']}\n")
        f.write(f"- Internal/External Ratio: {links['ratio']:.2f}\n")
        f.write("\n")

        f.write("## 🔒 Security\n")
        f.write(f"- Non-HTTPS Pages: {len(security['non_https'])}\n")
        if security['non_https']:
             for url in security['non_https'][:5]:
                 f.write(f"- {url}\n")
        f.write("\n")

        f.write("## 🔄 Canonical Tags\n")
        f.write(f"- Missing: {len(canonical['no_canonical'])}\n")
        f.write(f"- Canonical points to different URL: {len(canonical['diff'])}\n")
        f.write("\n")

        f.write("## 🖼️ Images\n")
        f.write(f"- Total Images Analyzed: {images['total_images']}\n")
        f.write(f"- Missing Alt Text: {images['missing_alt_count']} ({images['missing_pct']:.1f}%)\n")
        if images['missing_alt_details']:
            f.write("\n**Sample Pages with missing Alt:**\n")
            for item in images['missing_alt_details'][:10]:
                f.write(f"- {item['url']} ({item['count']} images)\n")
        f.write("\n")

        f.write("## ⚡ Performance & Other\n")
        f.write(f"- Average Response Time: {others['performance']['avg_time']:.2f}s\n")
        f.write(f"- Slow Pages (>3s): {len(others['performance']['slow_pages'])}\n")
        f.write(f"- Pages with Schema: {others['schema']['present']}\n")
        f.write(f"- Pages with OG Image: {others['og']['image']}\n")

    print(f"✓ Report generated: {filename}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    setup_logging()
    print_header()

    # 1. Crawl
    print_section("STEP 1: CRAWLING")
    if os.path.exists(CRAWL_FILE):
        print(f"⚠️  Crawl file {CRAWL_FILE} already exists. Using existing file.")
        crawl_output = CRAWL_FILE
    else:
        crawl_output = execute_crawl()

    if not crawl_output:
        print("❌ Crawl failed or returned no data. Exiting.")
        return

    # 2. Analyze
    print_section("STEP 2: ANALYSIS")
    df = load_data(crawl_output)
    if df is None or len(df) == 0:
        print("❌ No data found in crawl file.")
        return

    print(f"✓ Loaded {len(df)} pages for analysis.")

    metrics = {}
    print("• Analyzing HTTP Status...")
    metrics['http'] = analyze_http_status(df)

    print("• Analyzing H1 Tags...")
    metrics['h1'] = analyze_h1_tags(df)

    print("• Analyzing Titles...")
    metrics['title'] = analyze_titles(df)

    print("• Analyzing Meta Descriptions...")
    metrics['meta'] = analyze_meta_desc(df)

    print("• Analyzing Canonicals...")
    metrics['canonical'] = analyze_canonical(df)

    print("• Analyzing Images...")
    metrics['images'] = analyze_images(df)

    print("• Analyzing Links...")
    metrics['links'] = analyze_links(df)

    print("• Analyzing Security...")
    metrics['security'] = analyze_security(df)

    print("• Analyzing Others (Performance, OG, Schema)...")
    metrics['others'] = analyze_others(df)

    # 3. Score
    print_section("STEP 3: SEO SCORE")
    score, rating, penalties = calculate_score(metrics)
    print(f"🎯 GLOBAL SEO SCORE: {score:.1f}/100 - {rating}")

    # 4. Report
    print_section("STEP 4: REPORT GENERATION")
    generate_report(metrics, score, rating, penalties, REPORT_FILE)

    print("\n" + "="*60)
    print("✨ ANALYSIS COMPLETED SUCCESSFULLY")
    print("="*60 + "\n")
    print(f"📁 Files generated:")
    print(f"   • Report: {REPORT_FILE}")
    print(f"   • Data:   {CRAWL_FILE}")
    print(f"   • Log:    {LOG_FILE}\n")

if __name__ == "__main__":
    main()
