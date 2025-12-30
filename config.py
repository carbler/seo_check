import os
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class SEOConfig:
    """Configuration settings for the SEO Analyzer."""

    # Site to Analyze
    base_url: str = 'https://tuworker.com'
    sitemap_url: str = 'https://tuworker.com/sitemap-0.xml'

    # Crawl Configuration
    user_agent: str = 'TuWorkerBot/1.0 (+https://tuworker.com/bot)'
    concurrent_requests: int = 8
    download_delay: float = 0.5
    robotstxt_obey: bool = True
    follow_links: bool = True
    max_depth: int = 10
    timeout: int = 7200  # 2 hours

    # SEO Limits & Thresholds
    title_min_length: int = 30
    title_max_length: int = 60
    meta_desc_min_length: int = 120
    meta_desc_max_length: int = 160
    slow_page_threshold: float = 3.0

    # Thresholds (% of pages with issues)
    critical_threshold: int = 5
    warning_threshold: int = 10

    # Integrations
    enable_gsc: bool = False
    enable_ga: bool = False
    gsc_property: str = 'https://tuworker.com'
    ga_view_id: str = ''

    # Output Configuration
    output_format: str = 'md'  # options: 'md', 'html', 'json'

    # Dynamic Filenames
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    @property
    def output_dir(self) -> str:
        return os.path.join('reports', self.timestamp)

    @property
    def crawl_file(self) -> str:
        return os.path.join(self.output_dir, f'tuworker_crawl_{self.timestamp}.jl')

    @property
    def log_file(self) -> str:
        return os.path.join(self.output_dir, f'tuworker_crawl_{self.timestamp}.log')

    @property
    def report_file(self) -> str:
        ext = self.output_format.lower()
        return os.path.join(self.output_dir, f'tuworker_report_{self.timestamp}.{ext}')
