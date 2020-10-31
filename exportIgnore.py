import inkex_ex

def exportIgnore(stream, gcodeStyle, element, *args, **kwargs):
    stream.comment(f'exportIgnore: ignoring entry of unrecognized type: {inkex_ex.typeName(element)}');
    pass
