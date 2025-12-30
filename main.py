import os
import sys
from config import SEOConfig
from utils import setup_logging, print_header, print_section
from crawler import SEOCrawler
from analyzer import SEOAnalyzer, SEOScorer
from reporter import ReporterFactory

class SEOApplication:
    """Main application facade for the SEO Analyzer."""

    def __init__(self):
        self.config = SEOConfig()

    def setup_workspace(self):
        """Creates necessary directories."""
        if not os.path.exists(self.config.output_dir):
            os.makedirs(self.config.output_dir)
            print(f"📁 Created output directory: {self.config.output_dir}")

    def run(self):
        """Runs the complete SEO analysis workflow."""
        self.setup_workspace()

        setup_logging(self.config.log_file)
        print_header()

        # 1. Crawl
        print_section("STEP 1: CRAWLING")
        crawler = SEOCrawler(self.config)

        # Check if crawl file already exists in this specific timestamped folder (unlikely unless rerun)
        if os.path.exists(self.config.crawl_file):
            print(f"⚠️  Crawl file {self.config.crawl_file} already exists. Using existing file.")
            crawl_output = self.config.crawl_file
        else:
            crawl_output = crawler.execute()

        if not crawl_output:
            print("❌ Crawl failed or returned no data. Exiting.")
            return

        # 2. Analyze
        print_section("STEP 2: ANALYSIS")
        analyzer = SEOAnalyzer(self.config)
        df = analyzer.load_data(crawl_output)

        if df is None or len(df) == 0:
            print("❌ No data found in crawl file.")
            return

        print(f"✓ Loaded {len(df)} pages for analysis.")

        # Perform analysis
        print("• Running analysis modules...")
        metrics = analyzer.analyze(df)

        # 3. Score
        print_section("STEP 3: SEO SCORE")
        scorer = SEOScorer(self.config)
        score, rating, penalties = scorer.calculate(metrics)
        print(f"🎯 GLOBAL SEO SCORE: {score:.1f}/100 - {rating}")

        # 4. Report
        print_section(f"STEP 4: REPORT GENERATION ({self.config.output_format.upper()})")
        reporter = ReporterFactory.create_reporter(self.config, metrics, score, rating, penalties)
        reporter.generate()

        print("\n" + "="*60)
        print("✨ ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
        print(f"📁 Files generated in: {self.config.output_dir}")
        print(f"   • Report: {os.path.basename(self.config.report_file)}")
        print(f"   • Data:   {os.path.basename(self.config.crawl_file)}")
        print(f"   • Log:    {os.path.basename(self.config.log_file)}\n")

if __name__ == "__main__":
    app = SEOApplication()
    app.run()
