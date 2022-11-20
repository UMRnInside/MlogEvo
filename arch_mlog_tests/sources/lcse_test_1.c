/*
 * This is part of the MlogEvo test suite
 * intended for mlog architecture
 *
 * Expected results:
 * int r = 25
 * int g = 3
 */

int x1 = 3, x2 = 0, y1 = 0, y2 = 4;
int r;
int g;

void main() {
    int r2 = (x1-x2) * (x1-x2) + (y1-y2) * (y1-y2);
    g = (x1-x2);
    r = r2;
Foo:
    goto Foo;
}
