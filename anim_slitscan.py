#+
# Framework for generating slit-scan animations.
# For some background, see <https://en.wikipedia.org/wiki/Slitscan>.
#
# Copyright 2014 by Lawrence D'Oliveiro <ldo@geek-central.gen.nz>.
# Licensed under CC-BY-SA <http://creativecommons.org/licenses/by-sa/4.0/>.
#-

import math
import cairo
from anim_common import \
    ensure_interpolator

class Slitscan :
    "context for rendering a slitscan image. This is maintained as a bitmap which is" \
    " extent pixels tall and steps pixels wide. The draw routine takes two arguments:" \
    " a Cairo context into which to draw, and the current animation time. Drawing is" \
    " clipped to a single column of pixels corresponding to that time, transformed" \
    " to the bounding rectangle with corners at (0, 0) and (1, extent). The image will" \
    " be animated such that a width of steps pixels occupies duration units of time."

#+
# Internal stuff
#-

    def time_to_offset(self, at_time) :
        return \
            round((1.0 - at_time / self.duration) * self.steps - 1) % self.steps
    #end time_to_offset

    def init_background(self) :
        prevop = self.g.get_operator()
        self.g.set_operator(cairo.OPERATOR_SOURCE)
        {3 : self.g.set_source_rgb, 4 : self.g.set_source_rgba}[len(self.background)] \
            (*self.background)
        self.g.paint()
        self.g.set_operator(prevop)
    #end init_background

    def get_context(self, at_time) :
        "returns a graphics context for drawing the current row/column of pixels." \
        " at_time is in units such that 1.0 corresponds to the full number" \
        " of pixel steps in the pattern."
        self.g.identity_matrix()
        self.g.reset_clip()
        self.g.new_path()
        self.g.translate(self.time_to_offset(at_time), 0)
        self.g.rectangle \
          (
            0, # x
            0, # y
            1, # width
            self.extent # height
          )
        self.g.clip()
        self.g.new_path()
        self.init_background()
        return \
            self.g
    #end get_context

#+
# User-visible stuff
#-

    def __init__(self, draw, extent, steps, duration, background) :
        self.draw = draw
        self.extent = extent
        self.steps = steps
        self.duration = duration
        self.pix = cairo.ImageSurface(cairo.FORMAT_ARGB32, steps, extent)
        self.background = background
        self.g = cairo.Context(self.pix)
        self.pat = cairo.SurfacePattern(self.pix)
        self.pat.set_extend(cairo.EXTEND_REPEAT)
        self.pat.set_filter(cairo.FILTER_BILINEAR)
        self.init_background()
        self.last_draw_time = None
    #end __init__

    def render(self, g, at_time, from_x, from_y, from_extent, to_x, to_y, to_extent) :
        "updates the current state of the pattern and draws it into destination Cairo context" \
        " g. The line from (from_x, from_y) to (to_x, to_y) defines the  starting and ending" \
        " points of the animation trajectory, while from_extent and to_extent define the extents" \
        " of the image perpendicular to this direction at these points, the ratio of the values" \
        " defining the amount of perspective foreshortening."
        base_offset = self.time_to_offset(at_time)
        if self.last_draw_time != at_time :
            if self.last_draw_time == None :
                self.last_draw_time = - self.duration / self.steps
            #end if
            this_offset = self.time_to_offset(self.last_draw_time)
            time_steps = 0
            while this_offset != base_offset :
                time_steps += 1
                this_offset -= 1
                if this_offset < 0 :
                    this_offset += self.steps
                #end if
                this_time = self.last_draw_time + time_steps * self.duration / self.steps
                self.draw(self.get_context(this_time), this_time)
            #end while
            self.last_draw_time = at_time
        #end if
        angle = math.atan2(to_y - from_y, to_x - from_x)
        self.pix.flush()
        g.save()
        g.translate(from_x, from_y)
        g.rotate(angle) # orient source pattern parallel to x-axis
        g.translate(- from_x, - from_y)
        span = math.hypot(to_x - from_x, to_y - from_y)
        for i in range(0, math.ceil(span)) :
            dst_width = min(span - i, 1)
            dst_extent = i / span * (to_extent - from_extent) + from_extent
            dst_extent2 = (i + dst_width) / span * (to_extent - from_extent) + from_extent
            # conversion from coords in destination image to offsets in source image
            # uses reciprocals to simulate perspective foreshortening. Note offsets
            # are from base_offset - 1, not base_offset, because column of pixels
            # drawn at time t = 0 is at far right (x = steps - 1).
            this_offset = \
                (
                    (
                            (1 / dst_extent - 1 / from_extent)
                        /
                            (1 / to_extent - 1 / from_extent)
                        *
                            self.steps
                    +
                        base_offset
                    -
                        1
                    )
                %
                    self.steps
                )
            this_offset2 = \
                (
                    (
                            (1 / dst_extent2 - 1 / from_extent)
                        /
                            (1 / to_extent - 1 / from_extent)
                        *
                            self.steps
                    +
                        base_offset
                    -
                        1
                    )
                %
                    self.steps
                )
            if this_offset2 < this_offset :
                this_offset2 += self.steps
            #end if
            dst_x = from_x + i
            src_rect = (this_offset, 0, this_offset2 - this_offset, self.extent)
            dst_rect = (dst_x, from_y - dst_extent / 2, dst_width, dst_extent)
            m = cairo.Matrix()
            m.translate(src_rect[0], src_rect[1])
            m.scale(src_rect[3] / dst_rect[3], src_rect[3] / dst_rect[3])
            m.translate(- dst_rect[0], - dst_rect[1])
            self.pat.set_matrix(m)
            g.set_source(self.pat)
            g.new_path()
            g.rectangle(*dst_rect)
            g.fill()
        #end for
        g.restore()
    #end render

#end Slitscan

class SlitscanObjects(Slitscan) :
    "draws a series of objects arranged in time and space. items is a sequence of Item," \
    " (see the inner class definition) in the order in which they are to be drawn (which" \
    " need not correspond to their ordering in time); extent, steps, duration and background" \
    " have the same meanings as for the Slitscan superclass."

    class Item :
        "surface is expected to be a Cairo ImageSurface, while the other parameters specify" \
        " its extent in space and time within the slitscan animation: width and x_offset" \
        " are in time units, while height and y_offset are in units of the height of the" \
        " slit."

        def __init__(self, surface, width, height, x_offset, y_offset) :
            self.surface = surface
            self.width = width
            self.height = height
            self.x_offset = x_offset
            self.y_offset = y_offset
        #end __init__

    #end Item

    def draw_items(self, g, t) :
        for item in self.items :
            if (
                    item.x_offset >= t and item.x_offset <= t + self.duration
                or
                    item.x_offset + item.width >= t and item.x_offset + item.width <= t + self.duration
                  # either left or right edge is visible <=> some part of image is visible
            ) :
                g.save()
                g.translate((item.x_offset - t) / self.duration * self.steps, item.y_offset * self.extent)
                g.scale \
                  (
                    item.width / self.duration * self.steps / item.surface.get_width(),
                    item.height * self.extent / item.surface.get_height()
                  )
                g.set_source_surface(item.surface)
                g.paint()
                g.restore()
            #end if
        #end for
    #end draw_items

    def __init__(self, items, extent, steps, duration, background) :
        self.items = items
        super().__init__(self.draw_items, extent, steps, duration, background)
    #end __init__

#end SlitscanObjects

def make_draw(slitscan, from_x, from_y, from_extent, to_x, to_y, to_extent) :
    from_x = ensure_interpolator(from_x)
    from_y = ensure_interpolator(from_y)
    from_extent = ensure_interpolator(from_extent)
    to_x = ensure_interpolator(to_x)
    to_y = ensure_interpolator(to_y)
    to_extent = ensure_interpolator(to_extent)

    def apply_draw(g, t) :
        slitscan.render(g, t, from_x(t), from_y(t), from_extent(t), to_x(t), to_y(t), to_extent(t))
    #end apply_draw

#begin make_draw
    return \
        apply_draw
#end make_draw
