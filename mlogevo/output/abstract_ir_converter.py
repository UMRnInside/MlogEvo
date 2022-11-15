from ..intermediate import Quadruple
from typing import Iterable


class AbstractIRConverter:
    def convert(self, ir_list: Iterable[Quadruple]) -> str:
        return ""
