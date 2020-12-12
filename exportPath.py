import geometry
import inkex_ex
import GcodeStyle

from inkex import CubicSuperPath
from contour import contour
from pocket import pocket

def exportPath(stream, element, transform, methods):
    gcodeStyle = GcodeStyle.getElementGcodeStyle(stream, element)
        
    stream.comment(f'exportPath: exporting element type:"{inkex_ex.typeName(element)}" id:"{element.get_id()}"')
    effectiveTransform = transform.__mul__(element.composed_transform())
    #stream.comment(f'composed_transform:"{element.composed_transform()}"')
    #stream.comment(f'transform:"{transform}"')
    #stream.comment(f'effectiveTransform:"{effectiveTransform}"')

    if not gcodeStyle.depth:
        stream.comment("Depth is 0. Skipping path")
        return
    if gcodeStyle.display == 'none':
        stream.comment("Style.display:none. Skipping path")
        return

    path = element.path
    # stream.comment(f"path:{path}")
    stream.comment(f"gcodeStyle:{gcodeStyle.__dict__}")
    csp = CubicSuperPath(path).to_path()
    stream.comment(f"csp:{csp}")
    zones = geometry.cspToZones(stream, csp, gcodeStyle, effectiveTransform)

    contour(stream.indent(), gcodeStyle, zones, effectiveTransform)
    if gcodeStyle.fillMode == 'hatch':
        pocket(stream.indent(), gcodeStyle, zones, effectiveTransform)
