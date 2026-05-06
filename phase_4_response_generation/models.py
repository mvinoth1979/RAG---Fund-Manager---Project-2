from pydantic import BaseModel
from typing import Optional, Literal

class Phase4Response(BaseModel):
    status: Literal["SUCCESS", "T3_UNKNOWN", "T4_ERROR"]
    text: str
    provider_used: Optional[str] = None
    prompt_hash: Optional[str] = None
