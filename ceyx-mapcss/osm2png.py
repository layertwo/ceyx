#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2010. Authors:
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

#TODO requires at least python 2.5 so test for that somewhere
from optparse import OptionParser
import sys
import os.path
import math
import time
import logging
import urllib2
from ceyx.OSMrenderer import OSMrenderer
from ceyx.Parser import OSMparser, KothicJSparser
from ceyx.MapCSS import MapCSS


#-------------------------------------------------------------------------
def num2deg(xtile, ytile, zoom):
    """This returns the NW-corner of the square.
    Use the function with xtile+1 and/or ytile+1 to get the other corners. With xtile+0.5 & ytile+0.5 it will return the center of the tile.""" 
    n = 2.0 ** int(zoom)
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return(lat_deg, lon_deg)

#-------------------------------------------------------------------------
class OSM2SVG(object):
    def __init__(self, datafile, cssfile, lat1=None, lon1=None, lat2=None, lon2=None):
        # load and parse the CSS
        starttime = time.time()
        self.mapcss    = MapCSS(cssfile)
        logging.info("OSM2SVG: Parsing CSS took %f" % (time.time()-starttime))

        # If datafile doesn't exist here, download and cache it:
        if not os.path.exists(datafile):
            if (lat1 and lon1 and lat2 and lon2) is None:
                raise UserWarning("Datafile does not exist and no boundaries given. Aborting.")
            logging.info("Datafile does not exist. Downloading data...")
            datafile = self.cache_data_or_download(lat1,lon1,lat2,lon2)
            if not datafile:
                raise UserWarning("ABORT: Could not download data file.")

        if datafile.lower().endswith('.osm'):
            osm_parser_class = OSMparser
        elif datafile.lower().endswith('.js'):
            osm_parser_class = KothicJSparser
        else:
            logging.info("OSM2SVG: No recognized data file, not doing anything.")
            return
        starttime = time.time()
        self.osmparser = osm_parser_class(datafile, lat1, lon1, lat2, lon2)
        logging.info("OSM2SVG: Parsing Data took %f" % (time.time()-starttime))
        
    def cache_data_or_download(self, lat1, lon1, lat2, lon2, cachedir='cache'):
        """ """
        datapath = os.path.join(cachedir, "%s%s%s%s.osm" %(lat1,lon1,lat2,lon2))
        if os.path.exists(datapath):
            logging.debug("Using cached data download")
            return datapath
        if not os.path.isdir(cachedir):
            os.mkdir(cachedir) #create folder if needed
        min_lat, max_lat = min(lat1, lat2), max(lat1, lat2)
        apiurl="http://openstreetmap.org/api/0.6/map?bbox=%f,%f,%f,%f" % (lon1, min_lat, lon2, max_lat)
        logging.debug("Retrieve '%s'" % apiurl)
        try:
            data = urllib2.urlopen(apiurl)
        except urllib2.HTTPError as e:
            logging.error("Downloading from API failed.")
            raise e
        with open(datapath,"w") as file:
            #TODO, on failure remove the file again
            file.write(data.read())
        return datapath

    def apply_css(self, zoom):
        """Apply the css rules to the osm data

        :param zoom: Zoom level to apply the rules to
        :returns: Raises exception if no success."""
        self.zoom = zoom
        starttime = time.time()
        self.osmparser.apply_styles(self.mapcss, zoom)
        logging.info("Applying CSS styles to %d elements took %f\n" %\
                         (len(self.osmparser.root), time.time()-starttime))

    def render(self, width, height, outfilepath=None):
        """Render the osm data with the specified parameters

        You need to explicitly apply_css() before invoking render().
        :param width: Image width in pixel
        :param height: Image height in pixel, automatic if None
        :param outfile: filename or stdout if None
        :returns: True on success, or None otherwise."""
        starttime = time.time()
        renderer = OSMrenderer()
        png = renderer.render_png(self.osmparser, self.zoom, width, height)
        logging.info("Rendering at zoom level %d took %f\n" % (self.zoom, time.time()-starttime))

        if png is None:
            sys.stderr.write("No PNG returned.\n")
            return None

        if outfilepath:
            f = open(outfilepath,"wb")
            f.write(png)
            f.close()
        else:
            sys.stdout.write(png)

#-------------------------------------------------------------------------
if __name__=='__main__':
    LOGFORMAT = '%(levelname)s: %(message)s'
    logging.basicConfig(format=LOGFORMAT)
    usage="Usage: osm2png.py [options] [datafile]"
    parser = OptionParser(usage=usage)
    #TODO: allow the specification of an output file
    parser.add_option("-d", "--data", type="string", dest="datafile", 
                      default="data.osm",
                      help="location of .osm data file (default: data.osm)")
    parser.add_option("-r", "--rule", type="string", dest="cssfile", 
                      default="style.mapcss",
                      help="location of .mapcss rule file (default: "
                      "style.mapcss)")
    parser.add_option("-o", "--outfile", type="string", dest="outfile",
                      default=None,
                      help="Name of .png file to write to (use - for STDOUT). "
                      "(default: map<z>.png). In batch render mode, it speci"
                      "fies the directory under which we store <odir>/<zoom>/<"
                      "x>/<y>.png.")
    parser.add_option("--xy", type="string", dest="xy", default=None, 
                      metavar= 'x,y',
                      help="Explicitely give image boundaries for tile x,y at "
                      "initial zoom level.")
    parser.add_option("--batch", type="string", dest="batch", default=None, 
                      metavar= 'x,y',
                      help="Render x*y tiles (to the right and bottom) using "
                      "the data set")
    parser.add_option("-b", "--bounds", type="string", dest="bounds", 
                      default=None,
                      help="Explicitely give image boundaries in lat1,lon1,"
                      "lat2,lon2. Overrides any given -xy option (default: "
                      "determine from data)")
    parser.add_option("-z", "--zoom", type="string", dest="level", default="12",
                      help="Zoom level to render ('12', '11-13')(default 12)", 
                      metavar="zoom")
    parser.add_option("-s", "--size", dest="size", default=None,
                      help="Image dimensions as <width>[x<height>]. Square "
                      "image if 'aspect-ratio' is not given. (default  256 ** "
                      "max(0,(z-12)))")
    parser.add_option("-a", "--aspect-ratio", action="store_true", dest="ratio",
                      default=False,
                      help="Preserve image aspect ratio by adapting height")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout (unused yet)")
    (options, args) = parser.parse_args()

    # Sanity checks
    if sys.version_info < (2, 5):
        logging.error("Ceyx requires python 2.5 or greater")
        sys.exit(1)
    if not os.path.exists(options.cssfile):
        logging.error("CSS rule file does not exist.")
        sys.exit(1)

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # if datafile has been given as positional arg (without --d), use that
    if args:
        options.datafile = args.pop(0)

    #explicit zoom level given?
    try:
       options.level = [int(options.level)] # single number
    except ValueError:
       dashpos = options.level.find('-')
       options.level = list(range(int(options.level[:dashpos]),
                             int(options.level[dashpos+1:])+1))

    lat1,lon1,lat2,lon2 = None, None, None, None
    xtile, ytile = 0, 0
    # lat/lon boundaries explicitely given?
    if options.bounds:
        try:
            lat1,lon1,lat2,lon2 = list(map(float, options.bounds.split(',')))
        except ValueError:
            logging.error("Need 4 values for bounds in "
                             "'lat1,lon1,lat2,lon2' format.\n")
            sys.exit(1)

    # boundaries explicitely given by specifying xy tile?
    elif options.xy:
        try:
            xtile, ytile = list(map(float,options.xy.split(',')))
        except ValueError:
            logging.error("Need 2 values for tile coords 'x,y' format.\n")
            sys.exit(1)

        #calculate image boundaries for x,y at initial zoom level
        lat1,lon1 = num2deg(xtile, ytile, options.level[0])
        lat2,lon2 = num2deg(xtile+1, ytile+1, options.level[0])
        logging.debug("Using boundaries: %f,%f,%f,%f" % (lat1,lon1,lat2,lon2))

    #Do we want to batch render multiple tiles in one go?
    if options.batch:
        if lat1 is None:
            #if any of lat1,lon1,lat2,lon2 is still None, no explicit
            #boundaries had been specified, but we need that for batch
            #rendering.
            logging.error("No explicit boundaries given (-xy, or -b),"
                          "so we cannot do batch rendering without.\n")
            sys.exit(1)
        try:
            numx, numy = list(map(int,options.batch.split(',')))
        except ValueError:
            logging.error("Need 2 values for batch numbers in 'x,y' format.\n")
            sys.exit(1)
        batch_bounds = []
        for x in range(numx):
            for y in range(numy-1, -1, -1):
                # format [(x,y), lat1, lon1, lat2, lon2),...]
                batch_bounds.append(((x+xtile, y+ytile),
                                    lat1+(lat2-lat1)*y, lon1+(lon2-lon1)*x,
                                    lat1+(lat2-lat1)*(y+1), lon1+(lon2-lon1)*(x+1)))
    # image size given explicitely?
    if options.size:
        try:
            #'512' or '512x1024' format?
            if 'x' in options.size.lower():
                (size, height) = options.size.lower().split('x')
            else:
                size   = options.size
                height = options.size

            size, height = int(size), int(height)
        except ValueError:
            logging.error("Invalid size option '%s' given." % options.size)
            sys.exit(1)

   #load data and css
    osm2svg = OSM2SVG(options.datafile, options.cssfile, lat1, lon1, lat2, lon2)

    for level in options.level:
        start_time = time.time() # how long does render take?
        # apply the CSS rules to our OSM data for this level
        osm2svg.apply_css(level)
        css_time = time.time() - start_time # how long does render take?

        #calculate the size of the image to be used for this level
        if options.size is None:
           size  = 2 ** max(8,(level - 4))
           height= size

        if options.ratio:
           # calculate height automatically
           height=None

        if options.batch:
           # batch render all batch_bounds
           for (xy, lat1, lon1, lat2, lon2) in batch_bounds:
               # File name in batch rendering:
               outfile = str(level) #start with zoom dir
               if options.outfile:
                   outfile = os.path.join(options.outfile, str(level))
               # Create zoom dir if needed
               if not os.path.isdir(outfile): os.mkdir(outfile)
               # append /x/ dir to outfile 
               outfile = os.path.join(outfile, "%d"%xy[0])
               if not os.path.isdir(outfile): os.mkdir(outfile)
               # append <y>.png
               outfile = os.path.join(outfile, "%d.png" % xy[1])
               start_time = time.time()
               osm2svg.osmparser.set_bounds(lat1, lon1, lat2, lon2)
               osm2svg.render(size, height, outfilepath= outfile)
               logging.info("CSS + Render level %d took %f\n"\
                                % (level, time.time()-start_time + css_time))

        else:
           # No batch rendering
           if options.outfile is None:
               outfile = "map%d.png" % level
           elif options.outfile == '-':
               #use stdout
               outfile = None
           else: outfile = options.outfile

           start_time = time.time()
           osm2svg.render(size, height, outfilepath= outfile)
           logging.info("CSS + Render level %d took %f\n"\
                            % (level, time.time()-start_time + css_time))
