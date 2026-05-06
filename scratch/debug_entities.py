import sys
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def load_entities():
    path = PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.2_entity_resolution" / "entities.py"
    spec = importlib.util.spec_from_file_location("entities", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

entities = load_entities()
q = "Minimum SIP for Multi Asset Allocation Fund"
res = entities.run_entity_resolver(q, q.lower())
print(f"Query: {q}")
print(f"Funds: {res.mentioned_funds}")
print(f"Fact: {res.fact_type}")
