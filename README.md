# Inkscape Gcode Exporter 0.0.2

This is an export extension for Inkscape, focusing on producing g-code
that a CNC router can use to cut real-world objects based on an SVG
document.

## Installation:

1. Clone, symlink, or copy this repository into your
Inkscape/extensions directory and restart Inkscape.

## Use:

Gcode is configured through the use of extended CSS styles. This is
nice because we can leverage all of the inheritance rules that CSS
affords.

Until a UI is developed to edit them, your best bet is to use the XML
Editor in Inkscape (Edit => XML Editor)

Extended CSS Styles for GCODE control:

### x-gcode-depth
* Value indicating depth of cut
* Default: -0.25 (Trace outline above surface)

### x-gcode-increment
* Value greater than 0 and less than 1.
* Default: 0.1

This controls how many 't' increments to use when interpolating curves
into g-code line segments. Smaller numbers yield smoother curves at
the cost of longer gcode.

### x-gcode-tool
* Reference to a def containing a tool
* Default: ''

### x-gcode-mode
* One of: center, inside, outside, spiral, angled-fill, v-carve
* Default: center

*Not supported yet*
This controls how the path is traced in gcode.
If angled-fill is specified, x-gcode-fill-angle controls the angle of the lines cut into the surface
If v-carve is specified, the tool specified by x-gcode-tool will control the cutter angle. (TBD)

### x-gcode-fill-angle
* Angle in degrees

*Not supported yet*
The angle of the lines cut into the surface.

## Known Issues:

* requires converting text to paths.
* mode is ignored - only does "center"
