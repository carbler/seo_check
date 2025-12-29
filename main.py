import os
from config import CRAWL_FILE, REPORT_FILE, LOG_FILE
from utils import setup_logging, print_header, print_section
from crawler import execute_crawl
from analyzer import (
    load_data, analyze_http_status, analyze_h1_tags, analyze_titles,
    analyze_meta_desc, analyze_canonical, analyze_images, analyze_links,
    analyze_security, analyze_others, calculate_score
)
from reporter import generate_report

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
