import math
from inkex import bezier

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
    
