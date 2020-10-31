def getElementNamespace(elem):
    return elem.nsmap.get(elem.prefix, None)

def getElementFullTagname(elem):
    return (getElementNamespace(elem), elem.TAG)

def typeName(element):
    try:
        return type(element).__name__
    except Error:
        return '<unrecognized>'
