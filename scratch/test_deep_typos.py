import importlib.util
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv()

def _load_module(module_path: Path):
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

normalizer_mod = _load_module(PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.1_query_normalization" / "normalizer.py")
QueryNormalizer = normalizer_mod.QueryNormalizer

def test_deep_typos():
    normalizer = QueryNormalizer()
    
    test_cases = [
        "What is the min syp amount?",
        "sysmatic plan for smal cap",
        "ext lode of liquid fund",
        "who manages the ethical scheme",
        "how big is the flexicap fund",
        "nva for gold etf"
    ]
    
    print("Testing DEEP LLM Fuzzy Typo Correction")
    print("=" * 60)
    
    for query in test_cases:
        print(f"Original:  {query}")
        result = normalizer.normalize(query)
        print(f"Corrected: {result.normalized}")
        print("-" * 60)

if __name__ == "__main__":
    test_deep_typos()
