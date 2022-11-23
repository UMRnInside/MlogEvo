/*
 * This is part of the MlogEvo test suite
 * intended for mlog architecture
 * This test requires MlogEvo-stdlib
 *
 * Expected results:
 * double tsin = 0.5
 * double tcos = 0.8660254037844387
 * double ttan = 0.5773502691896257
 * double tasin = 0.5235987755982988
 * double tacos = 0.5235987755982988
 * double tatan = 0.5235987755982988
 * double tatan2 = 0.5235987755982988
 * double tatan2_alt = 2.6179938779914944
 */

#include "mlogevo/math.h"

// Basically M_PI / 6
double theta = M_TAU / 12;
double tsin, tcos, ttan;
double tasin, tacos, tatan, tatan2;
double tatan2_alt;

void main() {
    tsin = sin(theta), tcos = cos(theta), ttan = tan(theta);
    tasin = asin(tsin), tacos = acos(tcos), tatan = atan(ttan);
    // This can test if inline calls are implemented correctly
    double tmp = atan2(tsin, tcos);
    tatan2 = tmp;
    tatan2_alt = atan2(tsin, -tcos);
Foo:
    goto Foo;
}