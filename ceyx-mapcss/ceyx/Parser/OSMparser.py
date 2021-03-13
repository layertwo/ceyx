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
from xml.etree import ElementTree
from ceyx.utils import Rect,Node

#-------------------------------------------------------------------------
class OSMparser(object):

    def __init__(self, filepath, lat1=None, lon1=None, lat2=None, lon2=None):
        """Read in an .osm data file in preparation for rendering

        The OSM parser adds fake :closed tags and transforms all
        foo=yes|true tags to foo=1.

        :param osmpath: Full filepath & name to the .osm data file
        :param lat/lon: lat/lon floats of the data boundary. If not
                       given, the boundaries will be a)taken from the
                       <bounds> element or b) calculated from all nodes
                       in the data.  Independent of this value OSMparser
                       will still read and hold all data to RAM.
        """
        self.bounds = Rect()
        self.osmpath=filepath
        tree = ElementTree.parse(filepath)
        self.root = tree.getroot()
        self.nodes = {}
        """a dict of dicts. {nodeid:latlon}"""
        droptags = ('created_by','source', 'FIXME','fixme','comment')

        # if given set data boundaries otherwise calculate them
        if lat1 is not None:
            self.set_bounds(lat1, lon1, lat2, lon2)
        else:
            self.find_bounds()

        #go through all elements and do stuff with them
        for ele in self.root.findall('*'):

            way_id = None
            if ele.tag == 'node':
                #find nodes and create a dict that contains { noderef:
                #{latlon: (lat,lon), ...}, ...}
                ndid    = int(ele.get("id"))
                # find nodes lat/lon and stuff it in the dict
                #TODO fail-proof against faulty data?
                try:
                    self.nodes[ndid]
                except KeyError:
                    #does not exist yet. So create the dicts
                    self.nodes[ndid]={}
                self.nodes[ndid]["latlon"] = (float(ele.get('lat')),
                                              float(ele.get('lon')))

            elif ele.tag == 'way':
                # if child is a way, test for a closed way and add ':closed' tag to it
                way_id = int(ele.get('id'))
                ndrefs = []

            #go through the list of children for the element and
            #1) drop unneccessary tags
            #2) transform foo=yes|true|True into foo=1
            #3) create a list of nodes in each way (needed for nested rules)

            for child in ele.getchildren():

                #drop a list of useless tags
                if child.tag == 'tag':
                    if child.get('k') in droptags:
                        continue

                    #if the tag has value yes|true, make it 1
                    if child.get('v') in ['yes', 'true', 'True']:
                        child.set('v','1')

                #if we established a wayid earlier (ele is a 'way')
                #and we found a node reference
                elif child.tag == 'nd' and way_id:
                    # create a list of node ids of the way
                    ndrefs.append(int(child.get('ref')))            

            #if the way contains a node (sanity check) and the
            #first and last node ids are identical, put in the
            #fake ':closed' tag.
            if way_id and len(ndrefs) and ndrefs[0] == ndrefs[-1]:
                tag = ElementTree.SubElement(ele, 'tag')
                tag.set('k',':closed')

                #next, in self.nodes[ndid]['wayids'] add a list of all
                #way ids that a node is referred in.  we need that
                #later in order to find the "parent" of an element for
                #nested mapCSS rules.
                for nd in ndrefs:
                    try:
                        self.nodes[ndid]['wayids']
                    except KeyError:
                        #does not exist yet. So create the list
                        self.nodes[ndid]['wayids'] = []
                        
                    self.nodes[ndid]['wayids'].append(way_id)

    def find_bounds(self):
        """Identify the lat/lon boundaries of the OSM data file.

           Saves the boundary info in the Nodes self.ul and self.lr."""
        # search for a bounds element that contains valid information
        bounds = self.root.find('bounds')
        if bounds is not None:
            self.bounds.ul.lat = float(bounds.get("maxlat"))
            self.bounds.lr.lat = float(bounds.get("minlat"))
            self.bounds.ul.lon = float(bounds.get("minlon"))
            self.bounds.lr.lon = float(bounds.get("maxlon"))
        # simply return if we got 4 boundaries, otherwise search all nodes
        if not (self.bounds.ul.lat is None or self.bounds.ul.lon is None or 
                self.bounds.lr.lat is None or self.bounds.lr.lon is None):
            return

        nodes = self.root.findall('node')
        for nd in nodes:
            lat, lon = float(nd.get('lat')), float(nd.get('lon'))
            if lat > self.bounds.ul.lat or self.bounds.ul.lat is None:
                self.bounds.ul.lat = lat
            if lat < self.bounds.lr.lat or self.bounds.lr.lat is None:
                self.bounds.lr.lat = lat
            if lon < self.bounds.ul.lon or self.bounds.ul.lon is None:
                self.bounds.ul.lon = lon
            if lon > self.bounds.lr.lon or self.bounds.lr.lon is None:
                self.bounds.lr.lon = lon

    def set_bounds(self, lat1=None, lon1=None, lat2=None, lon2=None):
        """Set the lat/lon boundaries of the OSM data file so we only
        render the relevant parts.

        Saves the boundary info in the Nodes self.ul and self.lr."""
        assert lat1 is not None, 'None passed to set_bounds'
        # if given set data boundaries otherwise calculate them
        self.bounds.ul.lat = max(lat1, lat2)
        self.bounds.lr.lat = min(lat1, lat2)
        self.bounds.ul.lon = min(lon1, lon2)
        self.bounds.lr.lon = max(lon1, lon2)

    def apply_styles(self, mapcss, zoom):
        """Apply a MapCSS at level zoom to the current data"""
        #find the rules for 'canvas' and apply them to the 'osm' element.
        #self.osmparser.root points to the <osm> tag and applies
        #'canvas' rules.
        ele = self.root
        rules = mapcss.apply_to_ele(ele, zoom)
        ele.rules = rules

        # then find the matching rules for all children and apply them to the element too.
        for ele in self.root:
            rules = mapcss.apply_to_ele(ele, zoom)
            ele.rules = rules
