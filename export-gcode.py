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
import os
from inkex import bezier, CubicSuperPath, ShapeElement, ColorIdError, ColorError, transforms, elements, styles

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class GcodeWriter:
    def __init__(self, stream, depth):
        self.stream = stream
        self.depth = depth

    def write(self, code):
        self.stream.write((' ' * self.depth + code).encode('utf-8'))

    def indent(self):
        return GcodeWriter(self.stream, self.depth + 2)

def getDescription(element):
    for child in element.iterchildren():
        if type(child).__name__ == 'Desc':
            return child.text
    return ''

class GcodeGlobals:
    def __init__(self, fulldepth, scaleX = 1.0, scaleY = -1.0, translateX = 0, translateY = 7):
        self.fulldepth = fulldepth
        self.safeHeight = 0.25
        self.scaleX = scaleX
        self.scaleY = scaleY
        self.translateX = translateX
        self.translateY = translateY
        self.xyfeed = 25.400
        self.supportsCubicSpline = False

    def echo(self, stream):
        stream.write( '(Globals:)\n')
        s2 = stream.indent()
        s2.write(f'(.fulldepth: {self.fulldepth})\n')
        s2.write(f'(.safeHeight: {self.safeHeight})\n')
        s2.write(f'(.scaleX: {self.scaleX})\n')
        s2.write(f'(.scaleY: {self.scaleY})\n')
        s2.write(f'(.translateX: {self.translateX})\n')
        s2.write(f'(.translateY: {self.translateY})\n')

    pass

def eval(expression, default):
    try:
        return float(expression)
    except Exception:
        return default

class GcodeStyle:
    def __init__(self, depth, tool, increment, mode):
        self.depth = depth
        self.tool = tool
        self.increment = increment
        self.mode = mode

def getGcodeStyle(stream, element):
    style = element.composed_style()
    depth = eval(style.get("x-gcode-depth", None), -0.25)
    tool = style.get("x-gcode-tool", '')
    increment = eval(style.get("x-gcode-curve-increment", None), 0.1)
    if increment < 0 or increment > 1:
        increment = 0.1

    mode = style.get("x-gcode-mode", 'center')

    stream.write(f'(GcodeStyle depth:{depth} tool:{tool} increment:{increment} mode:{mode})\n')

    return GcodeStyle(depth, tool, increment, mode)

def getTagName(element):
    return os.path.basename(element.xml_path)

def typeName(element):
    try:
        return type(element).__name__
    except Error:
        return '<unrecognized>'

def exportIgnore(stream, gcodeGlobals, element, *args, **kwargs):
    stream.write( f'(ignoring entry of unrecognized type: {typeName(element)})\n');
    pass


def gcodeSafeHeight(stream, gcodeGlobals):
    stream.write( f'G00 Z{gcodeGlobals.safeHeight} (raise cutter to safe height)\n')

def gcodeCoordinates(X = None, Y = None, Z = None, F = None):
    result = ''
    if X != None:
        result += f' X{X:.5f}'
    if Y != None:
        result += f' Y{Y:.5f}'
    if Z != None:
        result += f' Z{Z:.5f}'
    if F != None:
        result += f' F{F:.5f}'
    return result.strip()

def gcodeRapid(stream, comment, X = None, Y = None, Z = None, F = None ):
    stream.write( f'G00 {gcodeCoordinates(X=X,Y=Y,Z=Z,F=F)} ({comment})\n')

def gcodeLinear(stream, comment, X = None, Y = None, Z = None, F = None ):
    stream.write( f'G01 {gcodeCoordinates(X=X,Y=Y,Z=Z,F=F)} ({comment})\n')


def cutPathAtDepth(stream, gcodeGlobals, transform, depth, needSafeHeight, path):
    p0 = None
    pInitial = None
    stream.write( f'(carving path at depth:{depth})\n')
    for command in path:
        letter = command.letter
        stream.write( f'(svg path command:"{command}")\n')
        if letter == 'M':
            p0 = transform.apply_to_point((command.args[0], command.args[1]))
            pInitial = p0
            if needSafeHeight:
                gcodeSafeHeight(stream.indent(), gcodeGlobals)
            gcodeRapid(stream.indent(), 'rapid to start of curve', X=p0[0], Y=p0[1], F=60)
            gcodeLinear(stream.indent(), 'plunge to depth', Z=depth, F=gcodeGlobals.xyfeed)
            needSafeHeight = True
        if letter == 'C':
            args = command.args
            # stream.write( f'  (args: {args})\n')
            p1 = transform.apply_to_point((args[0], args[1]))
            p2 = transform.apply_to_point((args[2], args[3]))
            p3 = transform.apply_to_point((args[4], args[5]))
            if gcodeGlobals.supportsCubicSpline:
                p1i = (p1[0] - p0[0], p1[1] - p0[0])
                p2i = (p2[0] - p1[0], p2[1] - p1[1])
                stream.write( f'G5 I{p1i[0]} J{p1i[1]} P{p2i[0]} Q{p2i[1]} X{p3[0]} Y{p3[1]} (cubic spline)\n')
            else:
                # stream.write( f'  (p0: {p0} p1:{p1} p2:{p2} p3:{p3})\n')
                for largeT in range(0,100,10):
                    t = largeT / 100.0
                    bez = [p0,p1,p2,p3]
                    pt = bezier.bezierpointatt(bez, t)
                    gcodeLinear(stream.indent(), f't:{t}', X=pt[0], Y=pt[1], F=gcodeGlobals.xyfeed)
                gcodeLinear(stream.indent(), f't:1.0', X=p3[0], Y=p3[1], F=gcodeGlobals.xyfeed)
            p0 = p3
            needSafeHeight = True
        if letter == 'L':
            p0 = transform.apply_to_point((command.args[0], command.args[1]))
            gcodeLinear(stream.indent(), f'line', X=p0[0], Y=p0[1], F=gcodeGlobals.xyfeed)
            needSafeHeight = True
        if letter == 'Z':
            p0 = pInitial
            gcodeLinear(stream.indent(), f'zone close', X=p0[0], Y=p0[1], F=gcodeGlobals.xyfeed)
            needSafeHeight = False
    return needSafeHeight

def gcodePath(stream, gcodeGlobals, GcodeStyle, path, transform):
    stream.write(f'(path commands:)\n')
    stream.write(f'(path:{path})\n')
    csp = CubicSuperPath(path).to_path()
    stream.write(f'(cubicsuperpath parsed:{csp} type:{type(csp).__name__})\n')

    depth = 0
    needSafeHeight = True
    while depth < GcodeStyle.depth:
        needSafeHeight = cutPathAtDepth(stream.indent(), gcodeGlobals, transform, -depth, needSafeHeight, csp)
        depth += GcodeStyle.increment
    if depth != GcodeStyle.increment:
        cutPathAtDepth(stream.indent(), gcodeGlobals, transform, -GcodeStyle.depth, needSafeHeight, csp)

def exportEllipse(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.write(f'(type:"Ellipse" id:"{element.get_id()}" radius:"{element.radius}" center:"{element.center}")\n')
    stream.write(f'(composed_transform:"{element.composed_transform()}")\n')
    stream.write(f'(transform:"{transform}")\n')
    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.write(f'(effectiveTransform:"{effectiveTransform}")\n')
    gcodePath(stream.indent(), gcodeGlobals, GcodeStyle, element.path, effectiveTransform)

def exportPath(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.write(f'(type:"{type(element).__name__}" id:"{element.get_id()}")\n')
    stream.write(f'(composed_transform:"{element.composed_transform()}")\n')
    stream.write(f'(transform:"{transform}")\n')
    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.write(f'(effectiveTransform:"{effectiveTransform}")\n')
    gcodePath(stream.indent(), gcodeGlobals, GcodeStyle, element.path, effectiveTransform)

def exportTextElement(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.write(f'\n\n')
    stream.write(f'(type:"{type(element).__name__}" id:"{element.get_id()}")\n')
    stream.write(f'(dir:"{element.__dir__()}")\n')
    stream.write(f'(elements._selected.__dir__():"{elements._selected.__dir__()}")\n')
    stream.write(f'(path: {element.get_path()})\n') # path is empty. :WTF:
    # stream.write(f'(makeelement: {element.makeelement()})\n') apparently from lxml, requires one param, probably not how to get a path

    for child in element.tspans():
        stream.write( f'({getElementNamespace(child)}:{child.TAG} => {type(child).__name__})\n')
        fn = elementExportFunctions.get(type(child).__name__, exportIgnore)
        fn(stream.indent(), gcodeGlobals, child, transform)

def exportTspan(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.write(f'\n\n')
    stream.write(f'(type:"{type(element).__name__}" id:"{element.get_id()}")\n')
    stream.write(f'(dir:"{element.__dir__()}")\n')
    stream.write(f'(path: {element.get_path()})\n')
    for child in element.iterchildren():
        stream.write( f'({getElementNamespace(child)}:{child.TAG} => {type(child).__name__})\n')
        fn = elementExportFunctions.get(type(child).__name__, exportIgnore)
        fn(stream.indent(), gcodeGlobals, child, transform)

def exportLayer(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)
    for child in element.iterchildren():
        stream.write( f'({getElementNamespace(child)}:{child.TAG} => {type(child).__name__})\n')
        fn = elementExportFunctions.get(type(child).__name__, exportIgnore)
        fn(stream.indent(), gcodeGlobals, child, transform)

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
    return elem.nsmap[elem.prefix]

def getElementFullTagname(elem):
    return (getElementNamespace(elem), elem.TAG)

class ExportCncGcode(inkex.OutputExtension):
    """Export all shapes with <gcode:settings> tags as gcode"""
    #select_all = (ShapeElement,)

    def setupMachine(self, stream):
        stream.write( 'G17 (XY plane)\n')
        stream.write( 'G21 (mm mode)\n')
        stream.write( 'G40 (compensation off)\n')
        stream.write( 'G90 (absolute distance mode)\n')

    def save(self, rawStream):
        name = self.svg.name.replace('.svg', '')
        root = GcodeWriter(rawStream, 0)
        root.write('(Inkscape => GCode Save)\n')
        stream = root.indent()
        stream.write(f'(Name: {name})\n')

        # find global gcode globals in the svg XML
        gcodeGlobalsTag = self.svg.xpath('.//gcode:globals',
                                    namespaces={'gcode':'http://xml.thenewentity.com/gcode/0.0'})
        bbox = self.svg.get_page_bbox()

        gcodeGlobals = GcodeGlobals(0.80, translateX = bbox.left, translateY = bbox.bottom)
        gcodeGlobals.echo(stream)

        stream.write('(Setting up Machine)\n')
        self.setupMachine(stream.indent())

        stream.write('(Traversing SVG document tree)\n')
        treeStream = stream.indent()
        for elem in self.svg.iterchildren():
            treeStream.write( f'({getElementNamespace(elem)}:{elem.TAG} => {type(elem).__name__})\n')
            fn = elementExportFunctions.get(type(elem).__name__, exportIgnore)
            fn(
                treeStream.indent(),
                gcodeGlobals,
                elem,
                transforms.Transform(f'translate({bbox.left}, {bbox.bottom})')
                .__mul__(transforms.Transform('scale(1,-1)'))
            )

        gcodeSafeHeight(stream, gcodeGlobals)
        stream.write(f'M02 (end of program)\n')


if __name__ == '__main__':
    ExportCncGcode().run()
