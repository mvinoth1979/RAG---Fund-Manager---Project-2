import json
import logging
from pathlib import Path
from typing import Tuple, List

logger = logging.getLogger(__name__)

class AdvisoryDetector:
    def __init__(self, banned_phrases_path: str):
        self.banned_phrases = []
        path = Path(banned_phrases_path)
        if path.exists():
            with open(path, 'r') as f:
                categories = json.load(f)
                for phrases in categories.values():
                    self.banned_phrases.extend([p.lower() for p in phrases])
        else:
            logger.warning(f"Banned phrases file not found at {banned_phrases_path}. Using empty list.")
            
    def check(self, response_text: str) -> Tuple[bool, List[str]]:
        """
        Returns (is_clean, violations)
        """
        violations = []
        text_lower = response_text.lower()
        for phrase in self.banned_phrases:
            if phrase in text_lower:
                violations.append(f"Advisory phrase detected: '{phrase}'")
                
        is_clean = len(violations) == 0
        return is_clean, violations
