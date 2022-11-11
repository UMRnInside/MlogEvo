/*
 * This is part of the MlogEvo test suite
 * intended for mlog architecture
 *
 * Expected results:
 * int sum_ab = 628
 * int diff_ab = -400
 * int diff_ba = 400
 * int a_minus = -114
 * int prod_ab = 58596
 * int quot_ab = 0
 * int quot_ba = 4
 * int rem_ab = 114
 * int rem_ba = 58
 * int mixed_1 = 233
 * int mixed_2 = 238
 * int comma_1 = 42
 * int lshift5_a = 3648
 * int rshift5_a = 3
 * int and_ab = 2
 * int or_ab = 626
 * int xor_ab = 624
 */

int a = 114, b = 514;

int sum_ab, diff_ab, diff_ba;
int a_minus;
int prod_ab;
int quot_ab, quot_ba;
int rem_ab, rem_ba;
int mixed_1, mixed_2, comma_1;
int lshift5_a, rshift5_a, and_ab, or_ab, xor_ab;

void main() {
    // MlogArithmeticRunner stops on self-loop
    sum_ab = a + b;
    diff_ab = a - b;
    diff_ba = b - a;
    a_minus = -a;
    prod_ab = a * b;
    quot_ab = a / b, quot_ba = b / a;
    rem_ab = a%b, rem_ba = b%a;
    mixed_1 = 5 + a*2;
    mixed_2 = (5 + a)*2;
    comma_1 = a+b, a+3, 42;

    lshift5_a = a << 5, rshift5_a = a >> 5;
    and_ab = a&b, or_ab = a|b, xor_ab = a^b;
Foo:
    goto Foo;
}