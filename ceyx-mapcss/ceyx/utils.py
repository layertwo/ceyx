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
from hashlib import md5
from math import sqrt
#-------------------------------------------------------------------------
class Node(object):
    def __init__(self):
        self.lat = None
        self.lon = None

    def __str__(self):
        return "lat: %s lon: %s" % (self.lat, self.lon)

class Rect(object):
    def __init__(self):
        self.ul = Node()
        self.lr = Node()

    def __str__(self):
        return "ul: %s lr: %s" % (self.ul, self.lr)
#-------------------------------------------------------------------------

# colormap for colors snatched from PIL (Python Imaging Library)
# which is probably the colors from here: http://www.w3.org/TR/css3-color/#svg-color
colormap = {'aliceblue': '#f0f8ff',
                'antiquewhite': '#faebd7',
                'aqua': '#00ffff',
                'aquamarine': '#7fffd4',
                'azure': '#f0ffff',
                'beige': '#f5f5dc',
                'bisque': '#ffe4c4',
                'black': '#000000',
                'blanchedalmond': '#ffebcd',
                'blue': '#0000ff',
                'blueviolet': '#8a2be2',
                'brown': '#a52a2a',
                'burlywood': '#deb887',
                'cadetblue': '#5f9ea0',
                'chartreuse': '#7fff00',
                'chocolate': '#d2691e',
                'coral': '#ff7f50',
                'cornflowerblue': '#6495ed',
                'cornsilk': '#fff8dc',
                'crimson': '#dc143c',
                'cyan': '#00ffff',
                'darkblue': '#00008b',
                'darkcyan': '#008b8b',
                'darkgoldenrod': '#b8860b',
                'darkgray': '#a9a9a9',
                'darkgreen': '#006400',
                'darkgrey': '#a9a9a9',
                'darkkhaki': '#bdb76b',
                'darkmagenta': '#8b008b',
                'darkolivegreen': '#556b2f',
                'darkorange': '#ff8c00',
                'darkorchid': '#9932cc',
                'darkred': '#8b0000',
                'darksalmon': '#e9967a',
                'darkseagreen': '#8fbc8f',
                'darkslateblue': '#483d8b',
                'darkslategray': '#2f4f4f',
                'darkslategrey': '#2f4f4f',
                'darkturquoise': '#00ced1',
                'darkviolet': '#9400d3',
                'deeppink': '#ff1493',
                'deepskyblue': '#00bfff',
                'dimgray': '#696969',
                'dimgrey': '#696969',
                'dodgerblue': '#1e90ff',
                'firebrick': '#b22222',
                'floralwhite': '#fffaf0',
                'forestgreen': '#228b22',
                'fuchsia': '#ff00ff',
                'gainsboro': '#dcdcdc',
                'ghostwhite': '#f8f8ff',
                'gold': '#ffd700',
                'goldenrod': '#daa520',
                'gray': '#808080',
                'green': '#008000',
                'greenyellow': '#adff2f',
                'grey': '#808080',
                'honeydew': '#f0fff0',
                'hotpink': '#ff69b4',
                'indianred': '#cd5c5c',
                'indigo': '#4b0082',
                'ivory': '#fffff0',
                'khaki': '#f0e68c',
                'lavender': '#e6e6fa',
                'lavenderblush': '#fff0f5',
                'lawngreen': '#7cfc00',
                'lemonchiffon': '#fffacd',
                'lightblue': '#add8e6',
                'lightcoral': '#f08080',
                'lightcyan': '#e0ffff',
                'lightgoldenrodyellow': '#fafad2',
                'lightgray': '#d3d3d3',
                'lightgreen': '#90ee90',
                'lightgrey': '#d3d3d3',
                'lightpink': '#ffb6c1',
                'lightsalmon': '#ffa07a',
                'lightseagreen': '#20b2aa',
                'lightskyblue': '#87cefa',
                'lightslategray': '#778899',
                'lightslategrey': '#778899',
                'lightsteelblue': '#b0c4de',
                'lightyellow': '#ffffe0',
                'lime': '#00ff00',
                'limegreen': '#32cd32',
                'linen': '#faf0e6',
                'magenta': '#ff00ff',
                'maroon': '#800000',
                'mediumaquamarine': '#66cdaa',
                'mediumblue': '#0000cd',
                'mediumorchid': '#ba55d3',
                'mediumpurple': '#9370db',
                'mediumseagreen': '#3cb371',
                'mediumslateblue': '#7b68ee',
                'mediumspringgreen': '#00fa9a',
                'mediumturquoise': '#48d1cc',
                'mediumvioletred': '#c71585',
                'midnightblue': '#191970',
                'mintcream': '#f5fffa',
                'mistyrose': '#ffe4e1',
                'moccasin': '#ffe4b5',
                'navajowhite': '#ffdead',
                'navy': '#000080',
                'oldlace': '#fdf5e6',
                'olive': '#808000',
                'olivedrab': '#6b8e23',
                'orange': '#ffa500',
                'orangered': '#ff4500',
                'orchid': '#da70d6',
                'palegoldenrod': '#eee8aa',
                'palegreen': '#98fb98',
                'paleturquoise': '#afeeee',
                'palevioletred': '#db7093',
                'papayawhip': '#ffefd5',
                'peachpuff': '#ffdab9',
                'peru': '#cd853f',
                'pink': '#ffc0cb',
                'plum': '#dda0dd',
                'powderblue': '#b0e0e6',
                'purple': '#800080',
                'red': '#ff0000',
                'rosybrown': '#bc8f8f',
                'royalblue': '#4169e1',
                'saddlebrown': '#8b4513',
                'salmon': '#fa8072',
                'sandybrown': '#f4a460',
                'seagreen': '#2e8b57',
                'seashell': '#fff5ee',
                'sienna': '#a0522d',
                'silver': '#c0c0c0',
                'skyblue': '#87ceeb',
                'slateblue': '#6a5acd',
                'slategray': '#708090',
                'slategrey': '#708090',
                'snow': '#fffafa',
                'springgreen': '#00ff7f',
                'steelblue': '#4682b4',
                'tan': '#d2b48c',
                'teal': '#008080',
                'thistle': '#d8bfd8',
                'tomato': '#ff6347',
                'turquoise': '#40e0d0',
                'violet': '#ee82ee',
                'wheat': '#f5deb3',
                'white': '#ffffff',
                'whitesmoke': '#f5f5f5',
                'yellow': '#ffff00',
                'yellowgreen': '#9acd32'}

def get_rgb(color):
    """Convert a color specification into (r,g,b) format
    
    :param color: The color specification as string in #123456 or
                  #123 format.  It also accepts color specifications. In
                  #case of unknown names it will use the first 6
                  #hexadecimal chars of the md5() of the color name. This
                  #way you can do eval('color=tag(name)').
    :returns: 3-tuple (r,g,b) as floats between 0.0 - 1.0
    """
    if color[0] != '#':
        try: 
            color =  colormap[color]
        except KeyError:
            color = '#%s' % ( md5(color).hexdigest()[:6] )

    if len(color) == 4:
        r,g,b = int(color[1]*2,16)/15.0,int(color[2]*3,16)/15.0,int(color[3]*2,16)/15.0
    elif len(color) == 7:
        r,g,b = int(color[1:2],16)/15.0,int(color[3:4],16)/15.0,int(color[5:6],16)/15.0
    else:
        raise CSSException('Invalid color specification (%s)' % color)
    return (r,g,b)


def beziercurve(xy):
    """is handed a list of (x,y) tuples of a path and returns a list
    of 2*xy - 2 control points that can be used to draw bezier curves.
    Algorithm based on: 
    http://www.antigrain.com/research/bezier_interpolation/index.html
    """
    cp = list()

    # closed area or nonclosed path?
    closed = (xy[0][0]==xy[-1][0]) & (xy[0][1]==xy[-1][1])

    if closed:
        startpoint = 0
    else:
        # first control point is 1st point
        startpoint = 1
        cp.append(xy[0])

    for index in range(startpoint, len(xy)-1):
        if index==0:
            #if closed, use second last point for cp calc
            x1,y1 = xy[-2]
        else:
            x1,y1 = xy[index-1]
        x2,y2 = xy[index]
        x3,y3 = xy[index+1]
      
        L1=path_length((x2,y2),(x1,y1))
        L2=path_length((x3,y3),(x2,y2))
        C1=0.5 * (x1+x2), 0.5 *(y1+y2)
        C2=0.5 * (x2+x3), 0.5 *(y2+y3)
        C1x, C1y = C1
        C2x, C2y = C2
      
        if (L1+L2==0) or (C2x==C1x) or (C2y==C1y):
            #if impossible, just use the point as control points
            cp.append(xy[index])
            cp.append(xy[index])
        else:
            #usually just calculate the control points properly:
            Mx = L1/(L1+L2) * (C2x - C1x) + C1x
            My = L1/(L1+L2) * (C2y - C1y) + C1y 
            cp1x,cp1y = C1x-Mx + x2, C1y-My + y2
            cp2x,cp2y = C2x-Mx + x2, C2y-My + y2      

            cp.append((cp1x,cp1y))
            cp.append((cp2x,cp2y))

    if closed:
        #closed way: use first calculated CP as very last one
        cp1 = cp.pop(0)
        cp.append(cp1)
    else:
        #last control point is last point
        cp.append(xy[-1])
    return cp

def path_length(a, b, c1=None, c2=None):
    """Returns the Euclidian distance between points
    
    Calculates the path length between a and b if c1,c2 are None,
    otherwise it takes c* as control points for a beziercurve and
    calculates the length of the beziervurve.
    :param a,b: sequence with x and y in first and second element.
    :returns: distance as float or None on error."""
    return sqrt(pow(a[0]-b[0],2)+pow(a[1]-b[1],2))
