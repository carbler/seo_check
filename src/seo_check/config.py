import os
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class SEOConfig:
    """Configuration settings for the SEO Analyzer."""

    # These will be set via CLI
    base_url: str = ''
    max_depth: int = 3

    # Internal defaults
    sitemap_url: str = ''
    user_agent: str = 'SEOAnalyzerBot/1.0 (+https://example.com/bot)'
    concurrent_requests: int = 8
    download_delay: float = 0.5
    robotstxt_obey: bool = True
    follow_links: bool = True
    timeout: int = 3600

    # Analysis Thresholds
    title_min_length: int = 30
    title_max_length: int = 60
    meta_desc_min_length: int = 120
    meta_desc_max_length: int = 160
    slow_page_threshold: float = 3.0
    min_word_count: int = 250
    text_ratio_threshold: float = 10.0

    # NEW: File Size Threshold (2MB)
    max_page_size_bytes: int = 2 * 1024 * 1024

    # Score Thresholds (How many failures allowed before penalty triggers)
    critical_threshold: int = 5
    warning_threshold: int = 10

    # Penalty Weights (Points subtracted from 100 base score)
    # Based on Google Ranking Factors and User Experience best practices.
    
    # Penalty weights are calibrated to Google's ranking factor priority tiers.
    # Max theoretical deduction ≈ 200 pts (score is floor-capped at 0).

    # TIER 1 — Indexability blockers (page is completely invisible to Google)
    penalty_noindex_page: float = 25.0      # noindex = page cannot rank, period.
    penalty_robots_disallow: float = 25.0   # Googlebot can't crawl → can't index.
    noindex_threshold: int = 2              # % of pages with noindex before full penalty

    # TIER 2 — Security (ranking signal + trust)
    penalty_invalid_ssl: float = 20.0       # Cert error → browser blocks users.
    penalty_insecure_http: float = 15.0     # Google ranking factor since 2014.

    # TIER 3 — Core on-page signals (what Google uses to understand & rank content)
    penalty_missing_title: float = 20.0     # Primary on-page ranking factor.
    penalty_missing_h1: float = 15.0        # Topic signal — critical for relevance.
    penalty_duplicate_title: float = 10.0   # Dilutes ranking signals across pages.
    penalty_duplicate_content: float = 15.0 # Splits authority; Google chooses one URL.
    duplicate_content_threshold: int = 5    # % of pages with duplicate body text

    # TIER 4 — Crawl health & UX (crawl budget + user experience)
    penalty_broken_link: float = 15.0       # Crawl budget waste + 404 UX damage.
    penalty_mixed_content: float = 10.0     # Chrome blocks HTTP on HTTPS — UX failure.
    penalty_broken_image: float = 8.0       # UX signal; broken assets = poor quality.
    broken_image_threshold: int = 5         # % of images that are broken

    # TIER 5 — CTR & discovery (indirect ranking via clicks & enrichment)
    penalty_missing_meta: float = 8.0       # Affects CTR in SERP, not direct ranking.
    penalty_missing_alt: float = 7.0        # Image SEO + accessibility (indirect).
    penalty_huge_page: float = 10.0         # Mobile-first CWV — page weight matters.

    # TIER 6 — Performance headers (Core Web Vitals delivery signals)
    penalty_no_compression: float = 6.0     # gzip/brotli directly reduces TTFB.
    penalty_bad_cache: float = 4.0          # Re-fetch overhead hurts repeat visitors.
    compression_threshold: int = 30         # % of HTML pages without compression
    cache_threshold: int = 30               # % of HTML pages with bad cache headers

    # TIER 7 — Internal link quality (PageRank flow)
    penalty_nofollow_internal: float = 5.0  # Wasted internal PageRank.
    penalty_page_nofollow: float = 3.0      # Less critical than noindex.
    penalty_generic_anchors: float = 4.0    # Weak semantic signal for internal links.
    generic_anchor_threshold: int = 10      # % of internal links with generic anchors

    # TIER 8 — URL hygiene (minor technical signal)
    penalty_url_quality: float = 5.0        # Underscores, uppercase, deep paths.
    url_quality_threshold: int = 20         # % of pages with URL quality issues

    # Output Configuration
    output_format: str = 'json'

    # Dynamic Filenames
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    @property
    def output_dir(self) -> str:
        return os.path.join('reports', self.timestamp)

    @property
    def crawl_file(self) -> str:
        return os.path.join(self.output_dir, 'crawl_data.jl')

    @property
    def log_file(self) -> str:
        return os.path.join(self.output_dir, 'execution.log')

    @property
    def report_file(self) -> str:
        return os.path.join(self.output_dir, 'report.json')
