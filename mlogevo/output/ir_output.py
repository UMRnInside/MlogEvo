from ..intermediate import Quadruple
from typing import Iterable
from .abstract_ir_converter import AbstractIRConverter


class IRDumper(AbstractIRConverter):
    def convert(self, ir_list: Iterable[Quadruple]) -> str:
        results = []
        for ir in ir_list:
            results.append(ir.dump())
        return "\n".join(results)