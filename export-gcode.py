#!/usr/bin/env python
# coding=utf-8
#
# Copyright (c) 2020 - Early Ehlinger, thenewentity.com
#
"""
Export cnc gcode (.gcode)
"""

# import cubicsuperpath
import inkex
import json
import math
import os
import re
import GcodeExporter
import GcodeStyle
from inkex import bezier, Group, CubicSuperPath, ShapeElement, ColorIdError, ColorError, transforms, elements, Style
from inkex import command # deprecated. Danger!
from synfig_prepare import InkscapeActionGroup

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


def segmentLength(p0, p1, stream = None):
    a = p1[0] - p0[0]
    b = p1[1] - p0[1]
    asq = a * a
    bsq = b * b
    result = math.sqrt(asq + bsq)
    if stream:
        stream.comment(f'segmentLength: p0:{p0} p1:{p1} a:{a} b:{b} asq:{asq} bsq:{bsq} result:{result}')
    return result

assert 10 == segmentLength((0,0), (10,0))
assert 10 == segmentLength((10,0), (0,0))
assert 10 == segmentLength((0,0), (0,10))
assert 10 == segmentLength((0,10), (0,0))
assert 5 == segmentLength((0,0), (3,4))
assert 5 == segmentLength((0,0), (4,3))
assert 5 == segmentLength((3,4), (0,0))
assert 5 == segmentLength((4,3), (0,0))

class Bounds:
    def __init__(self, x0 = None, y0 = None, x1 = None, y1 = None):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def __str__(self):
        return f"{self.__dict__}"

    def update(self, point):
        if self.x0 == None or self.x0 > point[0]:
            self.x0 = point[0]
        if self.x1 == None or self.x1 < point[0]:
            self.x1 = point[0]
        if self.y0 == None or self.y0 > point[1]:
            self.y0 = point[1]
        if self.y1 == None or self.y1 < point[1]:
            self.y1 = point[1]

class Polyline:
    def __init__(self, points = None, closed = False):
        self.points = points or list()
        self.closed = closed

    def __str__(self):
        return f"{self.__dict__}"

    def getLength(self):
        if len(self.points):
            result = 0
            p0 = self.points[0]
            for p1 in self.points[1:]:
                result = result + segmentLength(p0,p1)
                p0 = p1
            return result
        else:
            return 0

    def getBounds(self, result = Bounds()):
        for point in self.points:
            result.update(point)
        return result

class Zones:
    def __init__(self, polylines = None):
        self.polylines = polylines or list()

    def __str__(self):
        return "{'polylines':[" + ",".join([f"{p}" for p in self.polylines]) + "]}"

    def getLength(self):
        return sum([polyline.getLength() for polyline in self.polylines])

    def getBounds(self):
        result = Bounds()
        for polyline in self.polylines:
            polyline.getBounds(result)
        return result

def getDescription(element):
    for child in element.iterchildren():
        if type(child).__name__ == 'Desc':
            return child.text
    return ''

def getTagName(element):
    return os.path.basename(element.xml_path)

def typeName(element):
    try:
        return type(element).__name__
    except Error:
        return '<unrecognized>'

def exportIgnore(stream, gcodeStyle, element, *args, **kwargs):
    stream.comment(f'ignoring entry of unrecognized type: {typeName(element)}');
    pass


def gcodeSafeHeight(stream, gcodeStyle):
    stream.code(code='G00', Z=gcodeStyle.safeHeight, F=gcodeStyle.rapidz, comment='raise cutter to safe height')

#def gcodeRapid(stream, comment, X = None, Y = None, Z = None, F = None ):
#    stream.code(code='G00', X=X, Y=Y, Z=Z, F=F, comment=comment)

def gcodeLinear(stream, comment, X = None, Y = None, Z = None, F = None ):
    stream.code(code='G01', X=X, Y=Y, Z=Z, F=F, comment=comment)

def cspToZones(stream, path, gcodeStyle, transform):
    zones = Zones()
    stream.comment(f'cspToZones...')
    polyline = None
    for command in path:
        letter = command.letter
        stream.comment(f'svg path command:"{command}"')
        if letter == 'M':
            polyline = Polyline()
            zones.polylines.append(polyline)
            p0 = transform.apply_to_point((command.args[0], command.args[1]))
            polyline.points.append(p0)
            pInitial = p0
        if letter == 'C':
            args = command.args
            p1 = transform.apply_to_point((args[0], args[1]))
            p2 = transform.apply_to_point((args[2], args[3]))
            p3 = transform.apply_to_point((args[4], args[5]))
            t = 0
            while t < 1.0:
                bez = [p0,p1,p2,p3]
                pt = bezier.bezierpointatt(bez, t)
                polyline.points.append(pt)
                t += gcodeStyle.curveIncrement
            polyline.points.append(p3)
            polyline.closed = False
            p0 = p3
        if letter == 'L':
            p0 = transform.apply_to_point((command.args[0], command.args[1]))
            polyline.points.append(p0)
            polyline.closed = False
        if letter == 'Z':
            polyline.points.append(pInitial)
            polyline.closed = True
    stream.comment(f'...cspToZones: {zones}')
    return zones

def hasTabs(gcodeStyle):
    return gcodeStyle.tabHeight and gcodeStyle.tabWidth and gcodeStyle.tabStartInterval

def cutPolylineAtDepth(stream, polyline, gcodeStyle, startDepth, finalDepth, needSafeHeight):
    if not len(polyline.points):
        return
    totalL = polyline.getLength()
    depthRange = finalDepth - startDepth

    p0 = polyline.points[0]
    l = 0
    d = startDepth

    tabStart = totalL + 1
    tabEnd = totalL + 1
    tabDepth = gcodeStyle.tabDepth
    inTab = False
    useTabs = hasTabs(gcodeStyle)
    if useTabs:
        tabStart = gcodeStyle.tabStartInterval
        tabEnd = tabStart + gcodeStyle.tabWidth

    stream.comment(f'cutting polyline ramp: {startDepth} -> {finalDepth} needSafeHeight:{needSafeHeight}')
    if needSafeHeight:
        gcodeSafeHeight(stream, gcodeStyle)
    stream.rapid(comment='rapid to start of polyline', X=p0[0], Y=p0[1], F=gcodeStyle.rapidxy)
    stream.linear(comment='plunge to start depth', Z=d, F = gcodeStyle.feedz)

    for p1 in polyline.points[1:]:
        segmentL = segmentLength(p0,p1)
        startL = l
        endL = l + segmentL
        lFraction = endL / totalL
        d = startDepth + lFraction * depthRange # interpolate depth at p1

        while not inTab and (tabStart < startL):
            tabStart += gcodeStyle.tabStartInterval
            tabEnd = tabStart + gcodeStyle.tabWidth

        finishedSegment = False
        while not finishedSegment:
            if not inTab:
                if endL < tabStart or d > -tabDepth:
                    # either segment ends before tab, or whole segment is above tab
                    # NOTE: this presumes we only ramp *down*.
                    stream.linear(comment=f'lFraction:{lFraction} d:{d} tabDepth:{-tabDepth}', X=p1[0], Y=p1[1], Z=d, F=gcodeStyle.feedxy)
                    l = startL
                    finishedSegment = True
                else: # tab starts in this line segment
                    tabStartLFraction = tabStart / totalL
                    tabStartRampDepth = startDepth + tabStartLFraction * depthRange
                    tabSegmentFraction = (tabStart - startL) / (endL - startL)

                    # figure out x,y of tab start
                    tabStartPoint = (p0[0] + tabSegmentFraction*(p1[0]-p0[0]),
                                     p0[1] + tabSegmentFraction*(p1[1]-p0[1]))
                    stream.linear(comment=f'ramp to tab start', X=tabStartPoint[0], Y=tabStartPoint[1],
                                Z=tabStartRampDepth, F=gcodeStyle.feedxy)
                    stream.linear(comment=f'lift to tab depth', Z=-tabDepth, F=gcodeStyle.rapidz)
                    inTab = True

            if inTab:
                if tabEnd < endL:
                    tabStopLFraction = tabEnd / totalL
                    tabStopRampDepth = startDepth + tabStartLFraction * depthRange
                    tabSegmentFraction = (tabEnd - startL) / (endL - startL)

                    tabEndPoint = (p0[0] + tabSegmentFraction*(p1[0]-p0[0]),
                                   p0[1] + tabSegmentFraction*(p1[1]-p0[1]))

                    stream.linear(comment=f'skim tab top tabStop:{tabStopLFraction}', X=tabEndPoint[0],Y=tabEndPoint[1], F=gcodeStyle.feedxy)
                    stream.linear(comment=f'plunge to post-tab ramp top', Z=tabStopRampDepth, F=gcodeStyle.feedz)
                    tabStart = tabStart + gcodeStyle.tabStartInterval
                    tabEnd = tabStart + gcodeStyle.tabWidth
                    inTab = False
                else:
                    stream.linear(comment=f'skim tab top endL:{endL} tabEnd:{tabEnd}', X=p1[0],Y=p1[1], F=gcodeStyle.feedxy)
                    finishedSegment = True
            l = endL
        p0 = p1
    stream.comment(f'polyline.closed: {polyline.closed}')
    return not polyline.closed

def contour(stream, gcodeStyle, zones, transform):
    for polyline in zones.polylines:
        stream.comment(f"polyline: {polyline.__dict__}")
        needSafeHeight = True
        depth = gcodeStyle.startDepth
        while depth < gcodeStyle.depth:
            nextDepth = min(depth + gcodeStyle.depthIncrement, gcodeStyle.depth)
            needSafeHeight = cutPolylineAtDepth(stream, polyline, gcodeStyle,
                                                -depth, -nextDepth, needSafeHeight) and needSafeHeight
            depth = nextDepth
        cutPolylineAtDepth(stream, polyline, gcodeStyle, -depth, -depth, needSafeHeight)

def float_range(start, stop, step, includeStop = False):
    if start < stop:
        while start < stop:
            yield float(start)
            start += step
    else:
        while start > stop:
            yield float(start)
            start += step
    if includeStop:
        yield stop

def pocket(stream, gcodeStyle, zones, transform):
    if not gcodeStyle.depth:
        stream.comment("Depth is 0. Skipping path")
        return
    bounds = zones.getBounds()
    stream.comment(f"bounds: {bounds}")
    for depth in float_range(-gcodeStyle.startDepth, -gcodeStyle.depth, -gcodeStyle.depthIncrement, True):
        stream.comment(f"depth:{depth}")
        streamScan = stream.indent()
        for y in float_range(bounds.y0 + gcodeStyle.toolDiameter / 2.0, bounds.y1 - gcodeStyle.toolDiameter / 2.0, gcodeStyle.toolStepOver):
            streamScan.comment(f"y:{y}")
            streamSegments = streamScan.indent()
            intersections = []
            for polyline in zones.polylines:
                if not polyline.closed:
                    continue
                p0n = polyline.points[0]
                streamSegments.comment(f"polyline:{polyline}")
                for p1 in polyline.points[1:]:
                    p0 = p0n
                    p0n = p1
                    x0, y0 = p0[0], p0[1]
                    x1, y1 = p1[0], p1[1]
                    if (y1 > y0):
                        if (y < y0) or (y>y1):
                            continue
                        pass
                    else:
                        if (y < y1) or (y>y0):
                            continue
                        pass
                    # https://en.wikipedia.org/wiki/Linear_interpolation
                    # (y-y0)/(x-x0) = (y1-y0)/(x1-x0)
                    # solving for x...
                    # (x-x0)/(y-y0) = (x1-x0)/(y1-y0)
                    # (x-x0) = (y-y0)(x1-x0)/(y1-y0)
                    if y1 == y0:
                        #intersections.append(x0)
                        #intersections.append(x1)
                        continue
                    x = (y-y0)*(x1-x0)/(y1-y0) + x0
                    intersections.append(x)
                    streamSegments.comment(f"p0:{p0} p1:{p1} x:{x} intersections:{intersections}")
            # at this point, intersections contains an unsorted list of x coordinates. If we sort them and alternate up/down, we should
            # get the pattern we want.
            up = True
            for x in sorted(intersections):
                if up:
                    gcodeSafeHeight(streamSegments, gcodeStyle)
                    streamSegments.rapid(comment='rapid to start of polyline', X=x, Y=y, F=gcodeStyle.rapidxy)
                    up = False
                else:
                    streamSegments.linear('plunge', Z=depth,F=gcodeStyle.feedz)
                    streamSegments.linear('scan', X=x,Y=y,F=gcodeStyle.feedxy)
                    gcodeSafeHeight(streamSegments, gcodeStyle)
                    up = True
            
            

def exportPath(stream, element, transform):
    gcodeStyle = GcodeStyle.getElementGcodeStyle(stream, element)
    stream.comment(f'type:"{type(element).__name__}" id:"{element.get_id()}"')
    stream.comment(f'composed_transform:"{element.composed_transform()}"')
    stream.comment(f'transform:"{transform}"')
    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.comment(f'effectiveTransform:"{effectiveTransform}"')

    if not gcodeStyle.depth:
        stream.comment("Depth is 0. Skipping path")
        return

    path = element.path
    stream.comment(f"path:{path}")
    stream.comment(f"gcodeStyle:{gcodeStyle.__dict__}")
    csp = CubicSuperPath(path).to_path()
    stream.comment(f"csp:{csp}")
    zones = cspToZones(stream, csp, gcodeStyle, transform)

    
    if gcodeStyle.fillMode == 'hatch':
        pocket(stream.indent(), gcodeStyle, zones, effectiveTransform)
    contour(stream.indent(), gcodeStyle, zones, effectiveTransform)

def exportLayer(stream, element, transform):
    gcodeStyle = GcodeStyle.getElementGcodeStyle(stream, element)
    for child in reversed(list(element.iterchildren())):
        visitElement(stream.indent(), child, transform)
    gcodeSafeHeight(stream, gcodeStyle)

elementExportFunctions = {
    'Layer': exportLayer,
    'Group': exportLayer,
    'Circle': exportPath,
    'Ellipse': exportPath,
    'PathElement': exportPath,
    'Rectangle': exportPath,
}

def getElementNamespace(elem):
    return elem.nsmap.get(elem.prefix, None)

def getElementFullTagname(elem):
    return (getElementNamespace(elem), elem.TAG)

def visitElement(stream, elem, transform):
    stream.comment(f'{getElementNamespace(elem)}:{elem.TAG} => {type(elem).__name__} {elem.get_id()} {elem.label}')
    # stream.indent().comment(f'dir: {elem.__dir__()}')
    fn = elementExportFunctions.get(type(elem).__name__, exportIgnore)
    fn(stream.indent(), elem, transform)

class ExportCncGcode(inkex.OutputExtension):
    """Export all shapes with <gcode:settings> tags as gcode"""
    #select_all = (ShapeElement,)

    def setupMachine(self, stream):
        stream.code(code='G17', comment='XY plane')
        stream.code(code='G21', comment='mm mode')
        stream.code(code='G40', comment='compensation off')
        stream.code(code='G90', comment='absolute distance mode')

    def save(self, rawStream):
        name = self.svg.name.replace('.svg', '')
        root = GcodeExporter.GcodeExporter(rawStream, self.document, 0)
        root.comment('Inkscape => GCode Save')
        stream = root.indent()
        stream.comment(f'Name: {name}')
        stream.comment(f'self: {self.__dir__()}')

        bbox = self.svg.get_page_bbox()
        gcodeTransform = (transforms.Transform(f'translate({bbox.left}, {bbox.bottom})')
                          .__mul__(transforms.Transform('scale(1,-1)')))

        stream.comment('Setting up Machine')
        self.setupMachine(stream.indent())

        stream.comment('Traversing SVG document tree')
        for elem in self.svg.iterchildren():
            visitElement(stream.indent(), elem, gcodeTransform)

        stream.code(code='M02', comment='end of program')

if __name__ == '__main__':
    ExportCncGcode().run()
