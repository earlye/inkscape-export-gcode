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
from inkex import bezier, CubicSuperPath, ShapeElement, ColorIdError, ColorError

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

def getDescription(element):
    for child in element.iterchildren():
        if type(child).__name__ == 'Desc':
            return child.text
    return ''

class GcodeGlobals:
    def __init__(self, fulldepth, scaleX = 1.0/25.4, scaleY = -1.0/25.4, translateX = 1, translateY = 7):
        self.fulldepth = fulldepth
        self.safeHeight = 0.25
        self.scaleX = scaleX
        self.scaleY = scaleY
        self.translateX = translateX
        self.translateY = translateY

    def echo(self, stream):
        gcode(stream, '(Globals:)\n')
        gcode(stream,f'( .fulldepth: {self.fulldepth})\n')
        gcode(stream,f'( .safeHeight: {self.safeHeight})\n')
        gcode(stream,f'( .scaleX: {self.scaleX})\n')
        gcode(stream,f'( .scaleY: {self.scaleY})\n')
        gcode(stream,f'( .translateX: {self.translateX})\n')
        gcode(stream,f'( .translateY: {self.translateY})\n')

    pass

def eval(expression, default, context):
    try:
        return float(expression)
    except Exception:
        return default

class GcodeSettings:
    def __init__(self, depth, tool, increment = 0.1, context):
        self.depth = eval(depth, 0.25, context)
        self.tool = tool
        self.increment = increment

def getGcodeSettings(element, gcodeGlobals):
    for child in element.iterchildren():
        if getTagName(child) == 'gcode:settings':
            result = GcodeSettings(child.get("depth"), child.get("tool"), child.get("increment", 0.1))
            return result
    return GcodeSettings(0.25, '', 0.1)

def getTagName(element):
    return os.path.basename(element.xml_path)

def exportIgnore(ignore, gcodeGlobals, stream):
    gcode(stream, f'(ignoring entry of unrecognized type: {type(ignore).__name__})\n');
    pass

def gcode(stream, code):
    stream.write(code.encode('utf-8'))

def gcodeSafeHeight(stream, gcodeGlobals):
    gcode(stream, f'G00 Z{gcodeGlobals.safeHeight} (raise cutter to safe height)\n')

def gcodeCoordinates(X = None, Y = None, Z = None):
    result = ''
    if X != None:
        result += f' X{X}'
    if Y != None:
        result += f' Y{Y}'
    if Z != None:
        result += f' Z{Z}'
    return result.strip()

def gcodeRapid(stream, X, Y, Z, comment):
    gcode(stream, f'G00 {gcodeCoordinates(X,Y,Z)} ({comment})\n')

def gcodeLinear(stream, X, Y, Z, comment):
    gcode(stream, f'G01 {gcodeCoordinates(X,Y,Z)} ({comment})\n')


def cutPathAtDepth(stream, gcodeGlobals, depth, needSafeHeight, path):
    p0 = None
    pInitial = None
    gcode(stream, f'    (carving path at depth:{depth}')
    sX = gcodeGlobals.scaleX
    sY = gcodeGlobals.scaleY
    tX = gcodeGlobals.translateX
    tY = gcodeGlobals.translateY
    for command in path:
        letter = command.letter
        gcode(stream, f'    (command:{command} letter:{letter} type:{type(command).__name__})\n')
        if letter == 'M':
            p0 = (command.args[0] * sX + tX, command.args[1] * sY + tY)
            pInitial = p0
            if needSafeHeight:
                gcodeSafeHeight(stream, gcodeGlobals)
            gcodeRapid(stream, p0[0], p0[1], None, f'rapid to start of curve')
            gcodeLinear(stream, None, None, depth, f'plunge to depth')
            needSafeHeight = True
        if letter == 'C':
            args = command.args
            # gcode(stream, f'      (args: {args})\n')
            p1 = (args[0] * sX + tX, args[1] * sY + tY)
            p2 = (args[2] * sX + tX, args[3] * sY + tY)
            p3 = (args[4] * sX + tX, args[5] * sY + tY)
            # gcode(stream, f'      (p0: {p0} p1:{p1} p2:{p2} p3:{p3})\n')
            for largeT in range(0,100,10):
                t = largeT / 100.0
                bez = [p0,p1,p2,p3]
                pt = bezier.bezierpointatt(bez, t)
                gcodeLinear(stream, pt[0], pt[1], None, f't:{t}')
            gcodeLinear(stream, p3[0], p3[1], None, f't:1.0')
            p0 = p3
            needSafeHeight = True
        if letter == 'L':
            p0 = (command.args[0] * sX + tX, command.args[1] * sY + tY)
            gcodeLinear(stream, p0[0], p0[1], None, f'line')
            needSafeHeight = True
        if letter == 'Z':
            p0 = pInitial
            gcodeLinear(stream, p0[0], p0[1], None, f'zone close')
            needSafeHeight = False
    return needSafeHeight

def gcodePath(stream, gcodeGlobals, gcodeSettings, path):
    gcode(stream,f'  (gcodeSettings.depth: {gcodeSettings.depth})\n')
    gcode(stream,f'  (gcodeSettings.tool: {gcodeSettings.tool})\n')
    gcode(stream,f'  (path commands:)\n')
    csp = CubicSuperPath(path).to_path()
    gcode(stream,f'    (cubicsuperpath parsed:{csp} type:{type(csp).__name__})\n')

    depth = 0
    needSafeHeight = True
    while depth < gcodeSettings.depth:
        needSafeHeight = cutPathAtDepth(stream, gcodeGlobals, -depth, needSafeHeight, csp)
        depth += gcodeSettings.increment
    if depth != gcodeSettings.increment:
        cutPathAtDepth(stream, gcodeGlobals, -gcodeSettings.depth, needSafeHeight, csp)

def exportEllipse(ellipse, gcodeGlobals, stream):
    gcodeSettings = getGcodeSettings(ellipse, stream)
    if gcodeSettings is None:
        gcode(stream,f'(type:"{type(element).__name__}" id:"{element.get_id()}" -- skipping because no gcodeSettings)\n')
        return

    gcode(stream,f'\n\n')
    gcode(stream,f'(type:"Ellipse" id:"{ellipse.get_id()}" radius:"{ellipse.radius}" center:"{ellipse.center}")\n')
    gcodePath(stream, gcodeGlobals, gcodeSettings, ellipse.path)

def exportPath(element, gcodeGlobals, stream):
    gcodeSettings = getGcodeSettings(element, stream)
    if gcodeSettings is None:
        gcode(stream,f'(type:"{type(element).__name__}" id:"{element.get_id()}" -- skipping because no gcodeSettings)\n')
        return

    gcode(stream,f'\n\n')
    gcode(stream,f'(type:"{type(element).__name__}" id:"{element.get_id()}")\n')
    gcodePath(stream, gcodeGlobals, gcodeSettings, element.path)

elementExportFunctions = { 'Layer': exportIgnore, 'Ellipse': exportEllipse , 'PathElement': exportPath, 'TextElement': exportPath, 'Tspan': exportPath }

class ExportCncGcode(inkex.OutputExtension):
    """Export all shapes with <gcode:settings> tags as gcode"""
    select_all = (ShapeElement,)

    def save(self, stream):
        name = self.svg.name.replace('.svg', '')
        gcode(stream,'(Inkscape => GCode Save)\n')
        gcode(stream,f'(Name: {name})\n')

        # TODO: find global gcode globals in the svg XML
        gcodeGlobals = GcodeGlobals(0.80)
        gcode(stream, '\n\n')
        gcodeGlobals.echo(stream)
        gcode(stream, 'G90 (absolute distance mode)\n')

        for elem in self.svg.selection.paint_order().values():
            fn = elementExportFunctions.get(type(elem).__name__, exportIgnore)
            fn(elem, gcodeGlobals, stream)

        gcodeSafeHeight(stream, gcodeGlobals)
        gcode(stream,f'M02 (end of program)\n')


if __name__ == '__main__':
    ExportCncGcode().run()
