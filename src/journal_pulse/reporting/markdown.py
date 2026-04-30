from collections import defaultdict

from journal_pulse.models import DailyDigest


class MarkdownReporter:
    def render(self, digest: DailyDigest) -> str:
        grouped = defaultdict(list)
        for article in digest.articles:
            grouped[article.source].append(article)

        lines = [
            '# Daily Journal Digest',
            '',
            f'- Generated at: {digest.generated_at.isoformat()}',
            f'- Total articles: {len(digest.articles)}',
            '',
        ]

        for source in sorted(grouped):
            lines.append(f'## {source}')
            lines.append('')
            for article in grouped[source]:
                lines.append(f'- **{article.title}**')
                lines.append(f'  - URL: {article.url}')
                lines.append(f'  - Published: {article.published_at.isoformat()}')
                lines.append(f'  - Summary: {article.summary or article.abstract or "No summary yet."}')
                lines.append('')

        return '\n'.join(lines).strip() + '\n'
