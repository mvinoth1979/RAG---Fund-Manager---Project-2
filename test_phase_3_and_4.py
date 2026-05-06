import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (API keys)
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from phase_3_context_assembly.pipeline import ContextAssemblyPipeline
from phase_3_context_assembly.models import Chunk
from phase_4_response_generation.generator import ResponseGenerator

def run_integration_test():
    print("=" * 60)
    print("PHASE 3 -> PHASE 4 INTEGRATION TEST")
    print("=" * 60)
    
    # 1. Create a dummy whitelist
    whitelist = ["https://groww.in/mutual-funds/dummy-fund"]
    
    # 2. Create dummy ranked chunks (Output from Phase 2)
    ranked_chunks = [
        Chunk(
            chunk_id="chunk-1",
            doc_id="DOC-001",
            source_url="https://groww.in/mutual-funds/dummy-fund",
            chunk_type="expense_ratio",
            text="The expense ratio of the Dummy Fund is 0.50%."
        ),
        Chunk(
            chunk_id="chunk-2",
            doc_id="DOC-001",
            source_url="https://groww.in/mutual-funds/dummy-fund",
            chunk_type="nav",
            text="The NAV is currently 100 INR."
        ),
        Chunk(
            chunk_id="chunk-3", # Invalid URL to test whitelist filtering
            doc_id="DOC-002",
            source_url="https://bad-url.com",
            chunk_type="nav",
            text="Some bad data."
        )
    ]
    
    query = "What is the expense ratio and NAV of the Dummy Fund?"
    
    # 3. Run Phase 3: Context Assembly
    print(f"\n[PHASE 3] Starting context assembly for query: '{query}'")
    pipeline_p3 = ContextAssemblyPipeline(whitelist=whitelist, max_tokens=2000)
    context_string, source_url, doc_id = pipeline_p3.execute(ranked_chunks)
    
    print(f"[PHASE 3] Assembly Successful!")
    print(f"  -> Selected Source URL: {source_url}")
    print(f"  -> Selected Doc ID: {doc_id}")
    print(f"  -> Assembled Context: {context_string}")
    
    # 4. Run Phase 4: Response Generation
    print("\n[PHASE 4] Starting LLM Response Generation...")
    generator_p4 = ResponseGenerator()
    
    response = generator_p4.generate_response(context_string, query)
    
    print(f"\n[PHASE 4] Generation Complete!")
    print(f"  -> Status: {response.status}")
    print(f"  -> Provider Used: {response.provider_used}")
    print(f"  -> Prompt Hash: {response.prompt_hash}")
    print(f"  -> Text Response:\\n\\n{response.text}\\n")
    print("=" * 60)

if __name__ == "__main__":
    run_integration_test()
