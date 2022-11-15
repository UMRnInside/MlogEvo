import argparse
import sys

from .frontend import Compiler
from .backend import make_backend

parser = argparse.ArgumentParser(prog="mlogevo")
parser.add_argument("source_file", type=str, nargs='?', default='')
parser.add_argument("-o", type=str, nargs='?', default="a.mlog.txt",
        help="output file, '-' for stdout", dest="output")

parser.add_argument("-O", type=int, choices=range(0, 4), default=1,
        help="optimize level, default 1")
parser.add_argument("-D", type=str, action="append",
        help="macros")
parser.add_argument("-I", type=str, action="append",
        help="include directories")
parser.add_argument("-m", type=str, action="append",
        help="machine dependent options")
parser.add_argument("-f", type=str, action="append",
        help="machine independent options")
parser.add_argument("-print-basic-blocks", action="store_true",
        help="dump basic blocks")
parser.add_argument("-skip-preprocess", action="store_false",
        help="do not invoke `cpp` or `gcc -E`")

# Machine-dependant, arch & target(output format)
parser.add_argument("-march", type=str, choices=("mlog", ), default="mlog",
        help="target architecture")
parser.add_argument("-mtarget", type=str, choices=("mlog", "mlogev_ir"), default="mlog",
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
        target=args.mtarget,
        machine_dependents=args.m or [],
        machine_independents=args.f or [],
        optimize_level=args.O,
    )

    frontend_result = frontend.compile(
            args.source_file,
            use_cpp=args.skip_preprocess,
            cpp_args=cpp_args
    )
    result = backend.compile(frontend_result, dump_blocks=args.print_basic_blocks)
    if args.output == '-':
        print(result)
        return
    with open(args.output, "w") as f:
        f.write(result)

if __name__ == '__main__':
    main()
