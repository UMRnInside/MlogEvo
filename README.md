# MlogEvo
Compile C code to Mindustry logic, support C99 and some GNU extensions (mostly [GCC Extended ASM](https://gcc.gnu.org/onlinedocs/gcc/Extended-Asm.html)).

## Install
```bash
pip install mlogevo
```
...or install from GitHub: `pip install git+https://github.com/umrninside/mlogevo`

MlogEvo does not have *builtin* functions like [SuperStormer/c2logic](https://github.com/SuperStormer/c2logic), so it's recommended to install [MlogEvo Standard Library](https://github.com/UMRnInside/MlogEvo-stdlib)

## Usage
```bash
mlogevo --help
# Or...
python3 -m mlogevo --help
# or sometimes on Windows...
python -m mlogevo --help
```

NOTE: Python 3.7 or later is required. `cpp` (from GCC/Clang) is required for comments, macros and preprocessor directives.

If there is no `cpp`, you can still compile your source code by `python3 -m mlogevo -skip-preprocess`
