# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Copyright 2008-2011
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
from sys import stderr
import math
import cairo
import io
from ceyx import Textrenderer
from ceyx.MapCSS import CSSException
import ceyx.utils
import logging

class Relationship(object):
   def __init__(self):
       self.members = []

class RelMember(object):
    """A Multipolygon member"""
    def __init__(self):
       self.type   ='outer'
       self.wayref = None

class Way(object):
    tag = 'way'
    """For compatability with ElementTree we keep a tag attr, so we can
    replace xml elements with an Way object"""
    def __init__(self, osmparser, ele):
        """:param ele: ElementTree object of tag 'way'"""
        self.osmparser = osmparser
        # create a list of node ids of the way
        self.id = ele.get('id', None)
        self.noderefs = [int(child.get('ref')) for 
                         child in ele.findall('nd')]

    def get_waynodes_latlon(self):
       """return a generator of waynodes' (lat,lon)"""
       # find all nodes lat/lon, calculate the image coords and stuff
       # those into a list of tuples in 'waynodes'.
       for ref in self.noderefs:
           try:
               yield self.osmparser.nodes[ref]['latlon']
           except KeyError:
               #sanity check: we did not find a node that was referenced
               stderr.write("Way " + ele.get("id") +" contains unknown node\n" + str(ref) + "\n")
               return

    def get_waynodes_xy(self, osmrenderer):
       """return x,y values of waynodes on way"""
       for latlon in self.get_waynodes_latlon():
           yield osmrenderer.latlon2xy(latlon)


class OSMrenderer(object):
    def __init__(self):
        self.layers={}
        """a dict that contains {'z-index as float':CairoContext(),...}"""
        self.casinglayers={}
        """a dict that contains {'z-index as int':CairoContext(),...}

        Casinglayers are used to draw all casings from highways/ways
        in the int area. That is casinglayer[0] receives all the
        casings of highways with z-index:0.0 - 0.99. This is needed so
        a crossing between a primary road at z-index:0.1 and a
        tertiary road with z-index: 0.0 don't have their casings
        bleeding into the core of the other ways.
        """
        self.bounds = None
        self.margin = 0
        """Image Margin in pixel to boundary"""
        self.antialias = cairo.ANTIALIAS_DEFAULT
        """Should we perform antialiasing for graphics (not text):
           One of cairo.ANTIALIAS_NONE, cairo.ANTIALIAS_DEFAULT"""
        self.textrenderer = None;
        """render_png() inits this with an Textrenderer() instance"""

    def set_boundaries(self, bounds, height, width, margin=0):
        """Set the boundaries that are used to convert lat/lon to
        pixel positions on the image.
        :param height: Image height in pixel or None if autocalculated
        :param width: Image width in pixel
        :param margin: image border in pixels
        """
        self.bounds = bounds
        self.margin = margin
        if width is None: raise Exception("Width must not be None.")
        self.width=width

        #cache the upper and lower boundaries
         #following scales between 0-2 for degrees -85 - +85:
        #(((math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))))/math.pi) - 1)
        up_lat_rad = math.radians(self.bounds.ul.lat)
        low_lat_rad = math.radians(self.bounds.lr.lat)
        # This ranges from -pi to +pi
        self.up_y1 = math.log(math.tan(up_lat_rad) + (1 / math.cos(up_lat_rad)))
        self.low_y1 = math.log(math.tan(low_lat_rad) + (1 / math.cos(low_lat_rad)))

        if height: # explicitly given height?
            self.height = height
        else:
            #calculate aspect-ratio preserving height of image
            # self.up_y1 and low_y1 range from -pi/+pi, so we need the
            # same range for our lon boundaries_
            lon_range = ((self.bounds.lr.lon-self.bounds.ul.lon) / 180.0)\
                 * math.pi
            self.height = int(2*margin + \
                width * (self.up_y1-self.low_y1)/lon_range)
            logging.debug("Using calculated image height: %d" % self.height)

    def latlon2xy(self, latlon):
        """Converts a degree-based (lat,lon) into the x,y position on the image"""
        (lat, lon) = latlon
        #use cached upper and lower y boundaries up_y1 and low_y1
        #OBS: Make sure you refresh these values via set_boundaries() in
        #render_png when you pass in different boundaries.

        # lon is simply linear, easy.
        x = self.margin + (float(lon) - self.bounds.ul.lon) / \
            (self.bounds.lr.lon - self.bounds.ul.lon) * \
            (self.width - 2*self.margin)

        #lat is trickier
        #this scales between 0-2 for degrees -85 - +85:
        #(((math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))))/math.pi) - 1)
        lat_rad = math.radians(lat)
        y1 = (math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))))
        y = self.margin + ((self.up_y1 -y1) / (self.up_y1 - self.low_y1)) * (self.height - 2*self.margin)

        return (x,y)


    def get_or_create_ctx(self, z_index, casing=False):
        """Get Cairo context for the z-index layer

        Create a new Cairo context if necessary.  
        :param z_index: z-index as float. The layers will be merged
             sorted by the z-Index.  
        :param casing: is the layer to be returned for cores (False)
             or for casings (True). In case of casings we return a
             layer for floor(z_index), ie. we will return the same
             layer for (0.1,True) and (0.2,True)
        :returns: CairoContext() for the layer we want
        """
        if casing:
            z_index = math.floor(float(z_index))
            try:
                ctx = self.casinglayers[z_index]
            except KeyError:
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
                ctx = cairo.Context(surface)
                ctx.set_antialias(self.antialias)
                self.casinglayers[z_index] = ctx
        else:
            #non-casing layer
            try:
                ctx = self.layers[float(z_index)]
            except KeyError:
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
                ctx = cairo.Context(surface)
                ctx.set_antialias(self.antialias)
                self.layers[float(z_index)] = ctx
        return ctx

    def get_minmax_layers(self):
        """examine all elements z-index and return the minimum and the
        maximim value (0 by default)"""
        minlayer, maxlayer = 0, 0

        for ele in self.osmparser.root:
            # skip unknown elements 
            if not ele.tag in ['node','way']:
                continue
            #rules is a dict like {width:1;color:'black'}
            for rules in ele.rules.values():           
                # get the z-index
                z_index = float(rules.get('z-index', 0))
                if z_index < minlayer: minlayer = z_index
                if z_index > maxlayer: maxlayer = z_index

        return minlayer, maxlayer


    def fill_image_pattern(self, imagepath, ctx):
        """fill current path with image"""
        try: image = cairo.ImageSurface.create_from_png (imagepath);
        except cairo.Error as e:
            logging.warning("Could not open icon path %s? Cairo returned: %s" % (imagepath, e))
            return
        pattern = cairo.SurfacePattern(image)
        pattern.set_extend(cairo.EXTEND_REPEAT)
        ctx.set_source(pattern)
        ctx.fill_preserve()

    def render_icon(self, iconpath, ele, ctx):
        """
        :param iconpath: file path to png icon image"""
        #get the x,y of the icon to be drawn
        if ele.tag == 'node':
            (x,y)=self.latlon2xy((float(ele.get('lat')),float(ele.get('lon'))))
        elif ele.tag == 'way':
            #simply draw in the middle of the bounding box for now
            #TODO: more elaborate algorythm where to place it.
            (x,y,x2,y2) = ctx.path_extents()
            x,y = x+ (x2-x)/2, y+(y2-y)/2
        else:
            return False
        #TODO: handle remote icon URLs
        # Load a .png image, center it and overlay on the regular layer
        try:
            surface = cairo.ImageSurface.create_from_png(iconpath)
        except cairo.Error as e:
            if e.args[0] == 'file not found':
                raise CSSException("Could not find icon file '%s'" % iconpath)
            raise
        #calculate offset to draw icon centered
        dy = surface.get_height()/2
        dx = surface.get_width()/2
        #final positions rounded to full pixels to avoid blurriness:
        x,y = round(x-dx), round(y-dy)
        ctx.set_source_surface(surface, x, y)
        #ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.paint();

    def find_longest_subpath(self, ctx):
        """Find the longest subpath of the current path and return the length of it and the subpath.

        This is usually used to determine whether a text fits on a
        path and where to print it."""
        #cairo.PATH_MOVE_TO: A move-to operation
        #cairo.PATH_LINE_TO: A line-to operation
        #cairo.PATH_CURVE_TO: A curve-to operation
        #cairo.PATH_CLOSE_PATH: A close-path operation
        #path_length(a,b)
        prev_point, cur_point = None, None
        ret_point1, ret_point2 = None, None
        max_dist  = None

        # get current path and find longest part
        for part in ctx.copy_path():
            #if MOVE TO, just set the current 
            if part[0] == cairo.PATH_MOVE_TO:
                length = 0         
                prev_point = part[1]    
                cur_point = part[1]
            elif part[0]==cairo.PATH_LINE_TO or \
                 part[0]==cairo.PATH_CURVE_TO:
                #treat curves as straight lines for now
                length = self.path_length(cur_point, part[1])
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

####### Ancestor
    def find_longest_subpath(self, ctx):
        """Find the longest subpath of the current path and return the length of it and the subpath.

        This is usually used to determine whether a text fits on a
        path and where to print it."""
        #cairo.PATH_MOVE_TO: A move-to operation
        #cairo.PATH_LINE_TO: A line-to operation
        #cairo.PATH_CURVE_TO: A curve-to operation
        #cairo.PATH_CLOSE_PATH: A close-path operation
        #path_length(a,b)
        prev_point, cur_point = None, None
        ret_point1, ret_point2 = None, None
        max_dist  = None

        # get current path and find longest part
        for part in ctx.copy_path():
            #if MOVE TO, just set the current 
            if part[0] == cairo.PATH_MOVE_TO:
                length = 0         
                prev_point = part[1]    
                cur_point = part[1]
            elif part[0]==cairo.PATH_LINE_TO or \
                 part[0]==cairo.PATH_CURVE_TO:
                #treat curves as straight lines for now
                length = self.path_length(cur_point, part[1])
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

    def way_draw_segment(self, x, y, ctl_xys, ctx):
        if ctl_xys is not None: #beziercurve, control points already in 'ctl_xys'
            cp1_x,cp1_y = ctl_xys.pop(0)
            cp2_x,cp2_y = ctl_xys.pop(0)
            ctx.curve_to(cp1_x,cp1_y,cp2_x,cp2_y,x,y)
        else: # no beziercurve:
            ctx.line_to(x,y)

    def way_path_to_ctx(self, way_obj, bezier, ctx):
        waynodes = list(way_obj.get_waynodes_xy(self))
        #if we beziercurve this, calculate the control points
        ctl_xys = None
        if bezier:
            ctl_xys = ceyx.utils.beziercurve(waynodes)
        #go to the first way point and draw from here
        x,y = waynodes[0]
        ctx.move_to(x,y)
        #render the way on the image
        for (x,y) in waynodes[1:]:
            self.way_draw_segment(x, y, ctl_xys, ctx)

    def relation_path_to_ctx(self, rel_obj, bezier, ctx):
        """Draws lines of a multipoligon on the image"""
        if len(rel_obj.members) == 0:
            return
        firstnode = None #first node of first line
        lastnode = None #last node of actual line
        member = rel_obj.members[0]
        while firstnode == None or firstnode != lastnode:
            waynodes = list(member.way.get_waynodes_xy(self))
            #if we beziercurve this, calculate the control points
            ctl_xys = None
            if bezier:
                ctl_xys = ceyx.utils.beziercurve(waynodes)
            #draw line either in normal or reversed order
            if waynodes[-1] == lastnode: #lastnode=None value will go to normal order
                for (x,y) in reversed(waynodes):
                    self.way_draw_segment(x, y, ctl_xys, ctx)
                lastnode = waynodes[0]
            else:
                for (x,y) in waynodes:
                    #go to the first way point and draw from here
                    if firstnode == None:
                        x,y = waynodes[0]
                        ctx.move_to(x,y)
                        firstnode = waynodes[0]
                    else:
                        self.way_draw_segment(x, y, ctl_xys, ctx)
                lastnode = waynodes[-1]

            #avoid running in circles on one line
            if len(rel_obj.members) == 1:
                break

            #find an adjoining line to last line
            new_member = None
            for next_member in rel_obj.members:
                if next_member == member:
                    continue
                waynodes = list(next_member.way.get_waynodes_xy(self))
                if waynodes[0] == lastnode or waynodes[-1] == lastnode:
                    new_member = next_member
                    break
            if new_member == None:
                #not closed relation, give up
                break
            else:
                member = new_member

    def render_way(self, ele, rules, z_index, ctx):
        """Render a single way or relation, on the Cairo context

        :returns: True on success, False on error"""
        # ctx.set_line_width should already be set to the core width, as
        # we are going to add casing-width to it
        render_obj = None
        bezier = rules.get('bezier', None)

        if ele.tag == 'relation':
            #a relation!
            for child in ele.findall('tag'):
                if child.get('k') != 'type':
                    continue
                if child.get('v') == 'multipolygon':
                    render_obj = Relationship()
                    render_obj.type = 'multipolygon'
                    render_obj.id = ele.get('id')
                    for child in ele.findall('member'):
                        member = RelMember()
                        member.type = child.get('type', 'outer') # better be 'way'
                        if member.type == 'node':
                            print "Ignoring a node as member of a multipolygon!"
                            continue
                        assert member.type == 'way'
                        #TODO: be smarter if nonexistant!
                        member.role = child.get('type', 'outer')
                        wayid = child.get('ref')
                        if not wayid:
                            print str((child.keys()))
                        render_obj.members.append(member)
                        way_ele = self.osmparser.root.find("way[@id='%s']" % wayid)
                        if way_ele is None:
                            logging.warn("Missing way %s in relation. Dropping relation", wayid)
                            return False
                        member.way = Way(self.osmparser, way_ele)
                    break
        else: #ele.tag == 'way'
            render_obj = Way(self.osmparser, ele)

        if isinstance(render_obj, Way):
            #add way path to cairo context
            self.way_path_to_ctx(render_obj, bezier, ctx)
        else: #Relation with many ways
            # only draw ODDly intersected areas by default to make multipolygons works sanely
            ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            self.relation_path_to_ctx(render_obj, bezier, ctx)

        try:
            casingwidth = float(rules.get('casing-width', 0))
        except ValueError:
            casingwidth = None

        #Do we need to draw casings?
        if (casingwidth and rules.get('casing-color', None)):
            #retrieve the matching casing layer
            casing_ctx = self.get_or_create_ctx(z_index, True)
            # need to go back to the first path coord and draw the original path
            #x,y = waynodes[0]
            #casing_ctx.move_to(x,y)

            #copy the path and draw it later
            path = ctx.copy_path()
            casing_ctx.append_path(path)

            #calculate the new casing width
            corewidth = ctx.get_line_width()
            casing_ctx.set_line_width(corewidth + 2 * casingwidth)

            #get casing line-styles, fall back to core ones:
            linecap = rules.get('casing-linecap', rules.get('linecap', None))
            if linecap == 'round':
                linecap = cairo.LINE_CAP_ROUND
            elif linecap == 'square':
                linecap = cairo.LINE_CAP_SQUARE
            else:
                #None, 'none', or some other value
                linecap = cairo.LINE_CAP_BUTT
            casing_ctx.set_line_cap(linecap)

            #set casing-linejoin
            linejoin = rules.get('casing-linejoin', rules.get('linecap', None))
            if linejoin == 'miter':
                linejoin= cairo.LINE_JOIN_MITER
            elif linejoin == 'bevel':
                linejoin = cairo.LINE_JOIN_BEVEL
            else:
                #None, 'round' or some other value
                linejoin = cairo.LINE_JOIN_ROUND
            casing_ctx.set_line_join(linejoin)

            # get the casing-color
            color = rules.get('casing-color','#000')
            (red,green,blue) = ceyx.utils.get_rgb(color)

            # get the casing-opacity
            try:
                opacity = float(rules.get('casing-opacity',1.0))
            except ValueError:
                opacity = 1
            if opacity < 1:
                casing_ctx.set_source_rgba(red, green, blue, opacity)
            else:
                casing_ctx.set_source_rgb(red, green, blue)

            #set casing-dashes
            dashes = rules.get('casing-dashes', None)
            #if property exists, split into a list of floats
            if dashes is not None:
                dashes = dashes.split(',')
                dashes = map(float, dashes)
                casing_ctx.set_dash(dashes)
            else: casing_ctx.set_dash([])

            #finally stroke the casing
            casing_ctx.stroke()

        #find fill-color and fill if needed
        color = rules.get('fill-color', None)
        if color is not None and color != 'none':
            (red,green,blue) = ceyx.utils.get_rgb(color)
            # get the fill-opacity (solid by default)
            try:
                fillopacity = float(rules.get('fill-opacity', 1.0))
            except ValueError:
                fillopacity = 1.0

            if fillopacity > 0.0 and fillopacity <= 1.0:
                origsource = ctx.get_source()
                if fillopacity < 1.0:
                    ctx.set_source_rgba(red, green, blue, fillopacity)
                else:
                    ctx.set_source_rgb(red, green, blue)
                ctx.fill_preserve()
                ctx.set_source(origsource)

        #fill way with image?
        #TODO: make sure this is a closed way for perf reasons?!
        fillimage = rules.get('fill-image', None)
        if fillimage is not None:
            self.fill_image_pattern(fillimage, ctx)

        #and finally stroke the path, but preserve it, so text
        #rendering can use it.
        ctx.stroke_preserve()

        #need to render text?
        self.textrenderer.render_text(ele, rules, ctx)
        return True

    def render_node(self, ele, rules, ctx):
        """Render a single way, according to the CSS rules on the Cairo context

        Assumes that the following ctx attributes have been set already:
           line_width, source color
        :returns: True on success, False on error"""
        #TODO: use existing node latlon in osmparser for perf? Measure!
        (x,y)=self.latlon2xy((float(ele.get('lat')),float(ele.get('lon'))))

        #get the width that was set earlier
        width = ctx.get_line_width()
        if width:
            #draw the circle path
            ctx.move_to(x + width/2,y)
            ctx.arc(x, y, width/2, 0, 2*math.pi)

            #get casing-width (double, to get casing-width to the outside)
            try:
                casingwidth = float(rules.get('casing-width', 0)) * 2
            except ValueError:
                casingwidth = None

            if casingwidth:
                # save to keep line width and color for the fill
                ctx.save()
                ctx.set_line_width(casingwidth)
                # set the casing-color
                color = rules.get('casing-color','#000')
                (red,green,blue) = ceyx.utils.get_rgb(color)
                ctx.set_source_rgb(red, green, blue)
                ctx.stroke_preserve()
                ctx.restore()
            ctx.fill()
        # render text on the node if necessary
        self.textrenderer.render_text(ele, rules, ctx)
        return True

    def render_layer(self, baselayer):
        """Render all elements within the integer range of baselayer"""
        for ele in self.osmparser.root:
            # skip unknown elements
            if not ele.tag in ['node','way','relation']:
                continue
            #draw each subpart as separate stroke/fill etc
            #rules is a dict like {width:1;color:'black'}
            for subpart, rules in ele.rules.items():
                # below, set the render style based on the mapcss style rules
                z_index = float(rules.get('z-index', 0))
                #if z-index is not in the current range, skip drawing this
                if math.floor(z_index) != baselayer:
                    continue

                ctx = self.get_or_create_ctx(z_index, False)

                #TODO: color for nodes means fill, and width for nodes diameter ?!

                #set width
                try:
                    width = float(rules.get('width', 0))
                except ValueError:
                    width = 0
                ctx.set_line_width(width)

                #TODO: abort rendering if neither width, nor text, nor fill-color, nor caption-width is set?

                #set dashes
                dashes = rules.get('dashes', None)
                #if property exists, split into a list of floats
                if dashes is not None:
                    dashes = dashes.split(',')
                    dashes = map(float, dashes)
                    ctx.set_dash(dashes)
                else: ctx.set_dash([])

                #set opacity
                try:
                    opacity = float(rules.get('opacity', 1.0))
                except TypeError:
                    opacity = 1

                #set linecap
                linecap = rules.get('linecap', None)
                if linecap == 'round':
                    linecap = cairo.LINE_CAP_ROUND
                elif linecap == 'square':
                    linecap = cairo.LINE_CAP_SQUARE
                else:
                    #linecap is None, 'none' or some other value
                    linecap = cairo.LINE_CAP_BUTT
                ctx.set_line_cap(linecap)

                #set linejoin
                linejoin = rules.get('linejoin', None)
                if linejoin == 'miter':
                    linejoin= cairo.LINE_JOIN_MITER
                elif linejoin == 'bevel':
                    linejoin = cairo.LINE_JOIN_BEVEL
                else:
                    #linejoin is None, 'round' or some other value
                    linejoin = cairo.LINE_JOIN_ROUND
                ctx.set_line_join(linejoin)

                #set color
                color = rules.get('color','#000000')
                (red,green,blue) = ceyx.utils.get_rgb(color)
                if opacity < 1:
                    ctx.set_source_rgba(red, green, blue, opacity)
                else:
                    ctx.set_source_rgb(red, green, blue)

                #HANDLE WAYS
                if ele.tag == 'way' or ele.tag == 'relation':
                    self.render_way(ele, rules, z_index, ctx)
 
                #HANDLE NODES
                elif ele.tag == 'node':
                    self.render_node(ele, rules, ctx)

                # render an image icon if needed
                iconpath = rules.get('icon-image', None)
                if iconpath:
                    self.render_icon(iconpath, ele, ctx)
                #Finally, delete the used paths before returning
                ctx.new_path()

    def render_png(self, osmparser, zoom, width, height):
        """render the data in osmparser into a png file
        :param zoom: Zoom level (int)
        :param width: Image width in pixel
        :param height: Image height in pixel, automatic is None
        """

        #init a new Textrenderer instance
        self.textrenderer = Textrenderer(self)

        #should we do antialiasing? Retrieve the generic
        #'antialiasing' rule for the osm element. Note: turning off
        #text-aliasing is not supported as it did not yield speed
        #improvements and is complex
        antialias = osmparser.root.rules[None].get('antialiasing','full')
        if antialias == 'full':
            self.antialias = cairo.ANTIALIAS_DEFAULT
        else:
            #antialiasing: 'text','none'
            self.antialias = cairo.ANTIALIAS_NONE

        self.osmparser = osmparser
        #make boundaries of rendering available to class
        self.set_boundaries(osmparser.bounds, height, width)

        #get the minimum and maximum layers to render
        minlayer, maxlayer = self.get_minmax_layers()
        minlayer = int(math.floor(minlayer))
        maxlayer = int(math.floor(maxlayer))

        ##Create the base layer onto which to merge everything
        #fill base layer with canvas color and opacity first.
        canvascolor = osmparser.root.rules[None].get('fill-color','#FFF')
        (r,g,b) = ceyx.utils.get_rgb(canvascolor)
        try:
            opacity = float(osmparser.root.rules[None].get('fill-opacity', 1.0))
        except ValueError:
            opacity = 1.0

        out_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        out_ctx = cairo.Context(out_surface)
        out_ctx.set_source_rgba(r,g,b,opacity)
        out_ctx.mask(cairo.SolidPattern(1, 1, 1))

        #fill canvas with image?
        canvasimage = osmparser.root.rules[None].get('fill-image')
        if canvasimage is not None:
            #create path, fill with image, and remove it with new_path
            out_ctx.rectangle(0,0,self.width, self.height)
            self.fill_image_pattern(canvasimage, out_ctx)
            out_ctx.new_path()
        #finished creating the base layer

        ##Go through all z-index elements within an integer range and
        ##render those, then merge them all into the base layer and
        ##repeat for the next integer range
        for base_layer in range(minlayer, maxlayer+1):
            #reset layers
            self.layers = {}
            self.casinglayers = {}

            self.render_layer(base_layer)

        #finally merge all the current z-index layers
        # get first layer and merge all the others in.

        #merge all the layers sorted by z-index.
            casing_indices = sorted(self.casinglayers.keys())
            for z_index in sorted(self.layers.keys()):
            #if there is a casinglayer with z-index <= the current z_index, merge that first.
                if len(casing_indices) and casing_indices[0] <= z_index:
                    z = casing_indices.pop(0)
                    ctx = self.casinglayers[z]
                    surface = ctx.get_target()
                    out_ctx.set_source_surface(surface, 0, 0)
                    out_ctx.set_operator(cairo.OPERATOR_OVER)
                    out_ctx.paint();
                    del(self.casinglayers[z])
                # merge the proper z-Index layer in
                ctx = self.layers[z_index]
                surface = ctx.get_target()
                out_ctx.set_source_surface(surface, 0, 0)
                out_ctx.set_operator(cairo.OPERATOR_OVER)
                out_ctx.paint();

        # Get the png data and return it
        #f = io.StringIO()
        f = io.BytesIO()
        out_surface.write_to_png(f)
        data = f.getvalue()

        #explicitely tear down textrenderer due to circular references  
        del(self.textrenderer)
        return(data)

