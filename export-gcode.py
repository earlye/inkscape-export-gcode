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
from inkex import bezier, Group, CubicSuperPath, ShapeElement, ColorIdError, ColorError, transforms, elements, Style
from inkex import command # deprecated. Danger!
from synfig_prepare import InkscapeActionGroup

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

def wrapComment(comment, prefix = None):
    return f'{xstr(prefix)}({comment})' if comment else ''

def xstr(s):
    if s is None:
        return ''
    return str(s)

class GcodeExporter:
    def __init__(self, stream, document, depth):
        self.stream = stream
        self.depth = depth
        self.document = document

    def write(self, code):
        self.stream.write((' ' * self.depth + code).encode('utf-8'))

    def code(self, code=None, comment = None, **kwargs):
        self.write(f'{xstr(code)}{gcodeCoordinates(**kwargs)}{wrapComment(comment," ")}\n')

    def comment(self, comment):
        self.write(wrapComment(comment) + '\n')

    def indent(self):
        return GcodeExporter(self.stream, self.document, self.depth + 2)

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

class Polyline:
    def __init__(self, points = None, closed = False):
        self.points = points or list()
        self.closed = closed

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

class Zones:
    def __init__(self, polylines = None):
        self.polylines = polylines or list()

    def getLength(self):
        return sum([polyline.getLength() for polyline in self.polylines])

def getDescription(element):
    for child in element.iterchildren():
        if type(child).__name__ == 'Desc':
            return child.text
    return ''

def eval(expression, default):
    try:
        return float(expression)
    except Exception:
        return default

def mmFromInch(value):
    return value * 25.4

def isNumber(value):
    return isinstance(value, (int, float, complex)) and not isinstance(value, bool)

distanceRegex = re.compile('(([0-9]*(\.[0-9]*))(/([0-9]*(\.[0-9]*)))?)(px|in|mm|cm|Q|pc|pt)?')
unitFactors = { 'in': 25.4, 'px': 25.4 / 96.0, 'cm': 1.0/100.0, 'mm': 1.0, 'Q': 40.0/100.0, 'pc': 25.4/6.0, 'pt': 25.4/72.0 }
def distance(stream, value, defaultValue = None):
    if isNumber(value):
        return value
    if value is None:
        return defaultValue
    match = distanceRegex.match(value)
    if match is None:
        return defaultValue

    # stream.comment(f"distance: {value} {defaultValue} 0:{match.group(0)} 1:{match.group(1)} 2:{match.group(2)} 3:{match.group(3)} 4:{match.group(4)} 5:{match.group(5)} 6:{match.group(6)} 7:{match.group(7)}")
    numerator = float(match.group(2))
    denominator = match.group(5)
    if denominator is None:
        denominator = 1.0
    else:
        denominator = float(denominator)
    unit = match.group(7) or 'mm'
    unitFactor = unitFactors.get(unit, 'mm')

    unitValue = numerator / denominator
    scaledValue = unitValue * unitFactor
    stream.comment(f"distance: {value} {unitValue}{unit} {scaledValue}mm")
    return scaledValue

class GcodeStyle:
    def __init__(self, stream, style):
        self.depth = distance(stream, style.get("x-gcode-depth", None), 0)
        self.depthIncrement = distance(stream, style.get("x-gcode-depth-increment", None), mmFromInch(0.1))
        if self.depthIncrement < 0:
            self.depthIncrement = 0.1
        if self.depthIncrement > self.depth:
            self.depthIncrement = self.depth

        self.tool = style.get("x-gcode-tool", 'default')
        self.toolDiameter = distance(stream, style.get(f"x-gcode-tool-{self.tool}-diameter", mmFromInch(0.25)))
        self.toolStepOver = distance(stream, style.get(f"x-gcode-tool-{self.tool}-stepover", self.toolDiameter * 0.8 ))
        self.stepOver = distance(stream, style.get("x-gcode-stepover", self.toolStepOver))

        # Todo: switch from curveIncrement to maxCurveSegmentLength
        self.curveIncrement = distance(stream, style.get("x-gcode-curve-increment", None), 0.1)
        if self.curveIncrement < 0 or self.curveIncrement > 1:
            self.curveIncrement = 0.1
        self.edgeMode = style.get("x-gcode-edge-mode", 'center')
        self.fillMode = style.get("x-gcode-fill-mode", '')

        self.feedxy = distance(stream, style.get("x-gcode-feed-xy", None), mmFromInch(25))
        self.feedz = distance(stream, style.get("x-gcode-feed-z", None), mmFromInch(10))

        self.rapidxy = distance(stream, style.get("x-gcode-rapid-xy", None), mmFromInch(60))
        self.rapidz = distance(stream, style.get("x-gcode-rapid-z", None), mmFromInch(60))
        self.supportsCubicSpline = False
        self.safeHeight = mmFromInch(0.25)

def getGcodeStyle(stream, style):
    stream.comment(f'SvgStyle: {style}')
    result = GcodeStyle(stream, style)
    stream.comment(f'GcodeStyle: {json.dumps(result.__dict__)}')
    return result

def getElementGcodeStyle(stream, element):
    return getGcodeStyle(stream, element.composed_style())

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

def gcodeCoordinate(c,v):
    if v != None:
        return f' {c}{v:.5f}'
    return ''

def gcodeCoordinates(**kwargs):
    coord = gcodeCoordinate
    result = ''
    for key in kwargs:
        result = result + coord(key,kwargs[key])
    return result

def gcodeRapid(stream, comment, X = None, Y = None, Z = None, F = None ):
    stream.code(code='G00', X=X, Y=Y, Z=Z, F=F, comment=comment)

def gcodeLinear(stream, comment, X = None, Y = None, Z = None, F = None ):
    stream.code(code='G01', X=X, Y=Y, Z=Z, F=F, comment=comment)

def cspToZones(stream, path, gcodeStyle, transform):
    zones = Zones()
    stream.comment(f'cspToZones: len(zones.polylines):{len(zones.polylines)}')
    polyline = None
    for command in path:
        letter = command.letter
        stream.comment(f'svg path command:"{command}" len(zones.polylines):{len(zones.polylines)}')
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
    return zones

def cutPolylineAtDepth(stream, polyline, gcodeStyle, startDepth, finalDepth, needSafeHeight):
    if not len(polyline.points):
        return
    l = 0
    totalL = polyline.getLength()
    depthRange = finalDepth - startDepth
    d = startDepth

    p0 = polyline.points[0]
    stream.comment(f'cutting polyline ramp: {startDepth} -> {finalDepth}')
    if needSafeHeight:
        gcodeSafeHeight(stream, gcodeStyle)
    gcodeRapid(stream, 'rapid to start of curve', X=p0[0], Y=p0[1], F=gcodeStyle.rapidxy)
    gcodeLinear(stream, 'plunge to start depth', Z=d, F = gcodeStyle.feedz)
    for p1 in polyline.points[1:]:
        segmentL = segmentLength(p0,p1)
        l = l + segmentL
        lFraction = l / totalL
        d = startDepth + lFraction * depthRange # interpolate depth at p1
        gcodeLinear(stream, f'lFraction:{lFraction}', X=p1[0], Y=p1[1], Z=d, F=gcodeStyle.feedxy)
        p0 = p1
    return not polyline.closed

def cutPathAtDepth(stream, path, gcodeStyle, transform, startDepth, finalDepth, needSafeHeight):
    p0 = None
    pInitial = None
    stream.comment(f'carving path from startDepth:{startDepth} to finalDepth:{finalDepth}')
    stream = stream.indent()

    zones = cspToZones(stream, path, gcodeStyle, transform)

    needSafeHeight = True
    for polyline in zones.polylines:
        needSafeHeight = needSafeHeight and cutPolylineAtDepth(stream, polyline, gcodeStyle, startDepth, finalDepth, needSafeHeight)
    return needSafeHeight

def deadCode():
    for command in path:
        letter = command.letter
        stream.comment(f'svg path command:"{command}"')
        if letter == 'M':
            p0 = transform.apply_to_point((command.args[0], command.args[1]))
            pInitial = p0
            if needSafeHeight:
                gcodeSafeHeight(stream, gcodeStyle)
            gcodeRapid(stream, 'rapid to start of curve', X=p0[0], Y=p0[1], F=60)
            gcodeLinear(stream, 'plunge to start depth', Z=startDepth, F=gcodeStyle.feedz)
            needSafeHeight = True
        if letter == 'C':
            args = command.args
            p1 = transform.apply_to_point((args[0], args[1]))
            p2 = transform.apply_to_point((args[2], args[3]))
            p3 = transform.apply_to_point((args[4], args[5]))
            t = 0
            while t < 1.0:
                bez = [p0,p1,p2,p3]
                pt = bezier.bezierpointatt(bez, t)
                gcodeLinear(stream.indent(), comment=f'interpolated cubic spline at t:{t}', X=pt[0], Y=pt[1], F=gcodeStyle.feedxy)
                t += gcodeStyle.curveIncrement
            gcodeLinear(stream, comment=f'interpolated cubic spline at final t:1.0', X=p3[0], Y=p3[1], F=gcodeStyle.feedxy)
            p0 = p3
            needSafeHeight = True
        if letter == 'L':
            p0 = transform.apply_to_point((command.args[0], command.args[1]))
            gcodeLinear(stream, f'line', X=p0[0], Y=p0[1], F=gcodeStyle.feedxy)
            needSafeHeight = True
        if letter == 'Z':
            p0 = pInitial
            gcodeLinear(stream, f'zone close', X=p0[0], Y=p0[1], F=gcodeStyle.feedxy)
            needSafeHeight = False
    return needSafeHeight

def gcodePath(stream, gcodeStyle, path, transform):
    stream.comment(f'path commands:')
    stream.comment(f'path:{path}')

    if not gcodeStyle.depth:
        stream.comment("Depth is 0. Skipping path")
        return

    csp = CubicSuperPath(path).to_path()
    stream.comment(f'cubicsuperpath parsed:{csp} type:{type(csp).__name__}')

    startOffset = 0
    finalOffset = 0
    offsetStep = 0
    # change the offsets for inside vs outside vs center
    if 'inside' == gcodeStyle.edgeMode:
        startOffset = gcodeStyle.toolDiameter * -0.5
        finalOffset = gcodeStyle.toolDiameter * -0.5
    elif 'outside' == gcodeStyle.edgeMode:
        startOffset = gcodeStyle.toolDiameter * 0.5
        finalOffset = gcodeStyle.toolDiameter * 0.5

    if 'spiral' == gcodeStyle.fillMode:
        offsetStep = -gcodeStyle.toolStepOver
        finalOffset = float('-inf')

    stream.comment(f'shape offset range: [{startOffset}, {finalOffset}, {offsetStep}]')

    depth = 0
    needSafeHeight = True
    while depth < gcodeStyle.depth:
        nextDepth = depth + gcodeStyle.depthIncrement
        if nextDepth > gcodeStyle.depth:
            nextDepth = gcodeStyle.depth
        needSafeHeight = cutPathAtDepth(stream.indent(), csp, gcodeStyle, transform, -depth, -nextDepth, needSafeHeight )
        depth = nextDepth
    cutPathAtDepth(stream.indent(), csp, gcodeStyle, transform, -gcodeStyle.depth, -gcodeStyle.depth, needSafeHeight)

def exportEllipse(stream, element, transform):
    gcodeStyle = getElementGcodeStyle(stream, element)

    stream.comment(f'type:"Ellipse" id:"{element.get_id()}" radius:"{element.radius}" center:"{element.center}"')
    stream.comment(f'composed_transform:"{element.composed_transform()}"')
    stream.comment(f'transform:"{transform}"')
    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.comment(f'effectiveTransform:"{effectiveTransform}"')
    gcodePath(stream.indent(), gcodeStyle, element.path, effectiveTransform)

def exportPath(stream, element, transform):
    gcodeStyle = getElementGcodeStyle(stream, element)

    stream.comment(f'type:"{type(element).__name__}" id:"{element.get_id()}"')
    stream.comment(f'composed_transform:"{element.composed_transform()}"')
    stream.comment(f'transform:"{transform}"')
    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.comment(f'effectiveTransform:"{effectiveTransform}"')
    gcodePath(stream.indent(), gcodeStyle, element.path, effectiveTransform)

def exportTextElement(stream, element, transform):
    gcodeStyle = getElementGcodeStyle(stream, element)

    stream.comment(f'type:"{type(element).__name__}" id:"{element.get_id()}"')
    stream.comment(f'dir:"{element.__dir__()}"')
    stream.comment(f'elements._selected.__dir__():"{elements._selected.__dir__()}"')
    stream.comment(f'path: {element.get_path()}') # path is empty. :WTF:
    # stream.comment(f'makeelement: {element.makeelement()}') apparently from lxml, requires one param, probably not how to get a path

    for child in element.tspans():
        visitElement(stream.indent(), child, transform)

def exportTspan(stream, element, transform):
    gcodeStyle = getElementGcodeStyle(stream, element)

    stream.comment(f'type:"{type(element).__name__}" id:"{element.get_id()}"')
    stream.comment(f'dir:"{element.__dir__()}"')
    stream.comment(f'path: {element.get_path()}')
    for child in element.iterchildren():
        visitElement(stream.indent(), child, transform)

def exportLayer(stream, element, transform):
    gcodeStyle = getElementGcodeStyle(stream, element)
    for child in reversed(list(element.iterchildren())):
        visitElement(stream.indent(), child, transform)
    gcodeSafeHeight(stream, gcodeStyle)

elementExportFunctions = {
    'Layer': exportLayer,
    'Group': exportLayer,
    'Ellipse': exportEllipse ,
    'PathElement': exportPath,
    'Rectangle': exportPath,
    'TextElement': exportTextElement,
    'Tspan': exportTspan
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
        root = GcodeExporter(rawStream, self.document, 0)
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
