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
    def __init__(self, fulldepth):
        self.fulldepth = fulldepth
        self.safeHeight = 0.25
    pass

class GcodeSettings:
    def __init__(self, depth, tool):
        self.depth = depth
        self.tool = tool

def getGcodeSettings(element, gcodeGlobals):
    for child in element.iterchildren():
        if getTagName(child) == 'gcode:settings':
            result = GcodeSettings(child.get("depth"), child.get("tool"))
            return result
    return GcodeSettings(0.25, '')

def getTagName(element):
    return os.path.basename(element.xml_path)

def exportIgnore(ignore, gcodeGlobals, stream):
    gcode(stream, f'(ignoring entry of unrecognized type: {type(ignore).__name__})\n');
    pass

def gcode(stream, code):
    stream.write(code.encode('utf-8'))

def gcodeSafeHeight(stream, gcodeGlobals):
    gcode(stream, f'G00 Z{gcodeGlobals.safeHeight} (raise cutter to safe height)\n')

def gcodeRapid(stream, X, Y, Z, comment):
    gcode(stream, f'G00 X{X} Y{Y} ({comment})\n')

def gcodeLinear(stream, X, Y, Z, comment):
    gcode(stream, f'G01 X{X} Y{Y} ({comment})\n')

def gcodePath(stream, gcodeGlobals, gcodeSettings, path):
    gcode(stream,f'  (gcodeSettings.depth: {gcodeSettings.depth})\n')
    gcode(stream,f'  (gcodeSettings.tool: {gcodeSettings.tool})\n')
    gcode(stream,f'  (path commands:)\n')
    csp = CubicSuperPath(path).to_path()
    gcode(stream,f'    (cubicsuperpath parsed:{csp} type:{type(csp).__name__})\n')
    p0 = None
    pInitial = None
    for command in csp:
        letter = command.letter
        gcode(stream, f'    (command:{command} letter:{letter} type:{type(command).__name__})\n')
        if letter == 'M':
            p0 = (command.args[0], -command.args[1])
            pInitial = p0
            gcodeSafeHeight(stream, gcodeGlobals)
            gcodeRapid(stream, p0[0], p0[1], None, f'rapid to start of curve')
        if letter == 'C':
            args = command.args
            # gcode(stream, f'      (args: {args})\n')
            p1 = (args[0], -args[1])
            p2 = (args[2], -args[3])
            p3 = (args[4], -args[5])
            # gcode(stream, f'      (p0: {p0} p1:{p1} p2:{p2} p3:{p3})\n')
            for t in range(0,1000,100):
                bez = [p0,p1,p2,p3]
                pt = bezier.bezierpointatt(bez, t / 1000.0)
                gcodeLinear(stream, pt[0], pt[1], None, f't:{t/100.0}')
            gcodeLinear(stream, p3[0], p3[1], None, f't:1.0')
            p0 = p3
        if letter == 'L':
            p0 = (command.args[0], -command.args[1])
            gcodeLinear(stream, p0[0], p0[1], None, f'line')
        if letter == 'Z':
            p0 = pInitial
            gcodeLinear(stream, p0[0], p0[1], None, f'zone close')

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
        gcode(stream, '(Globals:)\n')
        gcode(stream,f'( .fulldepth: {gcodeGlobals.fulldepth})\n')
        gcode(stream, 'G90 (absolute distance mode)\n')

        for elem in self.svg.selection.paint_order().values():
            fn = elementExportFunctions.get(type(elem).__name__, exportIgnore)
            fn(elem, gcodeGlobals, stream)

        gcodeSafeHeight(stream, gcodeGlobals)
        gcode(stream,f'M02 (end of program)\n')


if __name__ == '__main__':
    ExportCncGcode().run()
