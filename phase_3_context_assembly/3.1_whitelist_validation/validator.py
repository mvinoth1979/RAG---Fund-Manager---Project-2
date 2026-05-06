import logging
from typing import List
from phase_3_context_assembly.models import Chunk

logger = logging.getLogger(__name__)

class WhitelistValidator:
    def __init__(self, whitelist: List[str]):
        self.whitelist = set(whitelist)
        
    def validate(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        3.1 Source Whitelist Validation
        Verify every chunk's source_url is in whitelist.
        Enforcement: Any invalid chunk -> discard + log security event.
        """
        valid_chunks = []
        for chunk in chunks:
            if chunk.source_url in self.whitelist:
                valid_chunks.append(chunk)
            else:
                logger.warning(f"SECURITY EVENT: Invalid chunk discarded. source_url '{chunk.source_url}' not in whitelist. Chunk ID: {chunk.chunk_id}")
        return valid_chunks
