from exportIgnore import exportIgnore
from exportPath import exportPath
from exportLayer import exportLayer

from inkex_ex import getElementNamespace, typeName

elementExportFunctions = {
    'Layer': exportLayer,
    'Group': exportLayer,
    'Circle': exportPath,
    'Ellipse': exportPath,
    'PathElement': exportPath,
    'Rectangle': exportPath,
}

def visitElement(stream, elem, transform):
    stream.comment(f'visitElement: {getElementNamespace(elem)}:{elem.TAG} => {typeName(elem)} {elem.get_id()} {elem.label}')
    fn = elementExportFunctions.get(typeName(elem), exportIgnore)
    fn(stream.indent(), elem, transform, {'visitElement':visitElement})

    
