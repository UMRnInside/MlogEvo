# MlogEvo "Flat" Mindustry Logic Calling Convention

Special thanks to [SuperStormer/c2logic](https://github.com/SuperStormer/c2logic), [UMRnInside/MlogExtended](https://github.com/UMRnInside/MlogExtended) and [Wikipedia: Calling convention](https://en.wikipedia.org/wiki/Calling_convention)

## Variable Name Decoration
MlogEv IR itself will NOT decorate variable names, the frontend IS responsible for this.

The decoration rule for parameters and variables is `_<variableName>@<functionName>`.
Given such funcion (in C):
```C
int add42(int a, int b) {
    int c = a + b + 42;
    return c;
}
```

The parameter `a` in function `add42` will be decorated as `_a@add42`, so do parameter `b` and variable `c`.
The return address of function `add42` will be in variable `retaddr@add42`, and result in `result@add42`

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
op add _tmp1@add42 _a@add42 _b@add42
op add _c@add42 _tmp1@add42 42
set result@add42 _c@add42
set @counter retaddr@add42

set _a@add42 41
set _b@add42 b
op add retaddr@add42 @counter 1
jump add42 always 0 0
```

Or in MlogEv IR:
```
__funcbegin add42
add_i32 _a@add42 _b@add42 _tmp1@add42
add_i32 _tmp1@add42 42 _c@add42
set_i32 _c@add42 result@add42
__return add42
__funcend add42

set_i32 41 _a@add42
set_i32 b _b@add42
__call add42
```
The IR instruction `__call` will store return address and invoke function.

It can be proven that recursive function will NOT work under such calling convention.

## Returning from a function

If a function has a return value, it must write that value in variable `result@<functionName>`
For the example given in Chapter _Variable Name Decoration_:

In C:
```C
    return c;
```

In mlog:
```
set result@add42 _c@add42
set @counter _retaddr@add42
```

Or in MlogEv IR:
```
set_i32 result@add42 _c@add42
__return add42
```
