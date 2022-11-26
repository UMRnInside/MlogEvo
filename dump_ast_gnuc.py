#-----------------------------------------------------------------
# pycparser: dump_ast.py
#
# Basic example of parsing a file and dumping its parsed AST.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------
from __future__ import print_function
import argparse
import sys

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file
from pycparserext_gnuc.ext_c_parser import GnuCParser

if __name__ == "__main__":
    argparser = argparse.ArgumentParser('Dump AST')
    argparser.add_argument('filename', help='name of file to parse')
    argparser.add_argument('--coord', help='show coordinates in the dump',
                           action='store_true')
    args = argparser.parse_args()

    ast = parse_file(args.filename, use_cpp=True, parser=GnuCParser())
    ast.show(showcoord=args.coord)
    # print(ast.ext[0].decl.quals)
    # print(ast.ext[0].decl.funcspec)
