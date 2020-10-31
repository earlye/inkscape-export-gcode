#!/usr/bin/env python
# coding=utf-8
#
# Copyright (c) 2020 - Early Ehlinger, thenewentity.com
#
"""
Export cnc gcode (.gcode)
"""

import GcodeExporter
from inkex import OutputExtension, transforms
from visitElement import visitElement

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class ExportCncGcode(OutputExtension):
    """Export all shapes with <-gcode-depth> CSS attributes"""
    
    def setupMachine(self, stream):
        stream.select_plane_xy(comment='XY plane')
        stream.select_units_mm(comment='mm mode')
        stream.tool_radius_compensation_off(comment='compensation off')
        stream.absolute_distance_mode(comment='absolute distance mode')

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

        stream.end_program(comment='end of program')

if __name__ == '__main__':
    ExportCncGcode().run()
