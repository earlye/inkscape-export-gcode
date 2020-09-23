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

def wrapComment(comment, prefix = None):
    return f'{prefix}({comment})' if comment else ''

class GcodeWriter:
    def __init__(self, stream, depth):
        self.stream = stream
        self.depth = depth

    def write(self, code):
        self.stream.write((' ' * self.depth + code).encode('utf-8'))

    def code(self, code=None, comment = None, X = None, Y = None, Z = None, F = None):
        self.write(f'{code}{gcodeCoordinates(X=X,Y=Y,Z=Z,F=F)}{wrapComment(comment," ")}\n')

    def comment(self, comment):
        self.write(wrapComment(comment) + '\n')

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
        stream.comment('Globals:')
        s2 = stream.indent()
        s2.comment(f'.fulldepth: {self.fulldepth}')
        s2.comment(f'.safeHeight: {self.safeHeight}')
        s2.comment(f'.scaleX: {self.scaleX}')
        s2.comment(f'.scaleY: {self.scaleY}')
        s2.comment(f'.translateX: {self.translateX}')
        s2.comment(f'.translateY: {self.translateY}')

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

    stream.comment(f'GcodeStyle depth:{depth} tool:{tool} increment:{increment} mode:{mode}')

    return GcodeStyle(depth, tool, increment, mode)

def getTagName(element):
    return os.path.basename(element.xml_path)

def typeName(element):
    try:
        return type(element).__name__
    except Error:
        return '<unrecognized>'

def exportIgnore(stream, gcodeGlobals, element, *args, **kwargs):
    stream.comment(f'ignoring entry of unrecognized type: {typeName(element)}');
    pass


def gcodeSafeHeight(stream, gcodeGlobals):
    stream.write(f'G00 Z{gcodeGlobals.safeHeight} (raise cutter to safe height)\n')

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
    return result

def gcodeRapid(stream, comment, X = None, Y = None, Z = None, F = None ):
    stream.code(code='G00', X=X, Y=Y, Z=Z, F=F, comment=comment)

def gcodeLinear(stream, comment, X = None, Y = None, Z = None, F = None ):
    stream.code(code='G01', X=X, Y=Y, Z=Z, F=F, comment=comment)

def cutPathAtDepth(stream, gcodeGlobals, transform, depth, needSafeHeight, path):
    p0 = None
    pInitial = None
    stream.comment(f'carving path at depth:{depth}')
    for command in path:
        letter = command.letter
        stream.comment(f'svg path command:"{command}"')
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
            # stream.write(f'  (args: {args})\n')
            p1 = transform.apply_to_point((args[0], args[1]))
            p2 = transform.apply_to_point((args[2], args[3]))
            p3 = transform.apply_to_point((args[4], args[5]))
            if gcodeGlobals.supportsCubicSpline:
                p1i = (p1[0] - p0[0], p1[1] - p0[0])
                p2i = (p2[0] - p1[0], p2[1] - p1[1])
                stream.write(f'G5 I{p1i[0]} J{p1i[1]} P{p2i[0]} Q{p2i[1]} X{p3[0]} Y{p3[1]} (cubic spline)\n')
            else:
                # stream.write(f'  (p0: {p0} p1:{p1} p2:{p2} p3:{p3})\n')
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
    stream.comment(f'path commands:')
    stream.comment(f'path:{path}')
    csp = CubicSuperPath(path).to_path()
    stream.comment(f'cubicsuperpath parsed:{csp} type:{type(csp).__name__}')

    depth = 0
    needSafeHeight = True
    while depth < GcodeStyle.depth:
        needSafeHeight = cutPathAtDepth(stream.indent(), gcodeGlobals, transform, -depth, needSafeHeight, csp)
        depth += GcodeStyle.increment
    if depth != GcodeStyle.increment:
        cutPathAtDepth(stream.indent(), gcodeGlobals, transform, -GcodeStyle.depth, needSafeHeight, csp)

def exportEllipse(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.comment(f'type:"Ellipse" id:"{element.get_id()}" radius:"{element.radius}" center:"{element.center}"')
    stream.comment(f'composed_transform:"{element.composed_transform()}"')
    stream.comment(f'transform:"{transform}"')
    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.comment(f'effectiveTransform:"{effectiveTransform}"')
    gcodePath(stream.indent(), gcodeGlobals, GcodeStyle, element.path, effectiveTransform)

def exportPath(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.comment(f'type:"{type(element).__name__}" id:"{element.get_id()}"')
    stream.comment(f'composed_transform:"{element.composed_transform()}"')
    stream.comment(f'transform:"{transform}"')
    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.comment(f'effectiveTransform:"{effectiveTransform}"')
    gcodePath(stream.indent(), gcodeGlobals, GcodeStyle, element.path, effectiveTransform)

def exportTextElement(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.comment(f'type:"{type(element).__name__}" id:"{element.get_id()}"')
    stream.comment(f'dir:"{element.__dir__()}"')
    stream.comment(f'elements._selected.__dir__():"{elements._selected.__dir__()}"')
    stream.comment(f'path: {element.get_path()}') # path is empty. :WTF:
    # stream.comment(f'makeelement: {element.makeelement()}') apparently from lxml, requires one param, probably not how to get a path

    for child in element.tspans():
        stream.comment(f'{getElementNamespace(child)}:{child.TAG} => {type(child).__name__}')
        fn = elementExportFunctions.get(type(child).__name__, exportIgnore)
        fn(stream.indent(), gcodeGlobals, child, transform)

def exportTspan(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)

    stream.write(f'\n\n')
    stream.comment(f'type:"{type(element).__name__}" id:"{element.get_id()}"')
    stream.comment(f'dir:"{element.__dir__()}"')
    stream.comment(f'path: {element.get_path()}')
    for child in element.iterchildren():
        stream.comment(f'{getElementNamespace(child)}:{child.TAG} => {type(child).__name__}')
        fn = elementExportFunctions.get(type(child).__name__, exportIgnore)
        fn(stream.indent(), gcodeGlobals, child, transform)

def exportLayer(stream, gcodeGlobals, element, transform):
    GcodeStyle = getGcodeStyle(stream, element)
    for child in element.iterchildren():
        stream.comment(f'{getElementNamespace(child)}:{child.TAG} => {type(child).__name__}')
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
        stream.code(code='G17', comment='XY plane')
        stream.code(code='G21', comment='mm mode')
        stream.code(code='G40', comment='compensation off')
        stream.code(code='G90', comment='absolute distance mode')

    def save(self, rawStream):
        name = self.svg.name.replace('.svg', '')
        root = GcodeWriter(rawStream, 0)
        root.comment('Inkscape => GCode Save')
        stream = root.indent()
        stream.comment(f'Name: {name}')

        # find global gcode globals in the svg XML
        gcodeGlobalsTag = self.svg.xpath('.//gcode:globals',
                                    namespaces={'gcode':'http://xml.thenewentity.com/gcode/0.0'})
        bbox = self.svg.get_page_bbox()

        gcodeGlobals = GcodeGlobals(0.80, translateX = bbox.left, translateY = bbox.bottom)
        gcodeGlobals.echo(stream)

        stream.comment('Setting up Machine')
        self.setupMachine(stream.indent())

        stream.comment('Traversing SVG document tree')
        treeStream = stream.indent()
        for elem in self.svg.iterchildren():
            treeStream.comment(f'{getElementNamespace(elem)}:{elem.TAG} => {type(elem).__name__}')
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
