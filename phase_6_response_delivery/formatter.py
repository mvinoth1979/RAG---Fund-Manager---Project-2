import html
import re

class ResponseFormatter:
    def escape_html(self, text: str) -> str:
        return html.escape(text)
        
    def linkify_urls_to_markdown(self, text: str) -> str:
        # Convert raw URLs to markdown links so frontend can use react-markdown
        # This avoids dangerouslySetInnerHTML
        url_pattern = re.compile(r'(https?://\S+)')
        def replace(match):
            url = match.group(0)
            if url.endswith('.') or url.endswith(','):
                url = url[:-1]
                return f'[{url}]({url})' + match.group(0)[-1]
            return f'[{url}]({url})'
        return url_pattern.sub(replace, text)
        
    def get_disclaimer(self) -> str:
        return "Data sourced from Groww.in. I cannot provide investment advice."
        
    def format_payload(self, raw_text: str, source_url: str = None, last_updated: str = None) -> dict:
        escaped = self.escape_html(raw_text)
        linkified = self.linkify_urls_to_markdown(escaped)
        return {
            "text": linkified,
            "source_url": source_url,
            "last_updated": last_updated,
            "disclaimer": self.get_disclaimer()
        }
