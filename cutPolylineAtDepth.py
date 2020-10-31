import geometry

def cutPolylineAtDepth(stream, polyline, gcodeStyle, startDepth, finalDepth, needSafeHeight):
    if not len(polyline.points):
        return
    totalL = polyline.getLength()
    depthRange = finalDepth - startDepth

    p0 = polyline.points[0]
    l = 0
    d = startDepth

    tabStart = totalL + 1
    tabEnd = totalL + 1
    tabDepth = gcodeStyle.tabDepth
    inTab = False
    useTabs = gcodeStyle.hasTabs()
    if useTabs:
        tabStart = gcodeStyle.tabStartInterval
        tabEnd = tabStart + gcodeStyle.tabWidth

    stream.comment(f'cutting polyline ramp: {startDepth} -> {finalDepth} needSafeHeight:{needSafeHeight}')
    if needSafeHeight:
        stream.safe_height(gcodeStyle)
    stream.rapid(comment='rapid to start of polyline', X=p0[0], Y=p0[1], F=gcodeStyle.rapidxy)
    stream.linear(comment='plunge to start depth', Z=d, F = gcodeStyle.feedz)

    for p1 in polyline.points[1:]:
        segmentL = geometry.segmentLength(p0,p1)
        startL = l
        endL = l + segmentL
        lFraction = endL / totalL
        d = startDepth + lFraction * depthRange # interpolate depth at p1

        while not inTab and (tabStart < startL):
            tabStart += gcodeStyle.tabStartInterval
            tabEnd = tabStart + gcodeStyle.tabWidth

        finishedSegment = False
        while not finishedSegment:
            if not inTab:
                if endL < tabStart or d > -tabDepth:
                    # either segment ends before tab, or whole segment is above tab
                    # NOTE: this presumes we only ramp *down*.
                    stream.linear(comment=f'lFraction:{lFraction} d:{d} tabDepth:{-tabDepth}', X=p1[0], Y=p1[1], Z=d, F=gcodeStyle.feedxy)
                    l = startL
                    finishedSegment = True
                else: # tab starts in this line segment
                    tabStartLFraction = tabStart / totalL
                    tabStartRampDepth = startDepth + tabStartLFraction * depthRange
                    tabSegmentFraction = (tabStart - startL) / (endL - startL)

                    # figure out x,y of tab start
                    tabStartPoint = (p0[0] + tabSegmentFraction*(p1[0]-p0[0]),
                                     p0[1] + tabSegmentFraction*(p1[1]-p0[1]))
                    stream.linear(comment=f'ramp to tab start', X=tabStartPoint[0], Y=tabStartPoint[1],
                                Z=tabStartRampDepth, F=gcodeStyle.feedxy)
                    stream.linear(comment=f'lift to tab depth', Z=-tabDepth, F=gcodeStyle.rapidz)
                    inTab = True

            if inTab:
                if tabEnd < endL:
                    tabStopLFraction = tabEnd / totalL
                    tabStopRampDepth = startDepth + tabStartLFraction * depthRange
                    tabSegmentFraction = (tabEnd - startL) / (endL - startL)

                    tabEndPoint = (p0[0] + tabSegmentFraction*(p1[0]-p0[0]),
                                   p0[1] + tabSegmentFraction*(p1[1]-p0[1]))

                    stream.linear(comment=f'skim tab top tabStop:{tabStopLFraction}', X=tabEndPoint[0],Y=tabEndPoint[1], F=gcodeStyle.feedxy)
                    stream.linear(comment=f'plunge to post-tab ramp top', Z=tabStopRampDepth, F=gcodeStyle.feedz)
                    tabStart = tabStart + gcodeStyle.tabStartInterval
                    tabEnd = tabStart + gcodeStyle.tabWidth
                    inTab = False
                else:
                    stream.linear(comment=f'skim tab top endL:{endL} tabEnd:{tabEnd}', X=p1[0],Y=p1[1], F=gcodeStyle.feedxy)
                    finishedSegment = True
            l = endL
        p0 = p1
    stream.comment(f'polyline.closed: {polyline.closed}')
    return not polyline.closed
