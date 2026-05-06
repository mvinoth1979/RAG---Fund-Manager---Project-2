from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    text: str
    source_url: Optional[str]
    last_updated: Optional[str]
    disclaimer: str
