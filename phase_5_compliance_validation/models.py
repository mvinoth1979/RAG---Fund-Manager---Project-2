from pydantic import BaseModel
from typing import Literal, List, Optional

class ComplianceResult(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    response: str
    violations: List[str]
    fallback_used: Optional[str] = None
