import advertools as adv
import time
import logging
from config import (
    BASE_URL, USER_AGENT, CONCURRENT_REQUESTS, DOWNLOAD_DELAY,
    ROBOTSTXT_OBEY, MAX_DEPTH, TIMEOUT, CRAWL_FILE, LOG_FILE, FOLLOW_LINKS
)

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
