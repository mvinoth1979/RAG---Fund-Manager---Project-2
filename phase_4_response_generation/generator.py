import sys
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "phase_4_response_generation" / "4.1_prompt_construction"))
sys.path.append(str(PROJECT_ROOT / "phase_4_response_generation" / "4.2_llm_inference"))

from phase_4_response_generation.models import Phase4Response
from prompts import PromptBuilder
from llm import LLMClient

logger = logging.getLogger(__name__)

class ResponseGenerator:
    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()
        
    def generate_response(self, context: str, query: str) -> Phase4Response:
        if not context.strip():
            logger.warning("Empty context provided. Returning T3.")
            return Phase4Response(status="T3_UNKNOWN", text="I do not have that information in my current sources.")
            
        try:
            prompt_data = self.prompt_builder.build(context, query)
            response_text, provider = self.llm_client.generate(prompt_data["system"], prompt_data["user"])
            
            if not response_text or not response_text.strip():
                logger.warning("Empty response from LLM. Returning T3.")
                return Phase4Response(status="T3_UNKNOWN", text="I do not have that information in my current sources.", provider_used=provider, prompt_hash=prompt_data["hash"])
                
            return Phase4Response(status="SUCCESS", text=response_text.strip(), provider_used=provider, prompt_hash=prompt_data["hash"])
            
        except Exception as e:
            logger.error(f"Phase 4 Generation Error: {e}")
            return Phase4Response(status="T4_ERROR", text="I'm unable to answer right now. Please try again later.")
