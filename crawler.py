import advertools as adv
import time
import logging
from config import SEOConfig

class SEOCrawler:
    """Handles the website crawling process."""

    def __init__(self, config: SEOConfig):
        self.config = config

    def execute(self) -> str:
        """Executes the crawl using advertools."""
        print("🕷️  STARTING CRAWL OF TUWORKER.COM")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("⚙️  Configuration:")
        print(f"   • User-Agent: {self.config.user_agent}")
        print(f"   • Follow links: {self.config.follow_links}")
        print(f"   • Obey robots.txt: {self.config.robotstxt_obey}")
        print(f"   • Max depth: {self.config.max_depth}")
        print("   • No page limit")

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
                custom_settings=custom_settings
            )
        except Exception as e:
            logging.error(f"Crawl failed: {e}")
            return None

        duration = time.time() - start_time
        print(f"✓ Crawl completed in {duration:.2f} seconds")
        return self.config.crawl_file
