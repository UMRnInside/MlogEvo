/*
 * This is part of the MlogEvo test suite
 * intended for mlog architecture
 *
 * This shows the difference between `op div` and `op idiv` in Mindustry Logic
 * SuperStormer/c2logic use `op div` for integers, which would not pass this test.
 *
 * Expected results:
 * int sum = 1650
 * double sum_f = 1683.3333333333333
 */ 

int sum;
double sum_f;

void main() {
    sum = 0;
    sum_f = 0.0;
    int i;
    for (i=1;i<=100;i++) {
        sum += i/3;
        sum_f += i/3.0;
    }
    // MlogArithmeticRunner stops on self-loop
Foo:
    goto Foo;
}
