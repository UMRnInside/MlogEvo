import argparse
import sys

from .frontend import Compiler
from .backend import make_backend

parser = argparse.ArgumentParser()
parser.add_argument("source_file", type=str, nargs='?', default='')
parser.add_argument("--output", "-o", type=str, nargs='?', default="a.mlog.txt")

# Machine-dependant, arch & target(output format)
parser.add_argument("-march", type=str, choices=("mlog", ), default="mlog" )
parser.add_argument("-mtarget", type=str, choices=("mlog", ), default="mlog" )

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    #print(args)
    if not args.source_file:
        parser.print_help()
        return

    # TODO: choose compiler by -march
    frontend = Compiler()
    backend = make_backend(
        arch=args.march,
        target=args.mtarget
    )
    result = backend.compile(frontend.compile(args.source_file))
    if args.output == '-':
        print(result)
        return
    with open(args.output, "w") as f:
        f.write(result)

if __name__ == '__main__':
    main()
