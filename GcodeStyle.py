import json
import re

distanceRegex = re.compile('(([0-9]*(\\.[0-9]*)?)(/([0-9]*(\\.[0-9]*)?))?)(px|in|mm|cm|Q|pc|pt)?')
unitFactors = { 'in': 25.4, 'px': 25.4 / 96.0, 'cm': 1.0/100.0, 'mm': 1.0, 'Q': 40.0/100.0, 'pc': 25.4/6.0, 'pt': 25.4/72.0 }
assert distanceRegex.match('3in')
assert distanceRegex.match('.3in')
assert distanceRegex.match('1/2in')

def isNumber(value):
    return isinstance(value, (int, float, complex)) and not isinstance(value, bool)

def mmFromInch(value):
    return value * 25.4

def distance(value, defaultValue = None, stream = None):
    if isNumber(value):
        return value
    scaledValue = defaultValue
    unitValue = None
    unit = None
    if not value is None:
        match = distanceRegex.match(value)
        if not match is None:
            numerator = float(match.group(2))
            denominator = match.group(5)
            if denominator is None:
                denominator = 1.0
            else:
                denominator = float(denominator)
            unit = match.group(7) or 'mm'
            unitFactor = unitFactors.get(unit, 'mm')

            unitValue = numerator / denominator
            scaledValue = unitValue * unitFactor
    if stream:
        stream.comment(f"distance: \"{value}\" {unitValue}{unit} {scaledValue}mm")
    return scaledValue

class GcodeStyle:
    def __init__(self, style, stream=None):
        self.display = style.get("display", "inline")
        self.depth = distance(style.get("-gcode-depth", None), 0)
        self.startDepth = distance(style.get("-gcode-start-depth", None), 0)
        self.depthIncrement = distance(style.get("-gcode-depth-increment", None), mmFromInch(0.1))
        if self.depthIncrement < 0:
            self.depthIncrement = 0.1
        if self.depthIncrement > self.depth:
            self.depthIncrement = self.depth

        self.tabHeight = distance(style.get("-gcode-tab-height", 0), None)
        self.tabWidth = distance(style.get("-gcode-tab-width", None), None)
        self.tabStartInterval = distance(style.get("-gcode-tab-start-interval", None), None)
        self.tabDepth = self.depth - self.tabHeight

        self.tool = style.get("-gcode-tool", 'default')
        self.toolDiameter = distance(style.get(f"-gcode-tool-{self.tool}-diameter", mmFromInch(0.25)))
        self.toolStepOver = distance(style.get(f"-gcode-tool-{self.tool}-stepover", self.toolDiameter * 0.8 ))
        self.stepOver = distance(style.get("-gcode-stepover", self.toolStepOver))

        # Todo: switch from curveIncrement to maxCurveSegmentLength
        self.curveIncrement = distance(style.get("-gcode-curve-increment", None), 0.05)
        if self.curveIncrement < 0:
            self.curveIncrement = 0.05
        if self.curveIncrement > 1:
            self.curveIncrement = 1
        self.edgeMode = style.get("-gcode-edge-mode", 'center')
        self.fillMode = style.get("-gcode-fill-mode", '')

        self.feedxy = distance(style.get("-gcode-feed-xy", None), mmFromInch(25))
        self.feedz = distance(style.get("-gcode-feed-z", None), mmFromInch(10))

        self.rapidxy = distance(style.get("-gcode-rapid-xy", None), mmFromInch(60))
        self.rapidz = distance(style.get("-gcode-rapid-z", None), mmFromInch(60))
        self.supportsCubicSpline = False
        self.safeHeight = mmFromInch(0.25)

    def hasTabs(self):
        return self.tabHeight and self.tabWidth and self.tabStartInterval

def getGcodeStyle(stream, style):
    stream.comment(f'SvgStyle: {style}')
    result = GcodeStyle(style, stream=stream)
    stream.comment(f'GcodeStyle: {json.dumps(result.__dict__)}')
    return result

def getElementGcodeStyle(stream, element):
    return getGcodeStyle(stream, element.composed_style())
