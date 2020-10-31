from float_range import float_range
from cutPolylineAtDepth import cutPolylineAtDepth

def contour(stream, gcodeStyle, zones, transform):
    for polyline in zones.polylines:
        stream.comment(f"polyline: {polyline.__dict__}")
        needSafeHeight = True
        for depth in float_range(gcodeStyle.startDepth, gcodeStyle.depth, gcodeStyle.depthIncrement, includeStop=True):
            nextDepth = min(depth + gcodeStyle.depthIncrement, gcodeStyle.depth)
            needSafeHeight = cutPolylineAtDepth(stream, polyline, gcodeStyle,
                                                -depth, -nextDepth, needSafeHeight) and needSafeHeight
        # provided by includeStop=True cutPolylineAtDepth(stream, polyline, gcodeStyle, -depth, -depth, needSafeHeight)
