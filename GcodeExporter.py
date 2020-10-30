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

    def write(self, code):
        self.stream.write((' ' * self.depth + code).encode('utf-8'))

    def code(self, code=None, comment = None, **kwargs):
        self.write(f'{xstr(code)}{gcodeCoordinates(**kwargs)}{wrapComment(comment," ")}\n')

    def comment(self, comment):
        self.write(wrapComment(comment) + '\n')

    def indent(self):
        return GcodeExporter(self.stream, self.document, self.depth + 2)

    def rapid(self, comment, **kwargs):
        self.code(code='G00',comment=comment, **kwargs)

    def linear(self, comment, **kwargs):
        self.code(code='G01',comment=comment, **kwargs)
