# MlogEvo Intermediate Code Format, version (nightly)

MlogEvo (or mlogev) intermediate code is (mostly) quadruple, and can be stored in plain text. Most of the instructions will be like:

`instruction arg1 arg2 result`

Immediate values should start with `$` (e.g. `setl $42 %a`

The suffix `l` indicates "long", or 32-bit signed integers, while `f` prefix means IEEE-754 float64 (or double).

Special thanks to [Wikibooks/x86 Assembly](https://en.wikibooks.org/wiki/X86_Assembly)


# Terms
* The _mlog_ is an abbreviation for [_Mindustry Logic_](https://mindustrygame.github.io/wiki/logic/0-introduction/) .
* The _mlogev_ (or MlogEv) is an abbreviation for _MlogEvo_ , where _evo_ means _evolution_ .
* An _int32_ stands for 32-bit signed integer.
* A _float64_ stands for IEEE-754 float64 (formerly double-precision floating point number).
* (TBC)


# Supported instructions / verdictsA

## Variable declaration
* Format: `varl <variable>`
* Format: `fvar <variable>`

Declare a variable is a 32-bit signed int (`varl`) or float64 (`fvar`), does _not_ affect final outputs.
If there are _conflict_ declarations, the _last_ one the backend processes should be followed.

## Data transfer

### Set or copy value
* Format: `setl <src> <dest>`
* Format: `fset <src> <dest>`

Copies the src operand into the dest operand. Note that if `src` operand is a float64 value, it will be rounded _down_ in `dest` operand.
The `src` operand can be an immediate value or a variable, while `dest` must be a variable.

## Control Flow
The jump instructions allow the programmer to (indirectly) set the value of the Program Counter (`@counter` in mlog). The location passed as the argument is usually a label. The first instruction executed after the jump is the instruction immediately following the label.

### Labels
* Format: `:this_is_a_label`, `:ThisIsAnotherLabel`, `:Label42`

### Unconditional jump
* Format: `goto <label>`

### Jump if condition IS met
* Format: `if <condition> goto <label>`

A _condition_ is a C-style comparison like `x < 100`

### Jump if condition IS Not met
* Format: `ifnot <condition> goto <label>`

## Arithmetic

### Addition
* Format: `addl src1 src2 dest`
* Format: `fadd src1 src2 dest`

This adds `src1` and `src2` then stores the result in `dest`.
If any of the `src1` and `src2` operand is float64, the behavior of `addl` is defind by implementation.

### Subtraction
* Format: `subl src1 src2 dest`
* Format: `fsub src1 src2 dest`

Like addition, only it subtracts `src2` from `src1` then stores the result in `dest`.

### Multiplication
* Format: `mull src1 src2 dest`
* Format: `fmul src1 src2 dest`

This multiplies `src1` by `src2` then stores the result in `dest`.

### Division (get quotient)
* Format: `divl dividend divisor dest`
* Format: `fdiv dividend divisor dest`

This divides dividend by divisor, then stores _quotient_ in dest. Contents in `dividend` and `divisor` remain untouched.
For `divl`, if `divisor` is not int32, the behavior is defined by implementation.

### Division (get remainder)
* Format: `reml dividend divisor dest`

Like `divl`, only it stores _remainder_ in dest.

### Sign Inversion
* Format: `minusl src dest`
* Format: `fminus src dest`

Namely `dest = -src` in C.


## Logical and Rearrangement

### Bitwise and
* Format: `andl src1 src2 dest`

### Bitwise or
* Format: `orl src1 src2 dest`

### Bitwise xor
* Format: `xorl src1 src2 dest`

### Bitwise inversion
* Format: `notl src dest`

### Logical (unsigned) left shift
* Format: `lshl src count dest`

Logical shift `src` to the left by `count` bits, then store its result in `dest`.

### Logical (unsigned) right shift
* Format: `rshl src count dest`

Logical shift `src` to the right by `count` bits, then store its result in `dest`.


## ASM block

Note that an ASM block can have no input or output variables. Everything in ASM block should be copied line-by-line by backend.

### ASM block begin
* Format: `__asmbegin <input_var_count> [input_var_1] [input_var_2] ...`

### ASM block end
* Format: `__asmend <output_var_count> [output_var_1] [output_var_2] ...`

## Miscellaneous

### No operation
* Format: `noop`

Literally does nothing.
