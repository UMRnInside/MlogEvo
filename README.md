# MlogEvo
Compile C code to Mindustry logic, support C99 and some GNU extensions (mostly [GCC Extended ASM](https://gcc.gnu.org/onlinedocs/gcc/Extended-Asm.html)).

## Install
```bash
pip install mlogevo
```
...or install from GitHub: `pip install git+https://github.com/umrninside/mlogevo`

MlogEvo does not have *builtin* functions like [SuperStormer/C2Logic](https://github.com/SuperStormer/c2logic), so it's recommended to install [MlogEvo Standard Library](https://github.com/UMRnInside/MlogEvo-stdlib)

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

## Features and limitations
MlogEvo is a C-based DSL, thus support mose of the C99 features, except:
  * `switch-case`
  * `enum`
  * actual pointers, arrays and structures (not in `mlog` architecture at least)
  * only `int` and `double` variables are supported

### Convenient `print()` function
The builtin `print` function can take multiple arguments as input. Remember to `print_flush(message1)`.
```C
#include <mlogevo/io.h>
extern struct MlogObject message1;
void main() {
    print("The ultimate answer is ", 42, "\n");
    print("62 * 1847 = ", 62*1847, "\n");
    print_flush(message1);
}
```

### Sensible Mlog Objects
In `mlog` arch, there is a `struct MlogObject` representing `Object` in Mlog. Unlike normal C structure, this is READONLY.
Every sensible attribute is considered as a "structure" member.

**NOTE:** 
  * This requires mlogEvo-stdlib.
  * The hyphens (`-`) in attribute names are replaced by underscores (`_`, e.g. `container1.blast_compound`)
```C
#include <mlogevo/mlog_object.h>
#include <mlogevo/io.h>
// extern is preferred
extern struct MlogObject message1;
void main() {
    print("x=", message1.x, ", y=", message1.y, "\n");
    print_flush(message1);
}
```

### Access to Mlog Builtin Constants
[Mindustry Wiki: Variables and Constants](https://mindustrygame.github.io/wiki/logic/3-variables/)

**NOTE:** 
  * This requires mlogEvo-stdlib.
  * The building (type) `switch` is named after `Switch` (capitalized). 
  * The hyphens (`-`) in attribute names are replaced by underscores

```C
#include <mlogevo/mlog_object.h>
#include <mlogevo/mlog_builtins.h>
extern struct MlogObject message1;
extern struct MlogObject switch1;
void main() {
    print(switch1.type == builtins.Switch);
    print_flush(message1);
}
```

### GCC Extended Asm Template (not basic ones)
This allows you to write Mlog assembly code, and make them work with the C part.
Asm Template can be `volatile`-qualified, so they won't break in further optimizations.

Do not use `asm goto`, use `asm volatile` instead.

See also [Extended Asm](https://gcc.gnu.org/onlinedocs/gcc-12.2.0/gcc/Extended-Asm.html)
```C
void main() {
    int result;
    int x = 1, y = 2;
    __asm__ volatile (
        "ubind @mono"
    );
    __asm__ (
        "op max %0 %1 %2\n"
        : "=r" (result)
        : "r" (x), "r" (y)
    );
}
```

### Local Common Subexpression Elimination (or LVN)
This is a trivial and conservative optimization.

```C
int x1 = 3, x2 = 0, y1 = 0, y2 = 4;
int r2;
void main() {
    r2 = (x1-x2) * (x1-x2) + (y1-y2) * (y1-y2);
}
```
Without LCSE (`-fno-lcse`):
```
set x1 3
set x2 0
set y1 0
set y2 4
op sub ___vtmp_1@main x1 x2
op sub ___vtmp_2@main x1 x2
op mul ___vtmp_3@main ___vtmp_1@main ___vtmp_2@main
op sub ___vtmp_4@main y1 y2
op sub ___vtmp_5@main y1 y2
op mul ___vtmp_6@main ___vtmp_4@main ___vtmp_5@main
op add r2 ___vtmp_3@main ___vtmp_6@main
end
```
With default `-O1`:
```
set x1 3
set x2 0
set y1 0
set y2 4
op sub ___vtmp_1@main x1 x2
op sub ___vtmp_4@main y1 y2
op mul ___vtmp_3@main ___vtmp_1@main ___vtmp_1@main
op mul ___vtmp_6@main ___vtmp_4@main ___vtmp_4@main
op add r2 ___vtmp_3@main ___vtmp_6@main
end
```