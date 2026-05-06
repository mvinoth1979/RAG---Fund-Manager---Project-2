import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv()

import importlib.util

def _load_module(module_path: Path):
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

normalizer_mod = _load_module(PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.1_query_normalization" / "normalizer.py")
QueryNormalizer = normalizer_mod.QueryNormalizer

def test_typo_correction():
    normalizer = QueryNormalizer()
    
    test_cases = [
        "NVA of the Smal Cap Fund",
        "What is the NSV of Ethical Fund?",
        "Min SIP for Flexicp",
        "Expnse ratio of Liquid"
    ]
    
    print("Testing LLM Fuzzy Typo Correction")
    print("=" * 50)
    
    for query in test_cases:
        print(f"Original:  {query}")
        result = normalizer.normalize(query)
        print(f"Corrected: {result.normalized}")
        print(f"Changes:   {result.transformations}")
        print("-" * 50)

if __name__ == "__main__":
    test_typo_correction()
