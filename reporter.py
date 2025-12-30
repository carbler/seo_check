from datetime import datetime
from config import BASE_URL

def generate_report(metrics, score, rating, penalties, filename):

    http = metrics['http']
    h1 = metrics['h1']
    titles = metrics['title']
    meta = metrics['meta']
    canonical = metrics['canonical']
    images = metrics['images']
    links = metrics['links']
    security = metrics['security']
    others = metrics['others']

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# 🔍 TuWorker.com - Technical SEO Analysis\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Base URL**: {BASE_URL}  \n")
        f.write(f"**Pages Analyzed**: {http['total']}\n\n")
        f.write(f"---\n\n")

        f.write(f"## 📊 Executive Summary\n\n")
        f.write(f"**SEO SCORE: {score:.1f}/100 - {rating}**\n\n")

        f.write("### Key Metrics\n")
        f.write("| Metric | Value | Status |\n")
        f.write("|--------|-------|--------|\n")
        f.write(f"| Total URLs | {http['total']} | - |\n")
        f.write(f"| OK Pages (200) | {http.get('stats', {}).get(200, 0)} | {'✅' if http['error_rate_4xx'] < 5 else '⚠️'} |\n")
        f.write(f"| Broken Links (4xx) | {len(http['broken_links'])} | {'✅' if http['error_rate_4xx'] < 5 else '❌'} {http['error_rate_4xx']:.1f}% |\n")
        f.write(f"| With H1 | {h1['total'] - len(h1['no_h1'])} | {100-h1['missing_pct']:.1f}% |\n")
        f.write(f"| With Title | {titles['total'] - len(titles['no_title'])} | {100-titles['missing_pct']:.1f}% |\n")
        f.write(f"| With Meta Desc | {meta['total'] - len(meta['no_meta'])} | {100-meta['missing_pct']:.1f}% |\n")
        f.write(f"| Images w/ Alt | {images['total_images'] - images['missing_alt_count']} | {100-images['missing_pct']:.1f}% |\n")
        f.write(f"| Secure (HTTPS) | {len(security['non_https'])} non-https | {security['secure_pct']:.1f}% |\n\n")

        f.write("### Score Penalties\n")
        for p in penalties:
            f.write(f"- {p}\n")
        f.write("\n---\n\n")

        f.write("## 🔴 Broken Links (4xx)\n")
        if http['broken_links']:
            for link in http['broken_links']:
                f.write(f"- {link['url']} ({link['status']})\n")
        else:
            f.write("None detected ✅\n")
        f.write("\n")

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

        f.write("## 📄 Title Tags\n")
        f.write(f"- Pages without Title: {len(titles['no_title'])}\n")
        f.write(f"- Too Short (<30): {len(titles['short'])}\n")
        f.write(f"- Too Long (>60): {len(titles['long'])}\n")
        f.write(f"- Duplicate Title Groups: {len(titles['duplicates'])}\n")

        if titles['no_title']:
            f.write("\n**Pages without Title:**\n")
            for url in titles['no_title']:
                f.write(f"- {url}\n")

        if titles['duplicates']:
            f.write("\n**Duplicate Title Groups:**\n")
            for title_text, urls in titles['duplicates'].items():
                f.write(f"\n**\"{title_text}\"** used on:\n")
                for url in urls:
                    f.write(f"- {url}\n")

        if titles['short']:
            f.write("\n**Titles Too Short (<30 chars):**\n")
            for url in titles['short']:
                f.write(f"- {url}\n")

        if titles['long']:
             f.write("\n**Titles Too Long (>60 chars):**\n")
             for url in titles['long']:
                 f.write(f"- {url}\n")
        f.write("\n")

        f.write("## 📝 Meta Descriptions\n")
        f.write(f"- Missing: {len(meta['no_meta'])}\n")
        f.write(f"- Too Short (<120): {len(meta['short'])}\n")
        f.write(f"- Too Long (>160): {len(meta['long'])}\n")
        f.write(f"- Duplicate Meta Groups: {len(meta['duplicates'])}\n")

        if meta['no_meta']:
            f.write("\n**Pages without Meta Description:**\n")
            for url in meta['no_meta']:
                f.write(f"- {url}\n")

        if meta['duplicates']:
            f.write("\n**Duplicate Meta Description Groups:**\n")
            for meta_text, urls in meta['duplicates'].items():
                # Truncate long meta description for display title
                display_text = (meta_text[:75] + '...') if len(meta_text) > 75 else meta_text
                f.write(f"\n**\"{display_text}\"** used on:\n")
                for url in urls:
                    f.write(f"- {url}\n")

        if meta['short']:
            f.write("\n**Meta Descriptions Too Short (<120 chars):**\n")
            for url in meta['short']:
                f.write(f"- {url}\n")

        if meta['long']:
            f.write("\n**Meta Descriptions Too Long (>160 chars):**\n")
            for url in meta['long']:
                f.write(f"- {url}\n")
        f.write("\n")

        f.write("## 🔗 Links Structure\n")
        f.write(f"- Internal Links: {links['internal']}\n")
        f.write(f"- External Links: {links['external']}\n")
        f.write(f"- Internal/External Ratio: {links['ratio']:.2f}\n")
        f.write("\n")

        f.write("## 🔒 Security\n")
        f.write(f"- Non-HTTPS Pages: {len(security['non_https'])}\n")
        if security['non_https']:
             f.write("\n**Non-HTTPS Pages:**\n")
             for url in security['non_https']:
                 f.write(f"- {url}\n")
        f.write("\n")

        f.write("## 🔄 Canonical Tags\n")
        f.write(f"- Missing: {len(canonical['no_canonical'])}\n")
        f.write(f"- Canonical points to different URL: {len(canonical['diff'])}\n")

        if canonical['no_canonical']:
            f.write("\n**Pages without Canonical Tag:**\n")
            for url in canonical['no_canonical']:
                f.write(f"- {url}\n")

        if canonical['diff']:
            f.write("\n**Canonical points to different URL:**\n")
            for item in canonical['diff']:
                f.write(f"- {item['url']} -> {item['canonical']}\n")
        f.write("\n")

        f.write("## 🖼️ Images\n")
        f.write(f"- Total Images Analyzed: {images['total_images']}\n")
        f.write(f"- Missing Alt Text: {images['missing_alt_count']} ({images['missing_pct']:.1f}%)\n")
        if images['missing_alt_details']:
            f.write("\n**Pages with missing Alt Text:**\n")
            for item in images['missing_alt_details']:
                f.write(f"- {item['url']} ({item['count']} images)\n")
        f.write("\n")

        f.write("## ⚡ Performance & Other\n")
        f.write(f"- Average Response Time: {others['performance']['avg_time']:.2f}s\n")
        f.write(f"- Slow Pages (>3s): {len(others['performance']['slow_pages'])}\n")
        f.write(f"- Pages with Schema: {others['schema']['present']}\n")
        f.write(f"- Pages with OG Image: {others['og']['image']}\n")

        if others['performance']['slow_pages']:
            f.write("\n**Slow Pages (>3s):**\n")
            for url in others['performance']['slow_pages']:
                f.write(f"- {url}\n")

    print(f"✓ Report generated: {filename}")
