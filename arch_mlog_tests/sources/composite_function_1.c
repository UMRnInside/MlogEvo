/*
 * This is part of the MlogEvo test suite
 * intended for mlog architecture
 *
 * Expected results:
 * int res1 = 14
 */

int res1 = 0;

int f(int a, int b) {
    return a*4 + b;
}

int g(int x) {
    return x+1;
}

void main() {
    res1 = f(g(2), g(1));
Foo:
    goto Foo;
}
