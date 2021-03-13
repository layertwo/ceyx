# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Copyright 2008,2010 authors:
# * Sebastian Spaeth
#    This file is part of ceyx.
#
#    ceyx is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    ceyx is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with ceyx.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------------
import math
import cairo
#pygtk >=2.8 contains support for having pango rendering text
import pangocairo
import pango
import ceyx.utils

class WarpCTX(object):
    """Warp a text ctx in place"""
    def get_xy_at_distance(self, dist, y_offset):
        """Walk along self.ctx and find the x,y offset for distance dist"""
        first_p = None
        prev_point = None
        curdist = 0
        x, y = 0, 0
        for type, points in self.ctx_flat:
            #if MOVE TO, just set the current 
            if type == cairo.PATH_MOVE_TO and not first_p:
                first_p = points
                prev_point = points
            elif type == cairo.PATH_LINE_TO: pass
            elif type == cairo.PATH_CLOSE_PATH:
                points = first_p
            else:
                raise Exception("Unknown Type Moo %s" % type)

            if prev_point != points:
                length = ceyx.utils.path_length(prev_point, points)
            else:
                continue

            curdist += length
            if curdist >= dist:
            #need to interpolate next fraction of next way:
                #TODO, document the working of this and the variables
                frac = (curdist-dist)/length
                delta_x = (frac * (points[0]-prev_point[0]))
                delta_y = (frac * (points[1]-prev_point[1]))
                sin_alpha = delta_x / (frac * length)
                cos_alpha = delta_y / (frac * length)
                x = points[0] - delta_x - (cos_alpha * y_offset)
                y = points[1] - delta_y + (sin_alpha * y_offset)
                break
            prev_point = points
        return x, y

    def warppoint(self, x, y):
        return self.get_xy_at_distance(x, y)

    def warptext(self, text_ctx, cPath):
        """Transform cairo context with text path according to function

        Take a cairo context and a function and transform each coordinate by
        invoking function(*points) which returns (x,y)"""
        self.ctx_flat = cPath
        first = True
        for type, points in text_ctx.copy_path():
            if type == cairo.PATH_MOVE_TO:
                if first:
                    text_ctx.new_path()
                    first = False
                x, y = self.warppoint(*points)
                text_ctx.move_to(x, y)

            elif type == cairo.PATH_LINE_TO:
                x, y = self.warppoint(*points)
                text_ctx.line_to(x, y)
    
            elif type == cairo.PATH_CURVE_TO:
                x1, y1, x2, y2, x3, y3 = points
                x1, y1 = self.warppoint(x1, y1)
                x2, y2 = self.warppoint(x2, y2)
                x3, y3 = self.warppoint(x3, y3)
                text_ctx.curve_to(x1, y1, x2, y2, x3, y3)
    
            elif type == cairo.PATH_CLOSE_PATH:
                text_ctx.close_path()


class Textrenderer(object):
    def __init__(self, osmrenderer):
        """TODO: we need to keep track where things have been printed,
        so we can do label suppression and fancy stuff."""
        self.osm = osmrenderer

    def get_path_length(self, ctx):
        """Return an approximate length of a path"""
        prev_point = None
        dist  = 0
        first = True
        # get current path and find longest part
        for part in ctx.copy_path_flat():
            #if MOVE TO, just set the current 
            if part[0] == cairo.PATH_MOVE_TO:
                if first:
                    first = False
                    length = 0
                else:
                    length = ceyx.utils.path_length(prev_point, part[1])
                prev_point = part[1]    
            elif part[0]==cairo.PATH_LINE_TO:
                length = ceyx.utils.path_length(prev_point, part[1])
                prev_point = part[1]
            elif part[0]==cairo.PATH_CLOSE_PATH:
                length = self.path_length(prev_point, path[0][1])
                prev_point = path[0][1]
            else:
                raise Exception("Impossible Cairo Operation")
            dist += length
        return dist

    def find_longest_subpath(self, ctx):
        """Find the longest subpath of the current path and return the length of it and the subpath.

        This is usually used to determine whether a text fits on a
        path and where to print it."""
        #possible CAIRO operations:
        #PATH_MOVE_TO, PATH_LINE_TO, PATH_CURVE_TO, PATH_CLOSE_PATH
        prev_point, cur_point = None, None
        ret_point1, ret_point2 = None, None
        max_dist  = None

        # get current path and find longest part
        for part in ctx.copy_path_flat():
            #if MOVE TO, just set the current 
            if part[0] == cairo.PATH_MOVE_TO:
                length = 0         
                prev_point = part[1]    
                cur_point = part[1]
            elif part[0]==cairo.PATH_LINE_TO or \
                 part[0]==cairo.PATH_CURVE_TO:
                #treat curves as straight lines for now
                length = ceyx.utils.path_length(cur_point, part[1])
                prev_point = cur_point
                cur_point = part[1]
            elif part[0]==cairo.PATH_CLOSE_PATH:
                length = self.path_length(cur_point, path[0][1])
                prev_point = cur_point
                cur_point = path[0][1]
            else:
                raise Exception("Impossible Cairo Operation")

            if length > max_dist:
                max_dist = length
                ret_point1 = prev_point
                ret_point2 = cur_point

        return max_dist, (ret_point1, ret_point2)

    def find_long_subpaths(self, minlength, ctx):
        """return all path elements which are longer than minlength"""
        #possible CAIRO operations:
        #PATH_MOVE_TO, PATH_LINE_TO, PATH_CURVE_TO, PATH_CLOSE_PATH
        points = []

        # get current path and find long parts
        for part in ctx.copy_path_flat():
            #if MOVE TO, just set the current 
            if part[0] == cairo.PATH_MOVE_TO:
                length = 0
                prev_point = part[1]
                cur_point = part[1]
            elif part[0]==cairo.PATH_LINE_TO:
                #treat curves as straight lines for now
                length = ceyx.utils.path_length(cur_point, part[1])
                prev_point = cur_point
                cur_point = part[1]
            elif part[0]==cairo.PATH_CLOSE_PATH:
                length = self.path_length(cur_point, path[0][1])
                prev_point = cur_point
                cur_point = path[0][1]
            else:
                raise Exception("Impossible Cairo Operation")

            if length > minlength:
                points.append((prev_point, cur_point))

        return points

    def render_text_curved_path(self, p_layout, rules, p_ctx, ctx):
        """Render text on an curved path, warping the text

        The caller needs to ensure that the text width is less than the
        length of path ctx (it fits the path)
 :param p_layout: is a
        pango layout created with p_ctx.create_layout()
        """
        extents = p_layout.get_pixel_extents()[1]
        textheight = extents[3]-extents[1]
        way_ctx = ctx.copy_path_flat()
        #save ctx, as we want to restore the current line width etc
        ctx.save()
        p_ctx.new_path()
        p_ctx.move_to(5, -textheight/2.0)
        p_ctx.layout_path(p_layout)
        #transform up TODO, FIXME
        #modify p_ctx in place
        WarpCTX().warptext(p_ctx, way_ctx)
        # and show the regular text
        p_ctx.fill()
        #restore the ctx that we previously saved in this function
        ctx.restore()

    def render_text_along_path(self, p_layout, rules, p_ctx, ctx):
        """Render text on an xy position

        :param p_layout: is a pango layout created with p_ctx.create_layout()
        """
        #Put text on line. Go through all path elements of the
        #current path and find the longes element. If the text
        #fits on there, print it on that element, otherwise
        #drop writing the text at all.
        extents = p_layout.get_pixel_extents()[1]
        textwidth = extents[2]-extents[0]
        #gravity point of previously drawn on label
        prev_p = None

        points = self.find_long_subpaths(textwidth, ctx)

        if not points:
            if self.get_path_length(ctx) < textwidth*1.2:
                #path shorter than text label. drop completely
                return
            #No long straight segments, but a long enough path, need to
            #print on curved path here:
            return self.render_text_curved_path(p_layout, rules, p_ctx, ctx)

        for p1, p2 in points:
            x1, x2 = p1[0], p2[0]
            y1, y2 = p1[1], p2[1]
            x = x1 + (x2-x1)/2
            y = y1 + (y2-y1)/2

            # drop points, if they are too close to the previous points,
            # suppressing the next label printing
            # gravity of 2 subsequent long path element less than
            # textwidth*4 apart? Suppress!
            if prev_p and \
                    ceyx.utils.path_length(prev_p, (x,y)) < \
                    (extents[2]-extents[0])*4:
                         continue
            prev_p = (x,y) #set new previous gravity point

            # How much do we need to rotate the label?
            rot_degree = math.atan2(y2-y1, x2-x1)

            #save ctx, as we want to restore the current line width etc
            ctx.save()

            # we don't need the current path anymore, 
            # delete it so we can stroke the text halo
            ctx.new_path()

            #(vertical) text-offset
            fontoffset = rules.get('text-offset', None)
            if fontoffset:
                try:
                    fontoffset = float(fontoffset)
                except ValueError:
                    fontoffset = 0
                y = y + fontoffset

            #debug circles:
            #ctx.move_to(x,y)
            #ctx.arc(x,y,40, 0, 2*math.pi)
            #ctx.stroke_preserve()
            #ctx.fill()
    
            #center text around zero
            p_ctx.translate(x,y)
            #rotate if needed
            if rot_degree:
                if rot_degree > math.pi / 2:
                    rot_degree -= math.pi
                elif rot_degree < -math.pi / 2:
                    rot_degree += math.pi
                p_ctx.rotate(rot_degree)
            p_layout.context_changed() 
    
            ctx.move_to(-textwidth/2.0,
                        (extents[1]-extents[3])/2.0)
    
            if (rules.get('text-halo-color') and rules.get('text-halo-radius')):
                #helo is wanted
                #text halo color
                halocolor = rules.get('text-halo-color', 'white')
                (r,g,b) = ceyx.utils.get_rgb(halocolor)
                ctx.set_source_rgb(r,g,b)
    
                texthalo = float(rules.get('text-halo-radius'))
                ctx.set_line_width(texthalo * 2)
                p_ctx.layout_path(p_layout)
                ctx.stroke()
                ctx.move_to(-textwidth/2.0,
                        (extents[1]-extents[3])/2.0)
            #regular text color
            color = rules.get('text-color', 'black')
            (r,g,b) = ceyx.utils.get_rgb(color)
            ctx.set_source_rgb(r,g,b)
            # and show the regular text
            p_ctx.show_layout(p_layout)
            #restore the ctx that we previously saved in this function
            ctx.restore()

    def render_text(self, ele, rules, ctx):
        """Render text using pango"""

        # First, determine which tag to render
        text_tag = rules.get('text', None)
        if text_tag is None:
            return False

        text = None
        rot_degree = None
        for child in ele.findall('tag'):
            if child.get('k') == text_tag:
                text = child.get('v', None)

        #don't render if there is this element's tag has no value
        if text is None:
            return True

        #render text on a node's position, if a way, look at 'text-position'
        if ele.tag == 'node':
            x, y = self.osm.latlon2xy((float(ele.get('lat')),
                                       float(ele.get('lon'))))
            render_on_point = True
        elif ele.tag == 'way':
            #text-position can be 'line' or 'center'
            textposition = rules.get('text-position', 'line')

            if textposition == 'center':
                #simply draw in the middle of the bounding box for now
                #TODO: more elaborate algorythm where to place it.
                (x,y,x2,y2) = ctx.path_extents()
                x,y = x+ (x2-x)/2, y+(y2-y)/2
                render_on_point = True

            else:
                #put text on line.
                render_on_point = False
        else:
            # no 'node' or 'way': unknown element, return with failure
            return False

        # chose the font characteristics
        ft_desc = pango.FontDescription()
        #font-family
        fontfamily = rules.get('font-family', 'sans')
        ft_desc.set_family(fontfamily)

        #font-size
        fontsize = int(rules.get('font-size',12))
        ft_desc.set_size(pango.SCALE*fontsize)

        #font-style
        fontstyle = rules.get('font-style', 'normal')
        if fontstyle == 'italic':
            fontstyle = pango.STYLE_ITALIC
        else:
            fontstyle = pango.STYLE_NORMAL
        ft_desc.set_style(fontstyle)

        #font-weight (either numeric 200-900, or 'normal' (400), or 'bold' (700)
        fontweight = rules.get('font-weight', 400)
        try:
            fontweight = int(fontweight)
        except ValueError:
            if fontweight == 'bold':
                fontweight = 700
            else:
                fontweight = 400
        ft_desc.set_weight(fontweight)

        #text-transform: 'none' or 'uppercase' 
        transform = rules.get('text-transform', 'none')
        if transform == 'uppercase':
            text = text.upper()

        #create a pangocairo.CairoContext
        p_ctx = pangocairo.CairoContext(ctx)
        p_layout = p_ctx.create_layout()

        p_layout.set_font_description(ft_desc)
        p_layout.set_text(text)

        p_attrs = pango.AttrList()

        #text-decoration: 'none' or 'underline
        decoration = rules.get('text-decoration', 'none')
        if decoration == 'underline':
            p_attrs.insert(pango.AttrUnderline(pango.UNDERLINE_SINGLE,end_index=-1))

        #font-variant: 'normal' or 'small-caps'
        decoration = rules.get('font-variant', 'none')
        if decoration == 'small-caps':
            p_attrs.insert(pango.AttrVariant(pango.VARIANT_SMALL_CAPS, start_index=0, end_index=-1))

        p_layout.set_attributes(p_attrs)

        #maximum text width before we wrap
        maxwidth = rules.get('max-width', -1)
        try:
            maxwidth = int(maxwidth)
        except ValueError:
            maxwidth = -1
        if maxwidth > 0:
            # set maximum width and center lines
            p_layout.set_width(pango.SCALE * maxwidth)
            #tried to center-align multiple lines, but that leads to
            #much large pixel extents in x-direction (see below, and
            #centering along pixel-extents would not center the text
            #anymore, so just left align here and all is well.
            #p_layout.set_alignment(pango.ALIGN_CENTER)
            p_layout.set_alignment(pango.ALIGN_LEFT)

        orig_path = ctx.copy_path() # save,s o we can restore before returning
        #if we render on a node, just render in any case. If we render
        #on point on way, drop if extents exceeds the way's bbox.
        #If we render along path, check if text exceeds longest part.
        if not render_on_point:
                self.render_text_along_path(p_layout, rules, p_ctx, ctx)
                ctx.new_path()
                ctx.append_path(orig_path) # restore original path
                return

        #calculate the extents of our text
        extents = p_layout.get_pixel_extents()[1]

        if ele.tag == 'way':
            fillx1,filly1,fillx2,filly2 = ctx.path_extents()
        #    if (fillx2-fillx1) < (extents[2]-extents[0]):
        #        return False

        #save ctx, as we want to restore the current line width etc
        ctx.save()

        # we don't need the current path anymore,
        # delete it so we can stroke the text halo
        ctx.new_path()

        #use text-alignment property to top-align or center text
        valignment = rules.get('text-alignment', 'center')
        if valignment == 'bottom':
            valignment = extents[1]-extents[3]
        elif valignment == 'center':
            valignment = (extents[1]-extents[3]) / 2
        else:
            #top etc
            valignment = 0

        #(vertical) text-offset
        fontoffset = rules.get('text-offset', None)
        if fontoffset:
            try:
                fontoffset = float(fontoffset)
            except ValueError:
                fontoffset = 0
            y = y + fontoffset

        #debug circles:
        #ctx.move_to(x,y)
        #ctx.arc(x,y,40, 0, 2*math.pi)
        #ctx.stroke_preserve()
        #ctx.fill()

        #center text around zero
        p_ctx.translate(x,y)
        #rotate if needed
        if rot_degree:
            if rot_degree > math.pi / 2:
                rot_degree -= math.pi
            elif rot_degree < -math.pi / 2:
                rot_degree += math.pi
            p_ctx.rotate(rot_degree)
        p_layout.context_changed() 

        ctx.move_to((extents[0]-extents[2])/2.0,
                    valignment)

        if (rules.get('text-halo-color') and rules.get('text-halo-radius')):
            #helo is wanted
            #text halo color
            halocolor = rules.get('text-halo-color', 'white')
            (r,g,b) = ceyx.utils.get_rgb(halocolor)
            ctx.set_source_rgb(r,g,b)

            texthalo = float(rules.get('text-halo-radius'))
            ctx.set_line_width(texthalo * 2)
            p_ctx.layout_path(p_layout)
            ctx.stroke()
            ctx.move_to((extents[0]-extents[2])/2.0,
                    valignment)

        #regular text color
        color = rules.get('text-color', 'black')
        (r,g,b) = ceyx.utils.get_rgb(color)
        ctx.set_source_rgb(r,g,b)
        # and show the regular text
        p_ctx.show_layout(p_layout)
        #restore the ctx that we previously saved in this function
        ctx.restore()
        ctx.append_path(orig_path) # restore original path
