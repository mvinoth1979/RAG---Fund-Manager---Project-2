import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class SentenceValidator:
    def __init__(self, max_sentences: int = 3):
        self.max_sentences = max_sentences
        
    def _split_sentences(self, text: str) -> list[str]:
        # Simple sentence tokenizer protecting basic abbreviations
        text = re.sub(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', '\n', text)
        sentences = [s.strip() for s in text.split('\n') if s.strip()]
        return sentences
        
    def validate_and_truncate(self, response_text: str) -> Tuple[str, bool]:
        """
        Returns (validated_text, was_truncated)
        """
        sentences = self._split_sentences(response_text)
        if len(sentences) > self.max_sentences:
            logger.warning(f"Response exceeded {self.max_sentences} sentences. Truncating.")
            truncated_text = " ".join(sentences[:self.max_sentences])
            return truncated_text, True
            
        return response_text, False
