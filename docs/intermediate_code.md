# MlogEvo Intermediate Code Format, version (nightly)

MlogEvo (or mlogev) intermediate code is (mostly) quadruple, and can be stored in plain text. Most of the instructions will be like:

`instruction arg1 arg2 result`

The suffix `_i32` indicates "long", or 32-bit signed integers, while `_f64` *suffix* means IEEE-754 float64 (or double).

Special thanks to [Wikibooks/x86 Assembly](https://en.wikibooks.org/wiki/X86_Assembly)


# Terms
* The _mlog_ is an abbreviation for [_Mindustry Logic_](https://mindustrygame.github.io/wiki/logic/0-introduction/) .
* The _mlogev_ (or MlogEv) is an abbreviation for _MlogEvo_ , where _evo_ means _evolution_ or _evolved_ .
* An _int32_ stands for 32-bit signed integer.
* A _float64_ stands for IEEE-754 float64 (formerly double-precision floating point number).
* (TBC)


# Supported instructions / verdicts

## Declaration
* Format: `decl_i32 <attributes> <var>`
* Format: `decl_f64 <attributes> <var>`
* Format: `decl_obj <attributes> <var>`
* Format: `decl_struct <attributes> <var> <struct_name>`

If you have no idea about `attributes`, feel free to write `default` verdict. e.g.: `decl_i32 default x`

Attributes that may be used:
  * `default`
  * `argument`
  * `volatile`
  * `static`

## Data transfer

### Set or copy value
* Format: `set_i32 <src> <dest>`
* Format: `set_f64 <src> <dest>`
* Format: `set_obj <src> <dest>`
* Format: `set_struct <src> <dest>`

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
* `<condition>`: `<value1> <relop> <value2>`
* e.g.: `if x lt_i32 100 goto some_label`

A _condition_ is a comparison like `x lt_i32 100` (which means `x < 100`).
A _relop_ is one of the comparison instructions.

### Jump if condition IS Not met
* Format: `ifnot <condition> goto <label>`

## Arithmetic

### Addition
* Format: `add_i32 src1 src2 dest`
* Format: `add_f64 src1 src2 dest`

This adds `src1` and `src2` then stores the result in `dest`.
If any of the `src1` and `src2` operand is float64, the behavior of `addl` is defind by implementation.

### Subtraction
* Format: `sub_i32 src1 src2 dest`
* Format: `sub_f64 src1 src2 dest`

Like addition, only it subtracts `src2` from `src1` then stores the result in `dest`.

### Multiplication
* Format: `mul_i32 src1 src2 dest`
* Format: `mul_f64 src1 src2 dest`

This multiplies `src1` by `src2` then stores the result in `dest`.

### Division (get quotient)
* Format: `div_i32 dividend divisor dest`
* Format: `div_f64 dividend divisor dest`

This divides dividend by divisor, then stores _quotient_ in dest. Contents in `dividend` and `divisor` remain untouched.
For `div_i32`, if `divisor` is not int32, the behavior is defined by implementation.

### Division (get remainder)
* Format: `rem_i32 dividend divisor dest`

Like `divl`, only it stores _remainder_ in dest.

### Ceiling and flooring
* Format: `floor_f64 src1 dest`
* Format: `ceil_f64 src1 dest`

### Convert from f64 to i32 (may truncate)
* Format: `cvtf64_i32 <src> <dest>`

`src` is `f64`.

### Convert from i32 to f64
* Format: `cvti32_f64 <src> <dest>`

### Sign Inversion
* Format: `minus_i32 src dest`
* Format: `minus_f64 src dest`

Namely `dest = -src` in C.

### Comparison
* Format: `lt_i32 <a> <b> <dest>`
* Format: `lt_f64 <a> <b> <dest>`

Write `1` (integer) to `<dest>` if `a < b` holds, otherwise write `0`

All comparison instructions:
* `lt_i32`, `lt_f64`: `a < b`
* `gt_i32`, `gt_f64`: `a > b`
* `lteq_i32`, `lteq_f64`: `a <= b`
* `gteq_i32`, `gteq_f64`: `a >= b`
* `eq_i32`, `eq_f64`: `a == b`
* `ne_i32`, `ne_f64`: `a != b`


## Logical and Rearrangement

### Bitwise and
* Format: `and_i32 src1 src2 dest`

### Bitwise or
* Format: `or_i32 src1 src2 dest`

### Bitwise xor
* Format: `xor_i32 src1 src2 dest`

### Bitwise inversion
* Format: `not_i32 src dest`

### Logical (unsigned) left shift
* Format: `lsh_i32 src count dest`

Logical shift `src` to the left by `count` bits, then store its result in `dest`.

### Logical (unsigned) right shift
* Format: `rsh_i32 src count dest`

Logical shift `src` to the right by `count` bits, then store its result in `dest`.

## Functions

### Function block begin
* Format: `__funcbegin <function_name> <flags>`

Denote the beginning of a function, and assign a label.

### Function block end
* Format: `__funcend <function_name>`

Denote the end of a function.

### Function call
* Format: `__call <function_name>`

Call a function, does store return address, does NOT automatically push arguments. `function_name` must be defined in `__funcbegin` beforehand.

### Function return
* Format: `__return <function_name>`

Return from a function, jump back to callee, does NOT automatically push results.


## Memory

### Read
 * Format: `read_i32 <address> <variable>`
 * Format: `read_f64 <address> <variable>`

Load variable from memory address. 

### Write
 * Format: `write_i32 <address> <variable>`
 * Format: `write_f64 <address> <variable>`

## Structure

* Format: `__structbegin <name>`
* Format: `__structend <name>`
* Internal notation: `Quadruple(instruction="struct")`

## ASM Template block

Note that an ASM Template block can have no input or output variables.

### ASM Template block begin and end
* Format: `__asmbegin <input_var_count> [input_var_1] [input_var_2] ...`
* Format: `__asmend <output_var_count> [output_var_1] [output_var_2] ...`
* Internal notation: `Quadruple(instruction="asm")`

### Volatile ASM Template block begin and end
* Format: `__asmvbegin <input_var_count> [input_var_1] [input_var_2] ...`
* Format: `__asmvend <output_var_count> [output_var_1] [output_var_2] ...`
* Internal notation: `Quadruple(instruction="asm_volatile")`

## Miscellaneous

### No operation
* Format: `noop`

Literally does nothing.
