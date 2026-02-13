import advertools as adv
import sys
import json
import os
import logging

# Ensure unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Configure basic logging for the runner itself (stdout/stderr will be captured by parent or printed)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_crawl(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        url = config['url']
        output_file = config['output_file']
        settings = config['settings']
        selectors = config.get('selectors', {})

        print(f"Runner: Starting crawl for {url}", flush=True)
        print(f"Runner: Output file {output_file}", flush=True)

        # Execute crawl
        adv.crawl(
            url,
            output_file=output_file,
            follow_links=config.get('follow_links', True),
            css_selectors=selectors,
            custom_settings=settings
        )
        print("Runner: Crawl finished successfully.", flush=True)

    except Exception as e:
        print(f"Runner: Error during crawl: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crawl_runner.py <config_json_path>", flush=True)
        sys.exit(1)

    config_file = sys.argv[1]
    run_crawl(config_file)
