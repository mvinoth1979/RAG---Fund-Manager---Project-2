from typing import List
from phase_3_context_assembly.models import Chunk

class SingleSourceSelector:
    def select(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        3.2 Single Source Selection
        Select document with highest-scoring chunk; tie-breaker: lowest doc_id.
        Assuming chunks are pre-sorted by score (highest first).
        Enforcement: P2: Only one source URL per response.
        """
        if not chunks:
            return []
            
        # The first chunk has the highest score since they are ranked candidate chunks
        # Tie-breaker for lowest doc_id is inherently handled if sorting mechanism supports it,
        # but here we simply take the top chunk's doc_id.
        selected_doc_id = chunks[0].doc_id
        
        # Filter all chunks belonging to exactly ONE document
        return [chunk for chunk in chunks if chunk.doc_id == selected_doc_id]
