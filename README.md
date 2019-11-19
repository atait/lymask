[![Build Status](https://travis-ci.org/atait/lytest.svg?branch=master)](https://travis-ci.org/atait/lytest)

# lymask

Mask dataprep and DRC with python and klayout.

Procedures are interpreted from YAML files which means they
- are easy to understand and edit
- can be modified without restarting klayout
- are declaritive, so their parameters can be accessed by other programs

Multiple entry points
- GUI menu: used for basic development and debug
- Command line: used for batch processing, particularly on remote computers
- API functions: used for automation within a larger program

## Installation
```
pip install lymask
lygadgets_link lymask
```

## Commands
See the tests for usage examples.

_Dataprep_
- check_floorplan
- flatten
- erase_text_and_other_junk
- convert_wgs
- nanowire_heal
- processor
- nanowire_sleeve
- waveguide_sleeve
- ground_plane
- metal_pedestal
- precomp
- mask_map
- smooth_floating
- clear_nonmask
- align_corners

_DRC_
- make_rdbcells
- processor
- drcX
- width
- space
- inclusion
- exclusion


## Configure your technology
KLayout-style technologies are directories that include a `.lyt` file and usually a layer properties `.lyp` file. `lymask` looks for available scripts in specific locations within "dataprep" and "drc" subdirectories. The structure should look like this
```
My_Tech
| - My_Tech.lyt
| - klayout_layers_My_Tech.lyp
| - dataprep
| | - my_dataprep_procedure.yml
| | - klayout_layers_dataprep.lyp
| - drc
| | - my_drc_procedure.yml
```
`klayout_layers_dataprep.lyp` can have multiple groups. See the tests for an example. In the GUI, `lymask` translates these groups into layer tabs for ease of viewing. This is done with "Reload Dataprep (Ctrl-L)" in the `lymask` menu.


## Multithreading
Data from doing a DRC space_check Vs number of tiles. A 6 mm x 7.75 mm die. 500nm space check on a fairly full layer (metal with ground plane). Tile border is 1000nm.  Machine was a 4-core laptop. Thread count = 4.

Tile border = 1000 nm
- 1: 108 sec
- 2x2: 41 sec
- 3x3: 94 sec
- 4x4: 82 sec
- 10x10: 215 sec

Tile border = 550 nm
- 2x2: 35 sec (repeated twice, same value)
- 3x3: 37 sec
- 4x4: 57 sec
- 8x8: 59 sec
- 1x4: 56 sec
- 1x16: 62 sec

With angle 40 (gives no violations. other one gave 140 violations)
- 2x2: 17 sec (repeated thrice)
- 2x2 with violation: 26 sec (error was appropriately caught)
- 3x3: 18 sec

No tile border
- 2x2: 28 sec
- 3x3: 16 sec
- 3x3, 12 threads: 15 sec
- 8x8: 14 sec
- 16x16: 16 sec


## Running tests
To test command line and API, run `pytest tests`. You can also go in the GUI and do it there, but that has to be manual


## DRC todo
XX - batch launching
XX - output to lyrdb files
XX - command line reorganization
XX - tests: generate the files and compare as xmldicts
XX - angle limits
- tiling
XX - drc exclude
- falling back on designer layers?
XX - inclusion, exclusion
- self overlap
- minimum area
- edge lengths
- run other files
XX - define your own in your dataprep directory
