import argparse
import sys

from .frontend import Compiler
from .backend import make_backend

parser = argparse.ArgumentParser(prog="mlogevo")
parser.add_argument("source_file", type=str, nargs='?', default='')
parser.add_argument("-o", type=str, nargs='?', default="a.mlog.txt",
        help="output file, '-' for stdout", dest="output")

parser.add_argument("-D", type=str, action="append",
        help="macros")
parser.add_argument("-I", type=str, action="append",
        help="include directories")

# Machine-dependant, arch & target(output format)
parser.add_argument("-march", type=str, choices=("mlog", ), default="mlog",
        help="target architecture")
parser.add_argument("-mtarget", type=str, choices=("mlog", ), default="mlog",
        help="output format, default mlog")

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    #print(args)
    if not args.source_file:
        parser.print_help()
        return

    cpp_args = []
    if args.I:
        cpp_args.extend( ["-I"+path for path in args.I ] )
    if args.D:
        cpp_args.extend( ["-D"+path for path in args.D ] )
    # TODO: choose compiler by -march
    frontend = Compiler()
    backend = make_backend(
        arch=args.march,
        target=args.mtarget
    )
    result = backend.compile(
        frontend.compile(
            args.source_file,
            use_cpp=True,
            cpp_args=cpp_args)
    )
    if args.output == '-':
        print(result)
        return
    with open(args.output, "w") as f:
        f.write(result)

if __name__ == '__main__':
    main()
