#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2010. Authors:
# * Sebastian Spaeth
#    This file is part of spaetz' mapcss.
#
#    spaetz' mapcss is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    spaetz' mapcss is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with spaetz' mapcss.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------
import simplejson as json
import re
from ceyx.Parser.OSMparser import OSMparser
from ceyx.utils import Rect
from xml.etree import ElementTree
#-------------------------------------------------------------------------
class KothicJSparser(OSMparser):
    re_data_match = re.compile('onKothicDataResponse\((.*),(\d+),(\d+),(\d+)\);')

    def __init__(self, filepath, lat1=None, lon1=None, lat2=None, lon2=None):
        """Read in a KothicJS.js data file in preparation for rendering

        The OSM parser adds fake :closed tags and transforms all
        foo=yes|true tags to foo=1.

        :param filepath: Full filepath & name to the KothicJS .js data file
        :param lat/lon: boundaries can be given, but are always
            contained in the KothicJS, so these parameters can be
            ignored unless you know what you do for this backend.
        """
        self.bounds = Rect()
        self._granularity = None
        self.parse(filepath)

        # if given set data boundaries otherwise calculate them
        if lat1 is not None:
            self.set_bounds(lat1, lon1, lat2, lon2)
        else:
            self.find_bounds()

    def parse(self, filepath):
        with open(filepath) as f:
            m = KothicJSparser.re_data_match.match(f.read())
        if not m:
            raise Exception('No valid source')

        j = json.loads(m.group(1)) #main json object, the rest are z,x,y
        self.zoom = m.group(2)
        self.x    = m.group(3)
        self.y    = m.group(4)
        self._granularity = j.get('granularity', None)
        self._bbox = j.get('bbox', None) #4-element list with x1,y1,x2,y2
        data = j.get('features', None)
        del j

        self.root = ElementTree.Element("osm")
        for feature in data:
            head = ElementTree.SubElement(self.root, "ele")

    def find_bounds(self):
        """Identify the lat/lon boundaries from the data file.

           Saves the boundary info in the Nodes self.ul and self.lr."""
        # search for a bounds element that contains valid information
        if self._bbox:
            self.bounds.ul.lat = float(self._bbox[3])
            self.bounds.lr.lat = float(self._bbox[1])
            self.bounds.ul.lon = float(self._bbox[0])
            self.bounds.lr.lon = float(self._bbox[2])

if __name__ == '__main__':
  source = KothicJSSource()
  source.read('21049.js')
  source.parse()
