import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

class HallucinationChecker:
    def check(self, response_text: str, source_context: str) -> Tuple[bool, List[str]]:
        """
        Extract numbers from response and verify they exist in the context.
        """
        violations = []
        
        # Extract numbers (e.g., 0.50, 100, 1.2%, etc.)
        numbers_in_response = set(re.findall(r'\b\d+(?:\.\d+)?\b', response_text))
        
        for num in numbers_in_response:
            if num not in source_context:
                violations.append(f"Untraceable number claim: '{num}'")
                
        is_faithful = len(violations) == 0
        return is_faithful, violations
