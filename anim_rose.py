#+
# Animations of rose curves.
# For background on the maths, see <https://en.wikipedia.org/wiki/Rose_curve>.
#
# Copyright 2014 by Lawrence D'Oliveiro <ldo@geek-central.gen.nz>.
#-

import math
import anim_common

def draw(g, radius, amplitude, freq, phase, nr_steps) :
    # note freq must be a Fraction

    def curve_func(x) :
        # Note that the curve can still be traced twice in some situations, e.g.
        # try a frequency of 3/5 and a radius of 0. But if the radius is set to nonzero,
        # the two halves no longer overlap.
        phi = 2 * math.pi * x * freq.denominator
        theta = 2 * math.pi * (x + phase) * freq.numerator
        r = radius + math.sin(theta) * amplitude
        return \
            (r * math.cos(phi), r * math.sin(phi))
    #end curve_func

    anim_common.draw_curve(g, f = curve_func, closed = True, nr_steps = nr_steps)
#end draw

def make_draw(radius, amplitude, freq, phase, nr_steps, do_settings = None) :
    # note freq must be a Fraction
    radius = anim_common.ensure_interpolator(radius)
    amplitude = anim_common.ensure_interpolator(amplitude)
    freq = anim_common.ensure_interpolator(freq)
    phase = anim_common.ensure_interpolator(phase)
    nr_steps = anim_common.ensure_interpolator(nr_steps)

    def apply_draw(g, x) :
        if do_settings != None :
            do_settings(g, x)
        #end if
        # note nr_steps must be integer
        draw \
          (
            g = g,
            radius = radius(x),
            amplitude = amplitude(x),
            freq = freq(x),
            phase = phase(x),
            nr_steps = round(nr_steps(x))
          )
    #end apply_draw

    return \
        apply_draw
#end make_draw