# Inkscape Gcode Exporter 0.0.2

This is an export extension for Inkscape, focusing on producing g-code
that a CNC router can use to cut real-world objects based on an SVG
document.

## Installation:

1. Clone, symlink, or copy this repository into your
Inkscape/extensions directory and restart Inkscape.

## Goals:

1. [done] Export G-Code suitable for use on a CNC router table,
   directly from Inkscape.

2. [in progress] Support offsetting paths to the center, inside, or
   outside of SVG paths.

3. Support filling paths (cutting pockets) using two facing patterns:
   * [in progress] spiral
   * hatch.

4. Support cutting paths to depth in a continuous ramp rather than
   plunge, cut at offset depth, plunge again, etc., until hitting bottom.
   Seems each line segment ought to be able to plunge continuously.

5. Support generating 3d surfacing paths using raster data as a depth
   map. This includes the crazy fill patterns that Inkscape can produce,
   so gradients, waves, yada yada.

6. Provide a UI for specifying the CSS styles that control all of the
   gcode exporting.

## Non-goals

1. Patching Inkscape itself. We will do so if we think it's necessary
   in order to accomplish our goals, but would prefer to avoid this.

## Use:

Gcode is configured through the use of extended CSS styles. This is
nice because we can leverage all of the inheritance rules that CSS
provides.

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

### x-gcode-tool-{x-gcode-tool}-diameter
* Positive distance
* Default: 0.25

Diameter of the tool.

### x-gcode-stepover
* Positive distance
* Default: 0.8 * tool diameter

When filling using spiral, how far should each offset be stepped over?

### x-gcode-edge-mode
* One of: center, inside, outside, v-carve
* Default: center

*Not supported yet*
This controls how the edge of the path is traced in gcode.

### x-gcode-fill-mode
* One of: none, spiral, hatch
* Default: none

*Not supported yet*
This controls how the area of a path is filled in gcode.

### x-gcode-fill-angle
* Angle in degrees

*Not supported yet*
The angle of the lines cut into the surface when 'hatch' is specified for x-gcode-fill-mode

## Known Issues:

* requires converting text to paths.
* mode is ignored - only does "center"
