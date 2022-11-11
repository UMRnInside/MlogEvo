/*
 * This is part of the MlogEvo test suite
 * intended for mlog architecture
 *
 * Expected results:
 * double sum_ab = 46.2
 * double diff_ab = 37.8
 * double diff_ba = -37.8
 * double a_minus = -42
 * double prod_ab = 176.4
 * double quot_ab = 10.0
 * double quot_ba = 0.1
 * double mixed_1 = 89
 * double mixed_2 = 94
 */

double a = 42, b = 4.2;
double sum_ab, diff_ab, diff_ba;
double a_minus;
double prod_ab, quot_ab, quot_ba;
double mixed_1, mixed_2;

void main() {
    sum_ab = a + b;
    diff_ab = a - b;
    diff_ba = b - a;
    a_minus = -a;
    prod_ab = a * b;
    quot_ab = a / b, quot_ba = b / a;
    mixed_1 = 5 + a*2;
    mixed_2 = (5 + a)*2;
    // MlogArithmeticRunner stops on self-loop
Foo:
    goto Foo;
}