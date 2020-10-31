import GcodeStyle

def exportLayer(stream, element, transform, methods):
    gcodeStyle = GcodeStyle.getElementGcodeStyle(stream, element)
    if gcodeStyle.display == 'none':
        stream.comment("Style.display:none. Skipping layer")
        return
    for child in reversed(list(element.iterchildren())):
        methods['visitElement'](stream.indent(), child, transform)
    stream.safe_height(gcodeStyle)
