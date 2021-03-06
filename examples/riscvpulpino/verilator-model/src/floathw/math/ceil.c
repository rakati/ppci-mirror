/*
 * lib-src/ansi/math/ceil.c
 * ANSI/ISO 9899-1990, Section 7.5.6.1.
 *
 * ceil(double x)
 * Return the smallest integer greater than or equal to x.
 *
 * Exceptions:
 *	EDOM	NaN		x is NaN
 *	none	[+-]Infinity	x is [+-]Infinity
 */

#include "mathlib.h"  

double
ceil(double x)
{

#if	defined(__IEEE_FP__)
	if (_isNaN(x)) {
		errno = EDOM;
		return x;		/* NaN: domain error, return NaN */
	}
	if (_isInfinity(x))
		return x;		/* [+-]Infinity: no error, return x */
#endif	/* defined(__IEEE_FP__) */

	return (modf(x, &x) > 0.0) ? x + 1.0 : x;
}
