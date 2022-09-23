# MlogEvo Mindustry Logic Calling Convention

Special thanks to [SuperStormer/c2logic](https://github.com/SuperStormer/c2logic), [UMRnInside/MlogExtended](https://github.com/UMRnInside/MlogExtended) and [Wikipedia: Calling convention](https://en.wikipedia.org/wiki/Calling_convention)

## Variable Name Decoration
MlogEv IR itself will NOT decorate variable names, the frontend IS responsible for this.

The decoration rule for parameters and variables is `__<variableName>_<functionName>`.
Given such funcion (in C):
```C
int add42(int a, int b) {
    int c = a + b + 42;
    return c;
}
```

The parameter `a` in function `add42` will be decorated as `__a_add42`, so do parameter `b` and variable `c`.
The return address of function `add42` will be in variable `_retaddr_add42`, and result in `_result_add42`

## Defining and calling a function
As there are no such thing like address space in vanilla mlog, a caller may fill parameters in any order. For the example given in Chapter _Variable Name Decoration_:

In C:
```
    // variable b is assigned and initialized beforehand
    int x = add42(41, b);
```

In mlog, one can use either `jump always` or `set counter` to invoke a function:
```
add42:
op add __tmp1_add42 a b
op add c __tmp1_add42 42
set _result_add42 __c_add42
set @counter _retaddr_add42

set _a_add42 41
set _b_add42 b
op add _retaddr_add42 @counter 1
jump add42 always 0 0
```

Or in MlogEv IR:
```
__funcbegin add42
addl __a_add42 __b_add42 __tmp1_add42
addl __tmp1_add42 42 __c_add42
setl __c_add42 _result_add42
__return add42
__funcend add42

setl 41 _a_add42
setl b _b_add42
__call add42
```
The IR instruction `__call` will store return address and invoke function.

It can be proven that recursive function will NOT work under such calling convention.

## Returning from a function

If a function has a return value, it must write that value in variable `_result_<functionName>`
For the example given in Chapter _Variable Name Decoration_:

In C:
```C
    return c;
```

In mlog:
```
set _result_add42 __c_add42
set @counter _retaddr_add42
```

Or in MlogEv IR:
```
setl _result_add42 __c_add42
__return add42
```
