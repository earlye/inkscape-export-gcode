#!/usr/bin/env python
# coding=utf-8
#
# Copyright (c) 2020 - Early Ehlinger, thenewentity.com
#
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

def encodeComment(comment):
    return comment.replace("(","{").replace(")","}")

def wrapComment(comment, prefix = None):
    return f'{xstr(prefix)}({encodeComment(comment)})' if comment else ''

def xstr(s):
    if s is None:
        return ''
    return str(s)

class GcodeExporter:
    def __init__(self, stream, document, depth):
        self.stream = stream
        self.depth = depth
        self.document = document

    def _write(self, code):
        self.stream.write((' ' * self.depth + code).encode('utf-8'))

    def _code(self, code=None, comment = None, **kwargs):
        self._write(f'{xstr(code)}{gcodeCoordinates(**kwargs)}{wrapComment(comment," ")}\n')

    def comment(self, comment):
        self._write(wrapComment(comment) + '\n')

    def indent(self):
        return GcodeExporter(self.stream, self.document, self.depth + 2)

    def rapid(self, comment, **kwargs):
        self._code(code='G00', comment=comment, **kwargs)

    def linear(self, comment, **kwargs):
        self._code(code='G01', comment=comment, **kwargs)

    def select_plane_xy(self, comment):
        self._code(code='G17', comment=comment)

    def select_units_mm(self, comment):
        self._code(code='G21', comment=comment)

    def tool_radius_compensation_off(self, comment):
        self._code(code='G40', comment=comment)

    def absolute_distance_mode(self, comment):
        self._code(code='G90', comment=comment)

    def end_program(self, comment='end of program'):
        self._code(code='M02', comment=comment)

    def safe_height(self, gcodeStyle, comment='raise cutter to safe height'):
        self._code(code='G00', Z=gcodeStyle.safeHeight, F=gcodeStyle.rapidz, comment=comment)
        
