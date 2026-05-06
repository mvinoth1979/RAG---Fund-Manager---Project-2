import sys
from pathlib import Path
import logging
from typing import Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "phase_3_context_assembly" / "3.1_whitelist_validation"))
sys.path.append(str(PROJECT_ROOT / "phase_3_context_assembly" / "3.2_single_source_selection"))
sys.path.append(str(PROJECT_ROOT / "phase_3_context_assembly" / "3.3_context_block_assembly"))

from phase_3_context_assembly.models import Chunk
from validator import WhitelistValidator
from selector import SingleSourceSelector
from assembler import ContextBlockAssembler

class ContextAssemblyPipeline:
    def __init__(self, whitelist: list[str], max_tokens: int = 2000):
        self.validator = WhitelistValidator(whitelist)
        self.selector = SingleSourceSelector()
        self.assembler = ContextBlockAssembler(max_tokens)
        
    def execute(self, ranked_chunks: list[Chunk]) -> Tuple[str, Optional[str], Optional[str]]:
        validated = self.validator.validate(ranked_chunks)
        single_source = self.selector.select(validated)
        return self.assembler.assemble(single_source)
