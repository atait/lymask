from __future__ import division, print_function, absolute_import
from functools import wraps
import os
import importlib.util

from lygadgets import pya, isGUI, message, message_loud
from lygadgets import anyCell_to_anyCell

from lymask.utilities import lys, LayerSet, gui_view, active_technology, func_info_to_func_and_kwargs
from lymask.library import dbu, as_region, fast_sized, fast_smoothed, set_threads


all_dpfunc_dict = {}
def dpStep(step_fun):
    ''' Each step must accept one argument that is cell, plus optionals, and not return

        steps are added to all_steps *in the order they are defined*
    '''
    all_dpfunc_dict[step_fun.__name__] = step_fun
    return step_fun


def dpStep_phidl(step_fun):
    ''' phidl version, where the mutable object is a phidl.Device not a pya.Cell
        Each step must accept one argument that is Device, plus optionals, and not return
    '''
    try:
        from phidl import Device
    except ImportError as err:
        raise ImportError('You are probably trying to use phidl dataprep steps within a GUI. This is only supported in batch mode. Not my fault')
    @wraps(step_fun)
    def wrapper(cell, *args, **kwargs):
        phidl_device = Device()
        anyCell_to_anyCell(cell, phidl_device)
        step_fun(phidl_device, *args, **kwargs)
        anyCell_to_anyCell(phidl_device, cell)
    all_dpfunc_dict[step_fun.__name__] = wrapper
    return wrapper

# @dpStep_phidl
# def phidl_example(device):
#     import phidl.geometry as pg
#     device << pg.rectangle((10, 10))


@dpStep
def add_library(cell, filename):
    ''' Imports from the filename, which is a path to a python file.
        Anything within there that is a dpStep gets added to the all_dpfunc_dict for later
    '''
    if os.path.isfile(filename):
        pass
    else:
        dataprep_relpath = os.path.join(active_technology().eff_path('dataprep'), filename)
        if os.path.isfile(dataprep_relpath):
            filename = os.path.realpath(dataprep_relpath)
        else:
            raise FileNotFoundError('lymask could not find {}'.format(filename))
    modulename = os.path.splitext(os.path.basename(filename))[0]
    spec = importlib.util.spec_from_file_location(modulename, filename)
    foo = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(foo)
    except ImportError as err:
        if 'gdspy' in err.args[0]:
            raise ImportError('You are probably trying to use phidl/gdspy dataprep steps within a GUI. This is only supported in batch mode currently')
        else:
            raise


@dpStep
def check_floorplan(cell, fp_safe=50):
    ''' Checks for floorplan. If you didn't make one, this makes one.
    '''
    if cell.shapes(lys.FLOORPLAN).is_empty():
        message('Warning: No floorplan found. Making one, but you should do this yourself')
        fp_box = cell.dbbox()  # this assumes that, if FLOORPLAN is present, that DRC has verified it forms the extent
        fp_box.enlarge(fp_safe, fp_safe)
        cell.shapes(lys.FLOORPLAN).insert(fp_box)


__warned_about_flattening = False
@dpStep
def flatten(cell):
    global __warned_about_flattening
    if isGUI() and not __warned_about_flattening:
        message_loud('Warning: The flattening step modifies the layout, so be careful about saving.')
        __warned_about_flattening = True
    cell.flatten(True)


@dpStep
def paths_to_polys(cell):
    for layname in lys.keys():
        lay = lys[layname]
        for shape in cell.each_shape(lay):
            if shape.is_path():
                shape.polygon = shape.simple_polygon


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
def processor(cell, thread_count=1, tiles=2, remote_host=None):
    if remote_host is not None:
        message_loud('Automatic remote hosting is not yet supported')
    set_threads(thread_count, tiles)


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
        Recognizes the wg_deep_photo layer as a photolith-only layer (lower resolution, faster EBeam write)
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
def ground_plane(cell, Delta_gp=15.0, points_per_circle=100, air_open=None):
    Delta_gp /= dbu
    cell.clear(lys.gp_photo)
    # Accumulate everything that we don't want to cover in metal
    gp_exclusion_things = pya.Region()
    for layname in ['wg_deep', 'wg_deep_photo', 'wg_shallow', 'm1_nwpad',
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

    # Connect to ground pads
    gp_region.merge()
    gp_region = fast_sized(gp_region, 1 / dbu)  # kill narrow spaces
    gp_region = fast_sized(gp_region, -2 / dbu)  # kill narrow widths
    gp_region = fast_sized(gp_region, 1 / dbu)
    gp_region += as_region(cell, 'm5_gnd')
    gp_region.round_corners(Delta_gp / 5, Delta_gp / 3, points_per_circle)
    gp_region = gp_region.smoothed(.001)  # avoid some bug in pya
    gp_region.merge()
    cell.shapes(lys.gp_photo).insert(gp_region)

    # Open up to the air
    if air_open is not None:
        Delta_air = 5
        fp_safe = as_region(cell, 'FLOORPLAN')
        air_rects = fp_safe - fp_safe.sized(0, -air_open / dbu, 0)
        air_region = air_rects & gp_region
        air_region = fast_sized(air_region, -Delta_air / dbu)
        air_region = fast_sized(air_region, 4 / dbu)  # kill narrow spaces
        air_region = fast_sized(air_region, -8 / dbu)  # kill narrow widths
        air_region = fast_sized(air_region, 4 / dbu)
        air_region.round_corners(Delta_gp / 5, Delta_gp / 3, points_per_circle)
        cell.shapes(lys.gp_v5).insert(air_region)


@dpStep
def metal_pedestal(cell, pedestal_layer='wg_full_photo', offset=0, keepout=None):
    metal_region = pya.Region()
    for layname in ['m5_wiring', 'm5_gnd', 'gp_photo']:
        try:
            metal_region += as_region(cell, layname)
        except: pass
    valid_metal = metal_region - fast_sized(as_region(cell, lys.wg_deep), offset / dbu)
    pedestal_region = fast_sized(valid_metal, offset / dbu)
    if keepout is not None:
        if not isinstance(keepout, (list, tuple)):
            keepout = [keepout]
        for ko_layer in keepout:
            pedestal_region -= as_region(cell, ko_layer)
    cell.shapes(lys[pedestal_layer]).insert(pedestal_region)


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
def mask_map(cell, **kwargs):
    ''' lyp_file is relative to the yml file. If it is None, the same layer properties will be used.
        kwarg keys are destination layers and values are source layers, which can be a list

        There is a problem if you have 101 defined in your file and then another layer that is not defined.
    '''
    assert_valid_mask_map(kwargs)
    # If we need to make new layers,
    new_mask_index = 0
    available_mask_layers = list(range(100, 200))
    for occupied_layer in lys.values():
        if occupied_layer.layer in available_mask_layers:
            available_mask_layers.remove(occupied_layer.layer)
    # merging and moving to new layers
    for dest_layer, src_layers in kwargs.items():
        if not dest_layer in lys.keys():
            new_layinfo = pya.LayerInfo(available_mask_layers[new_mask_index], 0, dest_layer)
            lys[dest_layer] = new_layinfo
            cell.layout().layer(new_layinfo)

        if not isinstance(src_layers, list):
            src_layers = [src_layers]
        for src in src_layers:
            cell.copy(lys[src], lys[dest_layer])
        new_mask_index += 1


def assert_valid_mask_map(mapping):
    for dest_layer, src_layers in mapping.items():
        try:
            lys[dest_layer]
        except KeyError as err:
            message_loud('Warning: Destination layer [{}] not found in mask layerset. We will make it...'.format(dest_layer))
            pass  # This is allowed

        if not isinstance(src_layers, list):
            src_layers = [src_layers]
        for src in src_layers:
            try:
                lys[src]
            except KeyError as err:
                message_loud('Error: Source layer [{}] not found in existing designer or dataprep layerset.'.format(src))
                raise


@dpStep
def invert_tone(cell, layer):
    inverted = as_region(cell, 'FLOORPLAN') - as_region(cell, layer)
    cell.clear(lys[layer])
    cell.shapes(lys[layer]).insert(inverted)


@dpStep
def smooth_floating(cell, deviation=0.005):
    ''' Removes teeny tiny edges that sometimes show up in curved edges with angles 0 or 90 plus tiny epsilon
    '''
    for layer_name in lys.keys():
        layer_region = as_region(cell, layer_name)
        layer_region = fast_smoothed(layer_region, deviation)
        cell.clear(lys[layer_name])
        cell.shapes(lys[layer_name]).insert(layer_region)


@dpStep
def clear_nonmask(cell):
    ''' Gets rid of everything except 101--199. That is what we have decided are mask layers.
        Same as clear_others in mask_map
    '''
    for any_layer in lys.keys():
        lay = lys[any_layer]
        is_mask = (100 <= lay and lay < 200) or any_layer == 'FLOORPLAN'
        if not is_mask:
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
        if cell.shapes(ly.layer(marked_layer)).is_empty():
            continue
        # do some boolean here to shave off overhangs
        # layer_region = as_region(cell, marked_layer)
        # layer_region = layer_region & as_region(cell, 'FLOORPLAN')
        # cell.clear(lys[marked_layer])
        # cell.shapes(lys[marked_layer]).insert(layer_region)

        # put in the markers
        for north_south in (fp_box.top - 1, fp_box.bottom):
            for east_west in (fp_box.right - 1, fp_box.left):
                mark = corner_mark.moved(east_west, north_south)
                if marked_layer.name == 'DRC_exclude' or marked_layer.layer == 91:
                    mark = mark.enlarged(1, 1)
                cell.shapes(ly.layer(marked_layer)).insert(mark)


def assert_valid_dataprep_steps(step_list):
    ''' This runs before starting calculations to make sure there aren't typos
        that only show up after waiting for for all of the long steps
    '''
    if any(func_info_to_func_and_kwargs(func_info)[0] == 'add_library' for func_info in step_list):
        return

    # check function names
    for func_info in step_list:
        try:
            func = all_dpfunc_dict[func_info_to_func_and_kwargs(func_info)[0]]
        except KeyError as err:
            message_loud('Function "{}" not supported. Available are {}'.format(func_info[0], all_dpfunc_dict.keys()))
            raise

        # check mask layers
        if func is mask_map:
            assert_valid_mask_map(func_info_to_func_and_kwargs(func_info)[1])
