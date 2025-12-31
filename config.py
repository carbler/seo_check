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

    # Score Thresholds
    critical_threshold: int = 5
    warning_threshold: int = 10

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
