from pydantic import BaseModel
from typing import Optional, List

class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    source_url: str
    chunk_type: str
    text: str
    embedding: Optional[List[float]] = None
