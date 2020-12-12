import GcodeStyle

def exportLayer(stream, element, transform, methods):
    gcodeStyle = GcodeStyle.getElementGcodeStyle(stream, element)
    if gcodeStyle.display == 'none':
        stream.comment("Style.display:none. Skipping layer")
        return

    effectiveTransform = transform.__mul__(element.composed_transform())
    stream.comment(f"layer: originalTransform: {transform} transform: {element.composed_transform()} effectiveTransform:{effectiveTransform}")

    for child in reversed(list(element.iterchildren())):
        methods['visitElement'](stream.indent(), child, effectiveTransform)
    stream.safe_height(gcodeStyle)
