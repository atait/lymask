from __future__ import division, print_function, absolute_import
from functools import wraps
from lygadgets import pya, isGUI, message, message_loud

from lymask.utilities import lys, LayerSet, insert_layer_tab, gui_view
from lymask.library import dbu, as_region, fast_sized, fast_smoothed, set_threads


all_func_dict = {}
def dpStep(step_fun):
    ''' Each step must accept one argument that is cell, plus optionals, and not return

        steps are added to all_steps *in the order they are defined*
    '''
    all_func_dict[step_fun.__name__] = step_fun
    return step_fun


@dpStep
def check_floorplan(cell, fp_safe=50):
    ''' Checks for floorplan. If you didn't make one, this makes one.
    '''
    if cell.shapes(lys.FLOORPLAN).is_empty():
        message('Warning: No floorplan found. Making one, but you should do this yourself')
        fp_box = cell.dbbox()  # this assumes that, if FLOORPLAN is present, that DRC has verified it forms the extent
        fp_box.enlarge(fp_safe, fp_safe)
        cell.shapes(lys.FLOORPLAN).insert(fp_box)


@dpStep
def flatten(cell):
    cell.flatten(True)


@dpStep
def erase_text_and_other_junk(cell):
    for layname in lys.keys():
        lay = lys[layname]
        for text in cell.shapes(lay).each(pya.Shapes.STexts):
            cell.shapes(lay).erase(text)
        # zero width paths


# Some peole use this, others have already converted
# @dpStep
# def convert_wgs(cell):
    # has_Si = pya.Region()
    # for si in ['wg_deep', 'wg_shallow']:
    #     has_Si.insert(cell.shapes(lys[si]))
    # ^ new version-ish

#     union(cell, 'wg_deep', 'wg_shallow')
#     layer_bool(cell, lys.wg_deep, lys.wg_shallow,
#                pya.EdgeProcessor.ModeBNotA, layC=lys.wg_shallow)
#     cell.clear(lys.wg_deep)
#     cell.move(lys.dp_temp, lys.wg_deep)


# @dpStep
# def nanowire_heal(cell):
#     delta = 0.01 / dbu
#     layer_resize(cell, lys.m2_nw, delta, layC=lys.dp_temp)
#     layer_resize(cell, lys.dp_temp, -delta, layC=lys.m2_nw)


@dpStep
def processor(cell, thread_count=1, remote_host=None):
    if remote_host is not None:
        message_loud('Automatic remote hosting is not yet supported')
    set_threads(thread_count)


@dpStep
def nanowire_sleeve(cell, Delta=2.5, delta=0.2, do_photo=True):
    Delta /= dbu
    delta /= dbu  # new naming convention?
    for dp_lay in ['m2_nw_photo', 'm2_nw_ebeam']:
        cell.clear(lys[dp_lay])
    nw_region = as_region(cell, 'm2_nw')
    nw_compressed = fast_smoothed(nw_region)
    ebeam_region = fast_sized(nw_compressed, Delta + delta) - nw_region
    cell.shapes(lys.m2_nw_ebeam).insert(ebeam_region)
    if do_photo:
        phoas_region = as_region(cell, 'FLOORPLAN') - fast_sized(nw_compressed, Delta - delta)
        cell.shapes(lys.m2_nw_photo).insert(phoas_region)


@dpStep
def waveguide_sleeve(cell, Delta_nw_si=2.0, Delta=2.0, delta=0.2, do_photo=True):
    ''' Does a bulk-sleeve for waveguide full, but first adds it under nanowires.
        Endcaps end where the explicit waveguide ends.
    '''
    Delta_nw_si /= dbu
    Delta /= dbu
    delta /= dbu
    for dp_lay in ['wg_full_photo', 'wg_full_ebeam']:
        cell.clear(lys[dp_lay])

    # add silicon under the nanowires
    nw_compressed = fast_smoothed(as_region(cell, 'm2_nw'))
    wg_explicit = as_region(cell, 'wg_deep')
    nw_except_on_wg = nw_compressed - fast_sized(wg_explicit, Delta_nw_si)
    wg_all = fast_sized(nw_except_on_wg, Delta_nw_si) + wg_explicit

    # do the bulk-sleeve
    # wg_compressed = filter_large_polygons(wg_all)
    wg_compressed = fast_smoothed(wg_all)
    ebeam_region = fast_sized(wg_compressed, Delta + delta) - wg_all
    cell.shapes(lys.wg_full_ebeam).insert(ebeam_region)
    if do_photo:
        phoas_region = as_region(cell, 'FLOORPLAN') - fast_sized(wg_compressed, Delta - delta)
        try:
            phoas_region -= as_region(cell, 'wg_deep_photo')
        except KeyError: pass
        cell.shapes(lys.wg_full_photo).insert(phoas_region)


@dpStep
def ground_plane(cell, Delta_gp=15.0, points_per_circle=100):
    Delta_gp /= dbu
    cell.clear(lys.gp_photo)
    # Accumulate everything that we don't want to cover in metal
    gp_exclusion_things = pya.Region()
    for layname in ['wg_deep', 'wg_shallow', 'm1_nwpad',
                    'm4_ledpad', 'm3_res', 'm5_wiring', 'm2_nw',
                    'GP_KO']:
        try:
            gp_exclusion_things += fast_smoothed(as_region(cell, layname))
        except KeyError: pass
    # Where ground plane is explicitly connected to wires, cut it out of the exclusion region
    gnd_explicit = as_region(cell, 'm5_gnd')
    gp_exclusion_tight = gp_exclusion_things - fast_sized(gnd_explicit, Delta_gp)
    # Inflate the buffer around excluded things and pour
    gp_exclusion_zone = fast_sized(gp_exclusion_tight, Delta_gp)
    gp_region = as_region(cell, 'FLOORPLAN') - gp_exclusion_zone

    # Connect to pads
    gp_region.merge()
    gp_region.round_corners(Delta_gp / 5, Delta_gp / 3, points_per_circle)
    gp_region += as_region(cell, 'm5_gnd')
    gp_region.merge()
    cell.shapes(lys.gp_photo).insert(gp_region)


has_precomped = dict()
@dpStep
def precomp(cell, **kwargs):
    '''
        Arguments are keyed by layer name with the value of bias in microns, so for example

            precomp(TOP, wg_deep=0.05, nw_pad=-0.6)

        The behavior is to overwrite the layer.
        Problem if it runs twice is that it expands too much, so it stores which layers have been biased.
        Currently, it doesn't act on this, assuming that if you have run twice that you hit Undo in between.
    '''
    global has_precomped
    for layer_name, bias_um in kwargs.items():
        # do a check for repeated precomp
        if cell in has_precomped.keys():
            if layer_name in has_precomped[cell]:
                pya.MessageBox.info('Dataprep precomp', 'Warning: precompensating {} twice. '.format(layer_name) + '(in this process)\n'
                                    'If the last precomp was not undone with Ctrl-Z, this will turn out wrong', pya.MessageBox.Ok)
                pass#raise RuntimeError('At this time, precomp cannot be run twice on the same layer.')
            else:
                has_precomped[cell].add(layer_name)
        else:
            has_precomped[cell] = set([layer_name])

        # size the layer in place
        bias = bias_um / dbu
        layer_region = as_region(cell, layer_name)
        layer_region.size(bias)
        cell.clear(lys[layer_name])
        cell.shapes(lys[layer_name]).insert(layer_region)


@dpStep
def mask_map(cell, clear_others=False, **kwargs):
    ''' lyp_file is relative to the yml file. If it is None, the same layer properties will be used.
        kwarg keys are destination layers and values are source layers, which can include "+"
    '''
    mask_layer_index = 101
    # merging and moving to new layers
    for dest_layer, src_expression in kwargs.items():
        new_layinfo = pya.LayerInfo(mask_layer_index, 0, dest_layer)
        lys[dest_layer] = new_layinfo
        cell.layout().layer(new_layinfo)
        components = src_expression.split('+')
        for comp in components:
            cell.copy(lys[comp.strip()], lys[dest_layer])
        mask_layer_index += 1
    if isGUI():
        try:
            lv = gui_view()
            add_tab = True
        except UserWarning:
            # No view is selected. We might be in batch mode
            add_tab = False
        if add_tab:
            if lv.is_transacting():
                lv.commit()
                lv.transaction('Adding mask layers')
            insert_layer_tab(tab_name='Masks')
            for dest_layer in kwargs.keys():
                lay_prop = pya.LayerProperties()
                lay_prop.source_name = lys.get_as_LayerInfo(dest_layer).name
                lay_prop.source_layer = lys.get_as_LayerInfo(dest_layer).layer
                lay_prop.source_datatype = lys.get_as_LayerInfo(dest_layer).datatype
                lv.init_layer_properties(lay_prop)
                lv.insert_layer(lv.end_layers(), lay_prop)
    if clear_others:
        for any_layer in lys.keys():
            if any_layer not in kwargs.keys():
                cell.clear(lys[any_layer])


@dpStep
def align_corners(cell):
    ''' Puts little boxes in the corners so lithography tools all see the same
        Goes through all the layers present in the layout (does not depend on currently loaded layer properties)
    '''
    ly = cell.layout()
    all_layers = ly.layer_infos()

    # get the actual floorplan this time
    if cell.shapes(lys.FLOORPLAN).size() != 1:
        raise RuntimeError('align_corners needs a FLOORPLAN to work consisting of exactly one polygon')
    for fp in cell.shapes(lys.FLOORPLAN).each():
        fp_box = fp.dbbox()

    corner_mark = pya.DBox(0, 0, 1, 1)
    for marked_layer in all_layers:
        if marked_layer.name in ['FLOORPLAN']:  # put exceptions here
            continue
        # do some boolean here to shave off overhangs
        layer_region = as_region(cell, marked_layer)
        layer_region = layer_region & as_region(cell, 'FLOORPLAN')
        cell.clear(lys[marked_layer])
        cell.shapes(lys[marked_layer]).insert(layer_region)

        # put in the markers
        for north_south in (fp_box.top - 1, fp_box.bottom):
            for east_west in (fp_box.right - 1, fp_box.left):
                mark = corner_mark.moved(east_west, north_south)
                if not cell.shapes(ly.layer(marked_layer)).is_empty():
                    cell.shapes(ly.layer(marked_layer)).insert(mark)
