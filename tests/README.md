# What these tests show

## DRC
- width, of course.
- spacing. parallel and angled. Angles above 40 degrees are ok. One of them throws, one of them has DRC exclude on it
- exclusion between wg_deep and m5_wiring
- DRC exclude.
    - On output: see above, that shallow spacing is quieted.
    - On input: Top left, one of the v3's is deleted and does not thow an inclusion error. The other one has a hole cut out of the center and then thows false width/space errors. This illustrates the danger of DRC_exclude on_input
- inclusions of v3 in wg_deep: one of them is too close to the edge (giving edge pair). One of them is totally outside (giving polygon)

## Dataprep
- precomps
- sleeves
- ground plane
- mapping to masks