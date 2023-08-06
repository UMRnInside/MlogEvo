from dataclasses import dataclass
from typing import Dict, List

from ..intermediate.function import Function
from ..intermediate import Quadruple


@dataclass
class FrontendResult:
    structures: Dict
    global_instructions: List[Quadruple]
    functions: Dict[str, Function]


class AbstractCompiler:
    def compile(self, filename: str, use_cpp=True, cpp_path="cpp", cpp_args=None) -> FrontendResult:
        pass