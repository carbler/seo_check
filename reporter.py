from abc import ABC, abstractmethod
from datetime import datetime
import json
from config import SEOConfig

class SEOReporter(ABC):
    """Abstract base class for SEO reporters."""

    def __init__(self, config: SEOConfig, metrics: dict, score: float, rating: str, penalties: list):
        self.config = config
        self.metrics = metrics
        self.score = score
        self.rating = rating
        self.penalties = penalties

    @abstractmethod
    def generate(self):
        """Generates the report."""
        pass

class MarkdownReporter(SEOReporter):
    """Generates a Markdown report."""

    def generate(self):
        filename = self.config.report_file
        http = self.metrics['http']
        h1 = self.metrics['h1']
        titles = self.metrics['title']
        meta = self.metrics['meta']
        canonical = self.metrics['canonical']
        images = self.metrics['images']
        links = self.metrics['links']
        security = self.metrics['security']
        others = self.metrics['others']

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 🔍 TuWorker.com - Technical SEO Analysis\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Base URL**: {self.config.base_url}  \n")
            f.write(f"**Pages Analyzed**: {http['total']}\n\n")
            f.write(f"---\n\n")

            f.write(f"## 📊 Executive Summary\n\n")
            f.write(f"**SEO SCORE: {self.score:.1f}/100 - {self.rating}**\n\n")

            f.write("### Key Metrics\n")
            f.write("| Metric | Value | Status |\n")
            f.write("|--------|-------|--------|\n")
            f.write(f"| Total URLs | {http['total']} | - |\n")
            f.write(f"| OK Pages (200) | {http.get('stats', {}).get(200, 0)} | {'✅' if http['error_rate_4xx'] < self.config.critical_threshold else '⚠️'} |\n")
            f.write(f"| Broken Links (4xx) | {len(http['broken_links'])} | {'✅' if http['error_rate_4xx'] < self.config.critical_threshold else '❌'} {http['error_rate_4xx']:.1f}% |\n")
            f.write(f"| With H1 | {h1['total'] - len(h1['no_h1'])} | {100-h1['missing_pct']:.1f}% |\n")
            f.write(f"| With Title | {titles['total'] - len(titles['no_title'])} | {100-titles['missing_pct']:.1f}% |\n")
            f.write(f"| With Meta Desc | {meta['total'] - len(meta['no_meta'])} | {100-meta['missing_pct']:.1f}% |\n")
            f.write(f"| Images w/ Alt | {images['total_images'] - images['missing_alt_count']} | {100-images['missing_pct']:.1f}% |\n")
            f.write(f"| Secure (HTTPS) | {len(security['non_https'])} non-https | {security['secure_pct']:.1f}% |\n\n")

            f.write("### Score Penalties\n")
            for p in self.penalties:
                f.write(f"- {p}\n")
            f.write("\n---\n\n")

            # --- Detailed Sections ---
            self._write_section(f, "🔴 Broken Links (4xx)", http['broken_links'],
                              lambda x: f"- {x['url']} ({x['status']})")

            self._write_h1_section(f, h1)
            self._write_titles_section(f, titles)
            self._write_meta_section(f, meta)

            f.write("## 🔗 Links Structure\n")
            f.write(f"- Internal Links: {links['internal']}\n")
            f.write(f"- External Links: {links['external']}\n")
            f.write(f"- Internal/External Ratio: {links['ratio']:.2f}\n")
            f.write("\n")

            self._write_section(f, "🔒 Security (Non-HTTPS)", security['non_https'],
                              lambda x: f"- {x}")

            self._write_canonical_section(f, canonical)
            self._write_images_section(f, images)

            f.write("## ⚡ Performance & Other\n")
            f.write(f"- Average Response Time: {others['performance']['avg_time']:.2f}s\n")
            f.write(f"- Pages with Schema: {others['schema']['present']}\n")
            f.write(f"- Pages with OG Image: {others['og']['image']}\n")

            if others['performance']['slow_pages']:
                f.write(f"\n**Slow Pages (>{self.config.slow_page_threshold}s):**\n")
                for url in others['performance']['slow_pages']:
                    f.write(f"- {url}\n")

        print(f"✓ Report generated: {filename}")

    def _write_section(self, f, title, items, format_func):
        f.write(f"## {title}\n")
        if items:
            for item in items:
                f.write(f"{format_func(item)}\n")
        else:
            f.write("None detected ✅\n")
        f.write("\n")

    def _write_h1_section(self, f, h1):
        f.write("## 🔤 H1 Tags\n")
        f.write(f"- Pages without H1: {len(h1['no_h1'])}\n")
        f.write(f"- Duplicate H1 Groups: {len(h1['duplicate_h1'])}\n")

        if h1['no_h1']:
            f.write("\n**Pages without H1:**\n")
            for url in h1['no_h1']:
                f.write(f"- {url}\n")

        if h1['duplicate_h1']:
            f.write("\n**Duplicate H1 Groups:**\n")
            for h1_text, urls in h1['duplicate_h1'].items():
                f.write(f"\n**\"{h1_text}\"** used on:\n")
                for url in urls:
                    f.write(f"- {url}\n")
        f.write("\n")

    def _write_titles_section(self, f, titles):
        f.write("## 📄 Title Tags\n")
        f.write(f"- Pages without Title: {len(titles['no_title'])}\n")
        f.write(f"- Too Short (<{self.config.title_min_length}): {len(titles['short'])}\n")
        f.write(f"- Too Long (>{self.config.title_max_length}): {len(titles['long'])}\n")
        f.write(f"- Duplicate Title Groups: {len(titles['duplicates'])}\n")

        if titles['no_title']:
            f.write("\n**Pages without Title:**\n")
            for url in titles['no_title']:
                f.write(f"- {url}\n")

        if titles['duplicates']:
            f.write("\n**Duplicate Title Groups:**\n")
            for txt, urls in titles['duplicates'].items():
                f.write(f"\n**\"{txt}\"** used on:\n")
                for url in urls:
                    f.write(f"- {url}\n")

        if titles['short']:
            f.write(f"\n**Titles Too Short:**\n")
            for url in titles['short']:
                f.write(f"- {url}\n")

        if titles['long']:
             f.write(f"\n**Titles Too Long:**\n")
             for url in titles['long']:
                 f.write(f"- {url}\n")
        f.write("\n")

    def _write_meta_section(self, f, meta):
        f.write("## 📝 Meta Descriptions\n")
        f.write(f"- Missing: {len(meta['no_meta'])}\n")
        f.write(f"- Too Short (<{self.config.meta_desc_min_length}): {len(meta['short'])}\n")
        f.write(f"- Too Long (>{self.config.meta_desc_max_length}): {len(meta['long'])}\n")
        f.write(f"- Duplicate Meta Groups: {len(meta['duplicates'])}\n")

        if meta['no_meta']:
            f.write("\n**Pages without Meta Description:**\n")
            for url in meta['no_meta']:
                f.write(f"- {url}\n")

        if meta['duplicates']:
            f.write("\n**Duplicate Meta Groups:**\n")
            for txt, urls in meta['duplicates'].items():
                display = (txt[:75] + '...') if len(txt) > 75 else txt
                f.write(f"\n**\"{display}\"** used on:\n")
                for url in urls:
                    f.write(f"- {url}\n")

        if meta['short']:
            f.write(f"\n**Meta Too Short:**\n")
            for url in meta['short']:
                f.write(f"- {url}\n")

        if meta['long']:
            f.write(f"\n**Meta Too Long:**\n")
            for url in meta['long']:
                f.write(f"- {url}\n")
        f.write("\n")

    def _write_canonical_section(self, f, canonical):
        f.write("## 🔄 Canonical Tags\n")
        f.write(f"- Missing: {len(canonical['no_canonical'])}\n")
        f.write(f"- Different: {len(canonical['diff'])}\n")

        if canonical['no_canonical']:
            f.write("\n**Pages without Canonical:**\n")
            for url in canonical['no_canonical']:
                f.write(f"- {url}\n")

        if canonical['diff']:
            f.write("\n**Canonical points to different URL:**\n")
            for item in canonical['diff']:
                f.write(f"- {item['url']} -> {item['canonical']}\n")
        f.write("\n")

    def _write_images_section(self, f, images):
        f.write("## 🖼️ Images\n")
        f.write(f"- Total Images: {images['total_images']}\n")
        f.write(f"- Missing Alt: {images['missing_alt_count']} ({images['missing_pct']:.1f}%)\n")
        if images['missing_alt_details']:
            f.write("\n**Pages with missing Alt:**\n")
            for item in images['missing_alt_details']:
                f.write(f"- {item['url']} ({item['count']} images)\n")
        f.write("\n")


class HTMLReporter(SEOReporter):
    """Generates an HTML report."""

    def generate(self):
        filename = self.config.report_file
        # Simplified HTML generation logic
        html_content = f"""
        <html>
        <head><title>SEO Report - {self.config.base_url}</title>
        <style>body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
               h1, h2 {{ color: #333; }}
               .score {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
               .warning {{ color: orange; }} .critical {{ color: red; }} .good {{ color: green; }}
        </style>
        </head>
        <body>
            <h1>🔍 SEO Analysis for {self.config.base_url}</h1>
            <p><strong>Date:</strong> {datetime.now()}</p>
            <div class="score">Score: {self.score:.1f}/100 - {self.rating}</div>

            <h2>📊 Executive Summary</h2>
            <p>Total URLs: {self.metrics['http']['total']}</p>

            <h3>Penalties</h3>
            <ul>
                {''.join(f'<li>{p}</li>' for p in self.penalties)}
            </ul>

            <h2>🔴 Broken Links</h2>
            <ul>
                {''.join(f"<li>{x['url']} ({x['status']})</li>" for x in self.metrics['http']['broken_links']) or '<li>None</li>'}
            </ul>

            <!-- More sections could be added here similar to MD -->

        </body>
        </html>
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ Report generated: {filename}")


class JSONReporter(SEOReporter):
    """Generates a JSON report."""

    def generate(self):
        filename = self.config.report_file

        # Convert NumPy types to native Python types for JSON serialization
        def convert_numpy(obj):
            if hasattr(obj, 'item'):
                return obj.item()
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_numpy(i) for i in obj]
            return obj

        data = {
            'metadata': {
                'date': str(datetime.now()),
                'base_url': self.config.base_url,
                'score': self.score,
                'rating': self.rating,
                'penalties': self.penalties
            },
            'metrics': convert_numpy(self.metrics)
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Report generated: {filename}")


class ReporterFactory:
    """Factory to create the appropriate reporter."""

    @staticmethod
    def create_reporter(config: SEOConfig, metrics, score, rating, penalties) -> SEOReporter:
        if config.output_format == 'html':
            return HTMLReporter(config, metrics, score, rating, penalties)
        elif config.output_format == 'json':
            return JSONReporter(config, metrics, score, rating, penalties)
        else:
            return MarkdownReporter(config, metrics, score, rating, penalties)
