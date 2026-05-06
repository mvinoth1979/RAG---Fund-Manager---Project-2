import re
from typing import List, Literal
from pydantic import BaseModel

class IntentResult(BaseModel):
    classification: Literal["FACTUAL", "ADVISORY", "UNCLEAR"]
    advisory_score: float
    triggers_matched: List[str] = []

class IntentClassifier:
    ADVISORY_TRIGGERS = [
        r"\bshould\b",
        r"\bbetter\b",
        r"\bbest\b",
        r"\brecommend\b",
        r"\bsafe\b",
        r"\boutperform\b",
        r"invest now",
        r"\bbuy\b",
        r"\bsell\b",
    ]

    FACTUAL_TRIGGERS = [
        r"\bwhat is\b",
        r"\bhow much\b",
        r"\btell me\b",
        r"\bdetails\b",
        r"expense ratio",
        r"exit load",
        r"minimum sip",
        r"min sip",
        r"minimum lumpsum",
        r"min lumpsum",
        r"benchmark",
        r"riskometer",
        r"risk level",
        r"nav",
        r"aum",
        r"asset under management",
        r"fund manager",
        r"inception date",
        r"launch date",
        r"category",
        r"tax",
        r"taxation",
        r"holdings",
        r"portfolio",
        r"investment objective",
        r"objective",
        r"fund size",
        r"total aum",
    ]

    def classify(self, query: str) -> IntentResult:
        query_lower = query.lower()

        advisory_hits = 0
        matched_triggers: List[str] = []

        for pattern in self.ADVISORY_TRIGGERS:
            if re.search(pattern, query_lower):
                advisory_hits += 1
                matched_triggers.append(f"ADV:{pattern}")

        factual_hits = 0
        for pattern in self.FACTUAL_TRIGGERS:
            if re.search(pattern, query_lower):
                factual_hits += 1
                matched_triggers.append(f"FACT:{pattern}")

        total_hits = advisory_hits + factual_hits

        if total_hits == 0:
            return IntentResult(
                classification="UNCLEAR",
                advisory_score=0.0,
                triggers_matched=[],
            )

        advisory_score = advisory_hits / total_hits

        if advisory_score >= 0.5:
            classification = "ADVISORY"
        else:
            classification = "FACTUAL"

        return IntentResult(
            classification=classification,
            advisory_score=round(advisory_score, 3),
            triggers_matched=matched_triggers,
        )

if __name__ == "__main__":
    ic = IntentClassifier()
    q = "Who is the fund manager for Flexi Cap Fund?"
    res = ic.classify(q)
    print(f"Query: {q}")
    print(f"Classification: {res.classification}")
    print(f"Triggers: {res.triggers_matched}")
