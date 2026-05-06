import datetime
from typing import Optional

class CitationFooterAppender:
    def append(self, response_text: str, source_url: Optional[str]) -> str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        url_to_display = source_url if source_url else "N/A"
        footer = f"\n\nSource: {url_to_display}\nLast updated from sources: {date_str}"
        return response_text.strip() + footer
