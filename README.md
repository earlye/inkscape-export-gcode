# Inkscape Gcode Exporter 0.0.3

This is an export extension for Inkscape, focusing on producing g-<code
that a CNC router can use to cut real-world objects based on an SVG
document.

## Installation:

1. Clone, symlink, or copy this repository into your
Inkscape/extensions directory and restart Inkscape.

## Use:

Gcode is configured through the use of extended CSS styles. This is
nice because we can leverage all of the inheritance rules that CSS
provides.

Until a UI is developed to edit them, your best bet is to use the XML
Editor in Inkscape (Edit => XML Editor)

## Extended CSS Styles reference:

### -gcode-curve-increment
* Value greater than 0 and less than 1.
* Default: 0.05


This controls how many 't' increments to use when interpolating curves
into g-code line segments. Smaller numbers yield smoother curves at
the cost of longer gcode.

### -gcode-depth
* Value indicating depth of the entire path/pocket
* Default: None (ignore path)

### -gcode-depth-increment
* Value indicates depth of cut
* Default: 0.1in
* Max: -gcode-depth

### -gcode-edge-mode
* One of: center, inside, outside, v-carve
* Default: center

*Not supported yet*
This controls how the edge of the path is traced in gcode.

### -gcode-feed-xy
* Positive distance indicating how quickly to feed horizontally while cutting.

### -gcode-feed-z
* Positive distance indicating how quickly to feed vertically while cutting.

### -gcode-fill-angle
* Angle in degrees

*Not supported yet*
The angle of the lines cut into the surface when 'hatch' is specified for -gcode-fill-mode
Currently ignored: fill-angle is always '0'.

### -gcode-fill-mode
* One of: none, hatch
* Default: none
* Reserved values for future: spiral

This controls how the area of a path is filled in gcode.
Only closed paths will actually be cut.

none: Do not cut the area of the path, only cut the contour.
hatch: Cut a pocket by tracing lines spaced by `-gcode-stepover`, at angle specified by `-gcode-fill-angle`

### -gcode-rapid-xy
* Positive distance indicating how quickly to feed horizontally while at safe height

### -gcode-rapid-z
* Positive distance indicating how quickly to feed vertically while at or going to safe height

### -gcode-tab-height
* Distance indicates how tall tabs should be
* Default: None

### -gcode-tab-width
* Distance indicates how wide tabs should be
* Default: None

### -gcode-tab-start-interval
* Distance indicates how far apart tabs should be along perimeter
* Default: None

### -gcode-tool
* Reference to a def containing a tool
* Default: ''

### -gcode-tool-{-gcode-tool}-diameter
* Positive distance
* Default: 0.25

Diameter of the tool.

### -gcode-tool-{-gcode-tool}-stepover
* Positive distance
* Default: 0.25

When filling using spiral, how much does this tool want to be stepped over?

### -gcode-stepover
* Positive distance
* Default: 0.8 * tool diameter

When filling using spiral, how far should each offset be stepped over?



## Goals:

1. [done] Export G-Code suitable for use on a CNC router table,
   directly from Inkscape.

2. [Done] Support cutting paths to depth in a continuous ramp rather than
   plunge, cut at offset depth, plunge again, etc., until hitting bottom.
   Seems each line segment ought to be able to plunge continuously.

3. [Done] Support generating tabs.

4. [on hold] Support offsetting paths to the center, inside, or
   outside of SVG paths.

5. Support filling paths (cutting pockets) using two facing patterns:
   * [on hold] spiral
   * [DONE] hatch.

6. Support generating 3d surfacing paths using raster data as a depth
   map. This includes the crazy fill patterns that Inkscape can produce,
   so gradients, waves, yada yada.

7. [on hold] _Looks like it will require a plugin rather than a python
   extension :-(_ Provide a UI for specifying the CSS styles that
   control all of the gcode exporting.

## Requirements:

1. Inkscape v1.1 is recommended, because earlier versions drop
   extended CSS attributes whenever you take an action that affects
   CSS values, e.g., changing the visibility or color of an
   object. This will work with earlier versions, but the inconvenience
   of losing your settings when turning layers on and off
   is... annoying.

   * The retention of custom CSS properties was added to Inkscape by
     this [pull request](https://gitlab.com/inkscape/inkscape/-/merge_requests/2405)

   * This is the first [build pipeline](https://gitlab.com/inkscape/inkscape/-/pipelines/204740791)
     that included this feature. It has linux and mac artifacts. The latest development
     version for windows _does_ have this feature.>

## Non-goals

1. Patching Inkscape itself. We will do so if we think it's necessary
   in order to accomplish our goals (and have - see "Requirements"),
   but would prefer to avoid this.


## Known Issues:

* requires converting text to paths.
* mode is ignored - only does "center"
