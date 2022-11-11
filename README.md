# MlogEvo
Compile C code to Mindustry logic, support C99 and some GNU extensions (mostly [GCC Extended ASM](https://gcc.gnu.org/onlinedocs/gcc/Extended-Asm.html)).

## Install
`pip install mlogevo`

or install from Github: `pip install git+https://github.com/umrninside/mlogevo`

## Usage
`python3 -m mlogevo --help`

NOTE: Python 3.9 or later is required. `cpp` (from GCC/Clang) is required for comments, macros and preprocessor directives.

If there is no `cpp`, you can still compile your source code by `python3 -m mlogevo -skip-preprocess`
