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
import re
import os.path
import logging
from xml.etree import ElementTree

class CSSException(Exception):
    pass

#-------------------------------------------------------------------------
class CSSRule(object):
    """A CSS rule represents a single map style rule.

    It consists out of an 'ele'ment, a |selector, .possibly
    :pseudoclassesa [filter]::subpart {rules}.

    A rule can only apply to one subpart (if specified), or to all
    subparts (if None), or to the '__unnamed__' subpart if subpart==''.
    """
    #Regexes to find the operators
    #binary ::= "=" | "!=" | "=~" | "<" | ">" | "<=" | ">=";
    RE_op_binary = re.compile('["\']?([:_\w]+)["\']?\s*(!=|=~|=|<=|>=<|>)\s*(.*)$')

    def __init__(self):
        self._ele = None
        self._filter = []
        self._rules = {}
        self._subpart = None

    def test_zoom(self, zoom):
        """Tests if the zoom level (selector) applies to this style

        :returns: True/False indicating whether this style applies to zoom level 'zoom'
        """
        #if style does not have a selector we always return True
        if self.selector is None: return True
        #here we know that selector is set, so self._minzoom and self._maxzoom should be available
        #selector but no zoom set -> False
        if zoom is None: return False
        return (zoom >= self._minzoom and zoom <= self._maxzoom)

    def test_filter(self, ele):
        """Test if this ele passes the style's filter rules
        
        This function will not check the selector, use `test_zoom` for
        that, this is just concerned with the bits in the brackets
        []. It is also not concerned about a matching "subpart" that
        will also have to be checked separately.

        Also note that the MapCSS class and this function will not
        do anything to make the pseudo-class :closed work (which
        applies to all closed ways). Adding a ':closed' tag has to be
        done by the OSM parser at parsing time.

        :param ele: The element 'node','way','relation' to check (an
                    ElementTree Element).

        :returns: True if it matches the filter, False otherwise"""
        # a filter can be 'highway', '!highway' 'highway=foo', highway="foo",
        #operators: binary ::= "=" | "!=" | "=~" | "<" | ">" | "<=" | ">=";

        # retval holds the function return value: Default to True
        retval = True

        for filter in self.filter:
            #to be filled with: negate: should the rule result be inverted?
            #tag_exists: Does the tag in the filter rule exist in 'ele'?
            #left hand, right hand, and operator string of test
            negate, lh, rh, operator = False, None, None, None

            # assume this filter does not match
            filter_result = False

            #Negate test, e.g. test for the nonexistence of a tag?
            if filter[0] == '!':
                negate = True
                filter = filter[1:]

            #check if there might be a binary operator in this rule
            #find lh, operator and rh of this rule
            m = CSSRule.RE_op_binary.match(filter)
            if m:
                #m.group(1) (the negation symbol ! or ''
                lh = m.group(1)       #left hand tag
                operator = m.group(2) #binary operator symbol
                rh = m.group(3)       #right hand expression
            else:
                #if no operator found, put the whole tag in lh (existence check)
                lh = filter

            #find all childnodes with tag 'lh' and test the filter
            #XXX ElementTree 1.3 can do nice Xpath stuff, we need to search manually
            for child in ele.findall('tag'):
                if child.get("k") == lh:
                    #the filter tag exists in 'ele'
                    tag_value  = child.get("v",None)
                    if operator == None:
                        filter_result = True
                    elif operator == '=':
                        if tag_value == rh:
                            filter_result = True
                    elif operator == '!=':
                        if tag_value != rh:
                            filter_result = True
                    elif operator == '<':
                        if float(tag_value) < float(rh):
                            filter_result = True
                    elif operator == '<=':
                        if float(tag_value) <= float(rh):
                            filter_result = True
                    elif operator == '>=':
                        if float(tag_value) >= float(rh):
                            filter_result = True
                    elif operator == '>':
                        if float(tag_value) > float(rh):
                            filter_result = True
                    elif operator == '=~':
                        #test regex, strip surrounding slashes
                        rh = rh.strip('/')
                        if re.search(rh, tag_value):
                            filter_result = True
                    else:
                        raise CSSException('Unknown operator (%s) in filter' %
                                           (operator, filter))

                #we can stop if the filter hit
                if filter_result:
                        break

            #if this filter did not match, overall return value is False
            #invert filter result if 'negate'
            if  filter_result ^ negate == False:
                retval = False
                break

        return retval


    def _get_id(self):
        try:
            return self._id
        except AttributeError:
            return None
    def _set_id(self, id):
       self._id = id
    id = property(_get_id, _set_id)

    def _get_ele(self):
       return self._ele

    def _set_ele(self, ele):
       """'ele' can either be set by using the enum or strings

       ie. cssrule.ele(MapCSS.node) or cssrule.ele('node') should both work
       """
       # first interprete 'ele' as string. If that does not work see if we got the numeric
       # enum value and use that. Bail out if 'ele' is not a recognized element
       try:
           self._ele = ['canvas','node','way','relation'].index(ele)
       except ValueError:
           # already in int/enum format?
           try:
               self._ele = int(ele)
           except ValueError:
               raise CSSException("Invalid CSS: '%s' must be one of 'canvas', 'node','way', or 'relation'." % ele)
    ele = property(_get_ele, _set_ele)

    def _get_selector(self):
        try:
            return self._selector
        except AttributeError:
            return None

    def _set_selector(self, selector):
       self._selector = selector
       # in case selector is 'z11' or 'z2-6', set min and max zoom levels
       if selector[0] == 'z':
           dashpos = selector[1:].find('-')
           if  dashpos == -1:
               # assume only a single numeric zoom level has been passed in
               [self._minzoom, self._maxzoom] = [int(selector[1:])] * 2
           else:
               # assume z3-7, z-11, or z3- format
               # set minzoom = 0 if empty and maxzoom=100 if empty
               self._minzoom = selector[1:dashpos+1]
               self._maxzoom = selector[dashpos+2:]
               if self._minzoom == '':
                   self._minzoom = 0
               if self._maxzoom == '':
                   self._maxzoom = 100

               self._minzoom = int(self._minzoom)
               self._maxzoom = int(self._maxzoom)
       else:
           raise CSSException("Invalid selector (%s) in rule" % selector)

    selector = property(_get_selector, _set_selector)

    def _get_filter(self):
       return self._filter

    def _set_filter(self, filter):
       self._filter = filter
    filter = property(_get_filter, _set_filter)

    def _get_subpart(self):
       return self._subpart

    def _set_subpart(self, subpart):
       self._subpart = subpart
    subpart = property(_get_subpart, _set_subpart)

    def _get_rules(self, subpart=None):
       return self._rules

    def _set_rules(self, rules, subpart=None):
       self._rules = rules
    rules = property(_get_rules, _set_rules)
    """Rules are a dict of rules, such as {'z-index':9,'width':3,...}"""

    def __str__(self):
       return str(self.ele) + " Selector: " + str(self.selector) + \
           " Filter: " + str(self.filter) + "\nRules: " + str(self.rules)

#-------------------------------------------------------------------------
class MapCSS(object):
    """This class parses mapcss files, contains a list of rules and is able to apply
    suitable styles to an element."""
    #ENUM for 'ele'
    canvas = 0
    node = 1
    way  = 2
    relation = 3

    re_rules = re.compile("(.*){(.*)}\s*$", re.S)
    """Used to split a CSS rule into a ele/selector/predicate part and a {rule} part."""
    re_nextword = re.compile(r"(?P<ws>\s*)(?P<word>([.,|]|:{1,2})?[-\w]*)(?P<rest>.*)$", re.S)
    """Used in order to split off the next word from the CSS blob
       Words can start with [.:,|] and contain alphanumerics and -_ otherwise.
       Available groups: 'ws': initial white space, 'word', and 'rest'"""
    re_filter= re.compile(r"""
       \s*\[                  ## initial whitespace and opening bracket
       ((([^'"\]]+)|("[^"]*")|('[^']*'))+? ##skip quotations and non-closing brackets
       )\]                    ## closing bracket
       """, re.VERBOSE|re.MULTILINE)
    """Used to find the inside of a [filter]"""


    def __init__(self, cssfile):
        self.rules   = [[],[],[],[]]
        """A list of
        [[CSSRule(),..],[CSSRule(),..],[CSSRule(),..],[CSSRule(),..],]
        that apply to 'canvas', 'node', 'way', and 'relation'
        respectively.  The id of the rule is set as to the index in
        this list, so make sure you don't remove rules as re-adding
        might lead to confusion with ids.
        """
        self.parseCSS_file(cssfile)


    def remove_comments(self, text):
        """Remove c-style comments from string 'text'

        This function was snatched from
        http://www.saltycrane.com/blog/2007/11/remove-c-comments-python/
        :param text: blob of text with comments (can include newlines)
        :returns: text with comments removed
        """
        pattern = r"""
                            ##  --------- COMMENT ---------
           /\*              ##  Start of /* ... */ comment
           [^*]*\*+         ##  Non-* followed by 1-or-more *'s
           (                ##
             [^/*][^*]*\*+  ##
           )*               ##  0-or-more things which don't start with /
                            ##    but do end with '*'
           /                ##  End of /* ... */ comment
         |                  ##  -OR-  various things which aren't comments:
           (                ## 
                            ##  ------ " ... " STRING ------
             "              ##  Start of " ... " string
             (              ##
               \\.          ##  Escaped char
             |              ##  -OR-
               [^"\\]       ##  Non "\ characters
             )*             ##
             "              ##  End of " ... " string
           |                ##  -OR-
                            ##  ------ ' ... ' STRING ------
             '              ##  Start of ' ... ' string
             (              ##
               \\.          ##  Escaped char
             |              ##  -OR-
               [^'\\]       ##  Non '\ characters
             )*             ##
             '              ##  End of ' ... ' string
           |                ##  -OR-
                            ##  ------ ANYTHING ELSE -------
             .              ##  Anything other char
             [^/"'\\]*      ##  Chars which doesn't start a comment, string
           )                ##    or escape
    """
        regex = re.compile(pattern, re.VERBOSE|re.MULTILINE|re.DOTALL)
        noncomments = [m.group(2) for m in regex.finditer(text) if m.group(2)]

        return "".join(noncomments)


    def addCSSrule(self, rule):
        """Parse a single CSS rule and add it to the internal representation of rules"""

        #create a one new and empty CSSRule
        cssrule = CSSRule()

        # next_possible_token values are concats of:
        #   1: 'way|node|relation': new rule or nested rule
        #   2: ',':next rule element starts
        #   4: '|': selector
        #   8: '.':tag existence filter (classes) or
        #      ':':pseudo-class existence
        #  16: '[':filter list starts
        #  32: '::' subpart label (after filter bracket)

        #split elements/selectors/predicates (esp) in one and {rules} in second part
        try:
            esp, rules = MapCSS.re_rules.match(rule).groups()
        except AttributeError:
            raise CSSException("Invalid CSS: Malformed rule:\n'%s'" % rule.strip())

        # parse all elements of esp, looking for tokens that we can use:
        next_possible_token = 1 #first ele must be way|node|relation
        while esp:
            handled_token = False
            match = MapCSS.re_nextword.match(esp)

            #just whitespace left? Finish
            if match and match.group('word') == '' and match.group('rest')=='':
                esp=''
                continue

            #consider options if we found a word
            if match and match.group('word') > '':
                word = match.group('word')

                # next element can be way|node|relation?
                if next_possible_token & 1 and \
                        word in (('canvas','node','way','relation')):
                    # get next word from 'esp' (splits in 2 m.groups)
                    # This should be the 'element' of the rule
                    handled_token = True
                    #if cssrule.ele is set, we already got an element, so this is the start of a nested rule
                    if cssrule.ele:
                        raise CSSException("Invalid CSS: Not yet handled nested rules in:\n'%s'" % (esp))
                    cssrule.ele = word
                    esp = match.group('rest')
                    #got element, next possible tokens are: element (nested), or ',.:['
                    next_possible_token = 1|2|4|8|16
                    continue

                # next element is ','?
                if next_possible_token & 2 and word[0] == ',':
                    # recursively add the 2nd part of our rules also to the list of CSSRules
                    # set the 'esp' string to '' to mark as handled.
                    handled_token = True
                    commapos = esp.find(',')
                    newesp = esp[commapos+1:] #esp behind the comma
                    if newesp.strip(): #any esp but space behind comma? recurse
                        newrulestr = "%s {%s}" % (newesp, rules)
                        self.addCSSrule(newrulestr)
                    esp = ''
                    next_possible_token = 0
                    continue

                # next element is selector '|'?
                if next_possible_token & 4 and word[0] == '|':
                    handled_token = True
                    #pass the word in as selector (sans the '|')
                    cssrule.selector = word[1:]
                    esp = match.group('rest')
                    #got element, next possible tokens are: element (nested), or ',.:['
                    next_possible_token = 1|2|4|8|16
                    continue

                # next element is subpart '::'?
                if next_possible_token & 32 and word[0:2] == '::':
                    # split off the filter (next_word is not good enough) and add it to the CSS filter list
                    cssrule.subpart=word[2:]
                    # ::* is an alias for all subparts
                    if word == '::*':
                        cssrule.subpart= None
                    # handle the rest of the string
                    esp = match.group('rest')
                    handled_token = True
                    #got element, next possible tokens are: element (nested), or ',.:[' or '::'
                    next_possible_token = 2
                    continue

                # next element is class filter '.' or ':'?
                if next_possible_token & 8 and word[0] in ['.',':']:
                    handled_token = True
                    # the tag existence test .foo or :closed is really just a shortcut for [.foo] [:closed]
                    # so add that filter. Split off the tag and the rest of esp
                    #                cssrule.filter.append(m.group(1))
                    #                esp = m.group(2).strip()
                    cssrule.filter.append(word)
                    esp = match.group('rest')
                    #got element, next possible tokens are: element (nested), or ',.:['
                    next_possible_token = 1|2|4|8|16
                    continue

            # next element is filter '['? This does not match the
            # next_word regex, so we need to consider it separate
            if next_possible_token & 16 and esp.lstrip().startswith('['):
                handled_token = True
                # split off the filter (next_word is not good enough) and add it to the CSS filter list
                m = MapCSS.re_filter.match(esp)
                #m.group(0) is the whole [...] term, group(1), the content of the brackets
                cssrule.filter.append(m.group(1).strip())
                    # handle the rest of the string
                esp = esp[len(m.group(0)):]
                    #got element, next possible tokens are: element (nested), or ',.:[' or '::'
                next_possible_token = 1|2|4|8|16|32
                continue

            #bail out here if we did not find a valid element
            raise CSSException("Invalid CSS: Unexpected token %s in rule:\n'%s'" % (esp.strip(),rule.strip()))

        # finally assign all our rules to the CSSRule
        # split rule string at ';'s and create a list
        ruleslist = rules.split(';')
        rule_dict = {}
        # now make a dict out of it and add it to the CSS rule
        for r in ruleslist:
            sep_pos = r.find(':')
            if sep_pos == -1:
                #ignore a rule if it doesn't contain a ':'
                continue
            rule_dict[r[0:sep_pos].strip()] = r[sep_pos + 1:].strip()

        cssrule.rules = rule_dict

        # add the new rule to the correct list of rules
        cssrule.id = len(self.rules[cssrule.ele])
        self.rules[cssrule.ele].append(cssrule)

    def parseCSS_file(self, filepath):
        """parse the CSS file given in the class intialization"""

        with open(filepath, "r") as css_file:
            css = css_file.read()
        #first remove all comments from the CSS
        css = self.remove_comments(css)
        # curpos points to the location in the data that we already have parsed.
        # It gets set to -1 when we reach EOF which is our termination criteria
        curpos = 0
        while curpos != -1:
            # @import rule?
            import_rule = re.match("\s*@import\s+url\(\"?([^\"\)]*)\"?\).*;", css[curpos:])
            if import_rule:
                #allow only simple file names, no spaces surrounding etc.
                import_file = import_rule.groups()[0].strip()
                if not os.path.isfile(import_file):
                    logging.error("Could not import file %s from file %s" % (
                            filepath, import_file))
                self.parseCSS_file(import_file)
                curpos += len(import_rule.group())
                continue
            #parse next rule, assume we are at the beginning of one
            nextpos = css.find('}', curpos)
            if nextpos == -1:
                # if no } found, make sure no nonwhitespace is left
                if re.search('\S', css[curpos:]):
                    raise CSSException("Invalid CSS: Non-whitespace after last '}' (after char %d)" % curpos)
                curpos = -1
            else:
                rule = css[curpos:nextpos + 1]
                self.addCSSrule(rule)

                # set curpos to next location we want to examine
                curpos = nextpos + 1

    def apply_to_ele(self, ele, zoom=None):
        """Applies all stylesheets to the element 'ele'
        :param ele: an ElementTree node containing the osm element
        :param zoom: optional zoom value that acts as style selector. If zoom is `None` 
                     only styles without any selector will be applied.
        :returns: a dict of rules that should be applied to it. 
                  Returns None if no styles can be applied to this element."""
        #determine the numeric value of the element type and immediately return if not node, way, relation.
        try:
            #the 'osm' tag will receive the rules for 'canvas'
            ele_type = ['osm','node','way','relation'].index(ele.tag)
        except ValueError:
            # on other elements, e.g. 'bounds', we simply return None
            return None

        #1) As a special case, look at the layer tag value and add that
        #later to the z-index to cope with bridges and stuff. 2) Check
        #if we have relation[type=multipolygon], if yes, pretend it is a
        #way (set ele_type to way), so the way styles apply to it.
        layer = 0
        for child in ele.findall('tag'):
            key = child.get('k')
            if ele_type == 3 and key == 'type' and \
                    child.get('v') == 'multipolygon':
                ele_type = 2 #pretend it's a way
                # and set :closed attr, so that area rule apply to multipolygons
                # TODO: this should probably be done in the parser already
                tag = ElementTree.SubElement(ele, 'tag')
                tag.set('k',':closed')
            if key == 'layer':
                layer = float(child.get('v', 0))

        # The rules dict that we will return
        appl_styles = {}

        ## We go through all possible style rules in order and try to apply those that match
        for style in self.rules[ele_type]:
            #only examine those with matching element type. Sanity check, should not happen anyway!
            #if style.ele != ele_type:
            #    continue
            #only examine style selector matches zoom
            if not style.test_zoom(zoom):
                continue
            if not style.test_filter(ele):
                continue

            #here we have a style that should be applied to the element
            #update style for the correct subpart
            try:
                appl_styles[style.subpart].update(style.rules)
            except KeyError:
                #create a copy of the origin style and save it in our new style
                appl_styles[style.subpart] = style.rules.copy()

            #as a special case, look at the layer tag value and add
            #that to the z-index to cope with bridges and stuff.
            try:
                appl_styles[style.subpart]["z-index"] = \
                    float(appl_styles[style.subpart]["z-index"]) + layer
            except KeyError:
                appl_styles[style.subpart]["z-index"] = layer 


        #finally take the generic stylesheet and update it with specific subpart ones:
        #XXX THis is a bit magic right now... :-(
        if len(appl_styles)>1 and appl_styles.has_key(None):
            base_style = appl_styles[None]
            del(appl_styles[None])
            for subpart, style in appl_styles.items():
                appl_styles[subpart] = base_style.copy()
                appl_styles[subpart].update(style)

        return appl_styles
