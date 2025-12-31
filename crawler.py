import advertools as adv
import time
import logging
import requests
from urllib.parse import urlparse, urljoin
from config import SEOConfig

class SEOCrawler:
    """Handles the website crawling process."""

    def __init__(self, config: SEOConfig):
        self.config = config

    def discover_sitemaps(self) -> list:
        """Attempts to find sitemaps via robots.txt and common paths."""
        sitemaps = []
        base_url = self.config.base_url

        # 1. Check robots.txt
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            logging.info(f"Checking {robots_url} for sitemaps...")

            # Simple fetch to avoid heavy advertools dependency for just this lines
            resp = requests.get(robots_url, timeout=10, headers={'User-Agent': self.config.user_agent})
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    if line.lower().strip().startswith('sitemap:'):
                        smap = line.split(':', 1)[1].strip()
                        if smap not in sitemaps:
                            sitemaps.append(smap)
        except Exception as e:
            logging.warning(f"Failed to fetch/parse robots.txt: {e}")

        # 2. Check common paths if none found
        if not sitemaps:
            common_paths = ['/sitemap.xml', '/sitemap_index.xml', '/sitemap/sitemap.xml']
            for path in common_paths:
                url = urljoin(base_url, path)
                try:
                    head = requests.head(url, timeout=5, headers={'User-Agent': self.config.user_agent})
                    if head.status_code == 200:
                        sitemaps.append(url)
                except:
                    pass

        logging.info(f"Discovered sitemaps: {sitemaps}")
        return sitemaps

    def execute(self) -> str:
        """Executes the crawl using advertools."""
        print(f"🕷️  STARTING CRAWL OF {self.config.base_url}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("⚙️  Configuration:")
        print(f"   • User-Agent: {self.config.user_agent}")
        print(f"   • Follow links: {self.config.follow_links}")
        print(f"   • Obey robots.txt: {self.config.robotstxt_obey}")
        print(f"   • Max depth: {self.config.max_depth}")
        print("   • No page limit")

        # Add body text extraction to enable content analysis
        # Using a custom name to avoid conflict with advertools default keys if present
        selectors = {
            'page_body_text': 'body ::text',
        }

        custom_settings = {
            'LOG_FILE': self.config.log_file,
            'ROBOTSTXT_OBEY': self.config.robotstxt_obey,
            'USER_AGENT': self.config.user_agent,
            'CONCURRENT_REQUESTS': self.config.concurrent_requests,
            'DOWNLOAD_DELAY': self.config.download_delay,
            'CLOSESPIDER_TIMEOUT': self.config.timeout,
            'DEPTH_LIMIT': self.config.max_depth,
            'HTTPERROR_ALLOW_ALL': True,
            'RETRY_ENABLED': True,
            'RETRY_TIMES': 3,
            'REDIRECT_ENABLED': True,
        }

        start_time = time.time()
        print("\n⏳ Crawling in progress... (Check log file for details)")

        try:
            adv.crawl(
                self.config.base_url,
                output_file=self.config.crawl_file,
                follow_links=self.config.follow_links,
                css_selectors=selectors,
                custom_settings=custom_settings
            )
        except Exception as e:
            logging.error(f"Crawl failed: {e}")
            return None

        duration = time.time() - start_time
        print(f"✓ Crawl completed in {duration:.2f} seconds")
        return self.config.crawl_file
