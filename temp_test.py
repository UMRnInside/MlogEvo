from mlogevo.frontend.compiler import Compiler
c = Compiler()
res = c.compile("/tmp/test.c")
for ir in res:
    print(ir.dump())
