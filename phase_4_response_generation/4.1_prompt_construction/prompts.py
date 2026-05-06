import hashlib
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a fact extraction engine. Use ONLY the provided context. Do not analyze, compare, recommend, or evaluate. If the answer is not in the context, respond ONLY with: 'I do not have that information in my current sources.' Answer in 1-3 sentences."

class PromptBuilder:
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT
        
    def build(self, context: str, query: str) -> dict:
        prompt_string = f"Context:\n{context}\n\nQuery:\n{query}"
        
        # Calculate prompt hash
        combined = self.system_prompt + prompt_string
        prompt_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        
        logger.info(f"Generated prompt with hash: {prompt_hash}")
        
        return {
            "system": self.system_prompt,
            "user": prompt_string,
            "hash": prompt_hash
        }
