import os
import sys
import logging
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import SEOConfig
from utils import setup_logging
from crawler import SEOCrawler
from analyzer import SEOAnalyzer, SEOScorer
from reporter import ReporterFactory

console = Console()

class SEOApplication:
    """Main application facade for the SEO Analyzer."""

    def __init__(self):
        self.config = SEOConfig()

    def setup_workspace(self):
        """Creates necessary directories."""
        if not os.path.exists(self.config.output_dir):
            os.makedirs(self.config.output_dir)

    def get_user_input(self):
        """Interactive CLI for configuration."""
        console.print(Panel.fit("[bold blue]SEO Analyzer v1.0[/bold blue]", border_style="blue"))

        self.config.base_url = Prompt.ask("[bold green]Enter Target URL[/bold green]", default="https://example.com")
        self.config.max_depth = IntPrompt.ask("[bold green]Max Crawl Depth[/bold green]", default=3)

        # Determine sitemap automatically if possible
        if not self.config.sitemap_url:
            self.config.sitemap_url = self.config.base_url.rstrip('/') + '/sitemap.xml'

    def run(self):
        """Runs the complete SEO analysis workflow."""
        try:
            self.get_user_input()
            self.setup_workspace()
            setup_logging(self.config.log_file)

            console.print(f"\n[dim]Output directory: {self.config.output_dir}[/dim]\n")

            # 1. Crawl
            crawl_output = None
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                task = progress.add_task("[cyan]Crawling website...", total=None)
                crawler = SEOCrawler(self.config)
                crawl_output = crawler.execute()

            if not crawl_output:
                console.print("[bold red]❌ Crawl failed or returned no data. Check logs.[/bold red]")
                return

            console.print("[green]✓ Crawl completed[/green]")

            # 2. Analyze
            df = None
            analyzer = SEOAnalyzer(self.config)

            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                task = progress.add_task("[cyan]Loading data...", total=None)
                df = analyzer.load_data(crawl_output)

            if df is None or len(df) == 0:
                console.print("[bold red]❌ No data found in crawl file.[/bold red]")
                return

            console.print(f"[green]✓ Loaded {len(df)} pages[/green]")

            metrics = None
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                task = progress.add_task("[cyan]Analyzing SEO metrics...", total=None)
                metrics = analyzer.analyze(df)

            console.print("[green]✓ Analysis complete[/green]")

            # 3. Score
            scorer = SEOScorer(self.config)
            score, rating, penalties = scorer.calculate(metrics)

            # 4. Report
            reporter = ReporterFactory.create_reporter(self.config, metrics, score, rating, penalties)
            reporter.generate()

            # Final Summary
            console.print("\n[bold]✨ Analysis Finished![/bold]")
            console.print(Panel(f"""
[bold]Score:[/bold] {score:.1f}/100 ({rating})
[bold]Pages:[/bold] {metrics['http']['total']}
[bold]Report:[/bold] {self.config.report_file}
            """, title="Summary", border_style="green"))

            console.print("\n[bold yellow]👉 Open 'viewer.html' in your browser and load the generated JSON file to view the report.[/bold yellow]\n")

        except KeyboardInterrupt:
            console.print("\n[bold red]Operation cancelled by user.[/bold red]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[bold red]Unexpected Error:[/bold red] {e}")
            logging.exception("Fatal error")
            sys.exit(1)

if __name__ == "__main__":
    app = SEOApplication()
    app.run()
