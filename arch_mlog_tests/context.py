import sys
import os
import unittest
import tempfile
from mlog_arithmetic_runner import MlogProcessor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
mlogevo = __import__("mlogevo")
mlogevo_main = __import__("mlogevo.__main__").__main__.main
module_abspath = os.path.abspath(os.path.dirname(__file__))
run_limit = 100000000


def parse_expected_results(filename: str) -> dict:
    # Structure
    # "variable_name" : (type, value)
    results = {}
    with open(filename) as f:
        for line in f:
            if not line.startswith(" * ") or " = " not in line:
                continue
            tokens = line.split()
            variable_type, variable_name = tokens[1:3]
            str_value = tokens[4]
            # TODO: more types, maybe?
            value = float(str_value) if variable_type in ("double", "float") else int(str_value)
            results[variable_name] = (variable_type, value)
    return results


# These tests can run in parallel
def compile_and_test(self:unittest.TestCase, source_filename: str, basic_argv: list):
    expected_results = parse_expected_results(source_filename)
    runner = MlogProcessor(memory_cells=8)
    try:
        fd, mlog_output_file = tempfile.mkstemp()
        argv = basic_argv + ["-o", mlog_output_file, source_filename]
        # TODO: compilation & emulation is done in main thread/process, consider moving it out
        mlogevo_main(argv)
        with os.fdopen(fd, "r") as f:
            runner.assemble_code(f.read())
            runner.run_with_limit(run_limit)
        for (variable, (vtype, value)) in expected_results.items():
            runner_result = runner.get_variable(variable)
            if vtype in ("double", "float"):
                self.assertAlmostEqual(
                    runner_result, value,
                    places=6,
                    msg=f"{source_filename}: value of `{variable}` should be `{value:.8f}`, got `{runner_result:.8f}` "
                        f"(difference {abs(runner_result-value):.8f} >= 1e-6) "
                )
            else:
                self.assertEqual(
                    runner_result, value,
                    msg=f"{source_filename}: value of `{variable}` should be `{value}`, got `{runner_result}`"
                )
    finally:
        os.remove(mlog_output_file)


def inject_class(target_class, basic_argv: list):
    sources_dir = os.path.join(module_abspath, "sources")
    for root, dirs, files in os.walk(sources_dir):
        for filename in files:
            src_abspath = os.path.abspath(os.path.join(root, filename))
            base = os.path.splitext(filename)[0]
            setattr(target_class, "test_" + base,
                    lambda self: compile_and_test(self, src_abspath, basic_argv)
            )