from typing import List, Tuple, Optional
from phase_3_context_assembly.models import Chunk

class ContextBlockAssembler:
    DOC_ID_TO_NAME = {
        "DOC-001": "The Wealth Company Small Cap Fund",
        "DOC-002": "The Wealth Company Ethical Fund",
        "DOC-003": "The Wealth Company Multi Asset Allocation Fund",
        "DOC-004": "The Wealth Company Flexi Cap Fund",
        "DOC-005": "The Wealth Company Gold ETF FoF",
        "DOC-006": "The Wealth Company Liquid Fund",
        "DOC-007": "The Wealth Company Arbitrage Fund",
    }

    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        
    def assemble(self, chunks: List[Chunk]) -> Tuple[str, Optional[str], Optional[str]]:
        """
        3.3 Context Block Assembly
        Concatenate up to 2000 tokens; truncate at last full sentence.
        Enforcement: Context must be non-empty; source_url must be non-null.
        Returns:
            Tuple[str, Optional[str], Optional[str]]: (context_string, source_url, doc_id)
        """
        if not chunks:
            return "", None, None
            
        source_url = chunks[0].source_url
        doc_id = chunks[0].doc_id
        
        if not source_url:
            return "", None, None
            
        fund_name = self.DOC_ID_TO_NAME.get(doc_id, "this mutual fund")
        context_string = f"Information for {fund_name}:\n"
        
        # Approximate current tokens (start with words in header)
        current_tokens = len(context_string.split())
        
        for chunk in chunks:
            # Simple estimation for tokens (1 word ~ 1 token approximation)
            chunk_words = chunk.text.split()
            
            if current_tokens + len(chunk_words) > self.max_tokens:
                # Truncate
                remaining = self.max_tokens - current_tokens
                if remaining <= 0:
                    break
                    
                allowed_text = " ".join(chunk_words[:remaining])
                
                # Truncate at last full sentence
                last_period = max(allowed_text.rfind('.'), allowed_text.rfind('!'), allowed_text.rfind('?'))
                if last_period != -1:
                    allowed_text = allowed_text[:last_period + 1]
                    
                context_string += allowed_text + " "
                break
            else:
                context_string += chunk.text + " "
                current_tokens += len(chunk_words)
                
        context_string = context_string.strip()
        
        if not context_string or context_string == f"Information for {fund_name}:":
            return "", None, None
            
        return context_string, source_url, doc_id
