import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from context import inject_class

mlogevo_arg = "-march=mlog -mtarget=mlog"
mlogevo_basic_argv = mlogevo_arg.split()
mlogevo_opt1_argv = mlogevo_basic_argv + ["-O1", ]
mlogevo_opt2_argv = mlogevo_basic_argv + ["-O2", ]


class AutogeneratedOptLevel0Test(unittest.TestCase):
    pass


class AutogeneratedOptLevel1Test(unittest.TestCase):
    """\
This class is intentionally left empty.
Don't worry, we will "inject" test cases later.
    """
    pass


inject_class(AutogeneratedOptLevel0Test, mlogevo_basic_argv + ["-O0", ])
inject_class(AutogeneratedOptLevel1Test, mlogevo_opt1_argv)

if __name__ == "__main__":
    unittest.main()
