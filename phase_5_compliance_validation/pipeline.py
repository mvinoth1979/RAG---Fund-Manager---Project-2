import sys
from pathlib import Path
import logging
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "phase_5_compliance_validation" / "5.1_advisory_detection"))
sys.path.append(str(PROJECT_ROOT / "phase_5_compliance_validation" / "5.2_hallucination_check"))
sys.path.append(str(PROJECT_ROOT / "phase_5_compliance_validation" / "5.3_sentence_validation"))
sys.path.append(str(PROJECT_ROOT / "phase_5_compliance_validation" / "5.4_citation_footer"))

from phase_5_compliance_validation.models import ComplianceResult
from advisory_detection import AdvisoryDetector
from hallucination_check import HallucinationChecker
from sentence_validation import SentenceValidator
from citation_footer import CitationFooterAppender

logger = logging.getLogger(__name__)

class CompliancePipeline:
    def __init__(self, banned_phrases_path: str, max_sentences: int = 3):
        self.advisory_detector = AdvisoryDetector(banned_phrases_path)
        self.hallucination_checker = HallucinationChecker()
        self.sentence_validator = SentenceValidator(max_sentences)
        self.citation_appender = CitationFooterAppender()
        
    def validate(self, raw_response: str, source_context: str, source_url: Optional[str]) -> ComplianceResult:
        is_clean, adv_violations = self.advisory_detector.check(raw_response)
        if not is_clean:
            logger.error(f"P1 VIOLATION: Advisory content detected. {adv_violations}")
            refusal_text = "I cannot provide investment advice or recommendations.\n\nYou can learn more about mutual fund basics here:\nhttps://www.amfiindia.com/investor-corner/knowledge-center.html"
            final_text = self.citation_appender.append(refusal_text, None)
            return ComplianceResult(status="REJECTED", response=final_text, violations=adv_violations, fallback_used="T2_REFUSAL")
            
        is_faithful, hal_violations = self.hallucination_checker.check(raw_response, source_context)
        if not is_faithful:
            logger.error(f"P3 VIOLATION: Hallucination detected. {hal_violations}")
            unknown_text = "I do not have that information in my current sources."
            final_text = self.citation_appender.append(unknown_text, None)
            return ComplianceResult(status="REJECTED", response=final_text, violations=hal_violations, fallback_used="T3_UNKNOWN")
            
        validated_text, was_truncated = self.sentence_validator.validate_and_truncate(raw_response)
        
        # Suppress citation for refusal or unknown responses
        refusal_phrases = [
            "i do not have that information", 
            "i cannot provide", 
            "i'm unable to answer",
            "i do not have information"
        ]
        final_source_url = source_url
        if any(phrase in validated_text.lower() for phrase in refusal_phrases):
            final_source_url = None
            
        final_text = self.citation_appender.append(validated_text, final_source_url)
        
        violations = []
        if was_truncated:
            violations.append("C1 VIOLATION: Response exceeded sentence limit and was truncated.")
            
        return ComplianceResult(status="APPROVED", response=final_text, violations=violations, fallback_used=None)
