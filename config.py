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
