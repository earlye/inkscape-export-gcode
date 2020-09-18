## Inkscape Gcode Exporter 0.0.1

### Installation:

1. Clone, symlink, or copy this repository into your
Inkscape/extensions directory and restart Inkscape.

### Use:

Instructions coming soon.

### Known Issues:

* doesn't scale the drawing from inkscape's coordinate system to, you know, real world units. So it wants to cut ENORMOUS items. I.e., I need to have calibration settings.
* group transforms are not handled (this is why the text in the gcode isn't stretched out in the screenshots...)
* doesn't lower the cutter.
* requires converting text to paths.
* mode is ignored - only does "outline"
