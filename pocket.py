from float_range import float_range

def pocket(stream, gcodeStyle, zones, transform):
    if not gcodeStyle.depth:
        stream.comment("Depth is 0. Skipping path")
        return
    bounds = zones.getBounds()
    stream.comment(f"Pocket bounds: {bounds}")
    for depth in float_range(-gcodeStyle.startDepth, -gcodeStyle.depth, -gcodeStyle.depthIncrement, True):
        stream.comment(f"depth:{depth}")
        streamScan = stream.indent()
        for y in float_range(bounds.y0 + gcodeStyle.toolDiameter / 2.0, bounds.y1 - gcodeStyle.toolDiameter / 2.0, gcodeStyle.toolStepOver):
            streamScan.comment(f"y:{y}")
            streamSegments = streamScan.indent()
            intersections = []
            for polyline in zones.polylines:
                if not polyline.closed:
                    stream.comment("Skipping polyline because it isn't closed.")
                    continue
                p0n = polyline.points[0]
                # streamSegments.comment(f"polyline:{polyline}")
                for p1 in polyline.points[1:]:
                    p0 = p0n
                    p0n = p1
                    x0, y0 = p0[0], p0[1]
                    x1, y1 = p1[0], p1[1]
                    if (y1 > y0):
                        if (y < y0) or (y>y1):
                            continue
                        pass
                    else:
                        if (y < y1) or (y>y0):
                            continue
                        pass
                    # https://en.wikipedia.org/wiki/Linear_interpolation
                    # (y-y0)/(x-x0) = (y1-y0)/(x1-x0)
                    # solving for x...
                    # (x-x0)/(y-y0) = (x1-x0)/(y1-y0)
                    # (x-x0) = (y-y0)(x1-x0)/(y1-y0)
                    if y1 == y0:
                        #intersections.append(x0)
                        #intersections.append(x1)
                        continue
                    x = (y-y0)*(x1-x0)/(y1-y0) + x0
                    intersections.append(x)
                    streamSegments.comment(f"p0:{p0} p1:{p1} x:{x} intersections:{intersections}")
            # at this point, intersections contains an unsorted list of x coordinates. If we sort them and alternate up/down, we should
            # get the pattern we want.
            up = True
            for x in sorted(intersections):
                if up:
                    streamSegments.safe_height(gcodeStyle)
                    streamSegments.rapid(comment='rapid to start of polyline', X=x, Y=y, F=gcodeStyle.rapidxy)
                    up = False
                else:
                    streamSegments.linear('plunge', Z=depth,F=gcodeStyle.feedz)
                    streamSegments.linear('scan', X=x,Y=y,F=gcodeStyle.feedxy)
                    streamSegments.safe_height(gcodeStyle)
                    up = True
