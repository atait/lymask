from __future__ import division, print_function, absolute_import
from functools import wraps
from lygadgets import pya, isGUI, message, message_loud

from lymask.utilities import lys, LayerSet, gui_view
from lymask.library import dbu, as_region, fast_sized, fast_smoothed, set_threads, rdb_create, fast_width, fast_space, fast_separation, turbo, Euclidian


all_drcfunc_dict = {}
def drcStep(step_fun):
    ''' Each step must accept one argument that is cell, plus optionals, and not return

        steps are added to all_steps *in the order they are defined*
    '''
    all_drcfunc_dict[step_fun.__name__] = step_fun
    return step_fun


__warned_about_flattening = False
@drcStep
def flatten(cell, rdb):
    global __warned_about_flattening
    if isGUI() and not __warned_about_flattening:
        message_loud('Warning: The flattening step modifies the layout, so be careful about saving.')
        __warned_about_flattening = True
    cell.flatten(True)

@drcStep
def make_rdbcells(cell, rdb):
    rdb.topcell = cell.name
    rdb_cell = rdb.create_cell(cell.name)


@drcStep
def processor(cell, rdb, thread_count=1, tiles=2, remote_host=None):
    if remote_host is not None:
        message_loud('Automatic remote hosting is not yet supported')
    set_threads(thread_count, tiles=tiles)


@drcStep
def drcX(cell, rdb, on_input=[], on_output=[], none=None):
    ''' DRC exclude handling. It takes lists of layers. There are three kinds
            on_input: removes that layer in the DRC_exclude regions. This is fast but dangerous if you create a small hole in some polygon
                This modifies the layout as you see it, so don't save.
            on_output (default): does the full computations but does not output edges that fall within the DRC_exclude parts
            none: output everything regardless of DRC_exclude
    '''
    if none is not None:
        raise RuntimeError('none-type DRC exclude is not supported yet.')
    for layer in on_input:
        pre_exclude = as_region(cell, layer)
        post_exclude = pre_exclude - as_region(cell, 'DRC_exclude')
        cell.clear(lys[layer])
        cell.shapes(lys[layer]).insert(post_exclude)
    for layer in on_output:
        pass  # good job you picked the default


@drcStep
def width(cell, rdb, layer, value, angle=90):
    rdb_category = rdb.create_category('{}_Width'.format(layer))
    rdb_category.description = '{} [{:1.3f} um] - Minimum feature width violation'.format(layer, value)
    # message_loud('lymask doing {}'.format(rdb_category.name()))

    # do it
    polys = as_region(cell, layer)
    violations = fast_width(polys, value / dbu, angle)
    # violations = polys.width_check(value / dbu, False, Euclidian, angle, None, None)
    # violations = turbo(polys, 'width_check', [value / dbu, False, Euclidian, angle, None, None],
    #                    tile_border=1.1*value, job_name='{}_Width'.format(layer))
    rdb_create(rdb, cell, rdb_category, violations)


@drcStep
def space(cell, rdb, layer, value, angle=90):
    rdb_category = rdb.create_category('{}_Space'.format(layer))
    rdb_category.description = '{} [{:1.3f} um] - Minimum feature spacing violation'.format(layer, value)
    # message_loud('lymask doing {}'.format(rdb_category.name()))

    # do it
    polys = as_region(cell, layer)
    violations = fast_space(polys, value / dbu, angle)
    # violations = turbo(polys, 'space_check', [value / dbu, False, Euclidian, angle, None, None],
    #                    tile_border=1.1*value, job_name='{}_Space'.format(layer))
    rdb_create(rdb, cell, rdb_category, violations)


@drcStep
def inclusion(cell, rdb, inner, outer, include):
    rdb_category = rdb.create_category('{} in {}'.format(inner, outer))
    rdb_category.description = '{} in {} [{:1.3f} um] - Minimum inclusion violation'.format(inner, outer, include)

    # do it
    rin = as_region(cell, inner)
    rout = as_region(cell, outer)
    # violations = rin.sized(include / dbu) - rout
    big_rin = fast_sized(rin, include / dbu)
    # Note: this could be parallelized, but it is easier I think than sizing
    violations = big_rin - rout

    rdb_create(rdb, cell, rdb_category, violations)


@drcStep
def exclusion(cell, rdb, lay1, lay2, exclude):
    rdb_category = rdb.create_category('{} from {}'.format(lay1, lay2))
    rdb_category.description = '{} from {} [{:1.3f} um] - Minimum exclusion violation'.format(lay1, lay2, exclude)

    # do it
    r1 = as_region(cell, lay1)
    r2 = as_region(cell, lay2)
    # r1.separation_check(r2, exclude / dbu)
    too_close = fast_separation(r1, r2, exclude / dbu)
    # This could be parallelized
    overlaps = r1 & r2

    rdb_create(rdb, cell, rdb_category, overlaps)
    rdb_create(rdb, cell, rdb_category, too_close)


def assert_valid_drc_steps(step_list):
    ''' This runs before starting calculations to make sure there aren't typos
        that only show up after waiting for for all of the long steps
    '''
    # check function names
    for func_info in step_list:
        try:
            func = all_drcfunc_dict[func_info[0]]
        except KeyError as err:
            message_loud('Function "{}" not supported. Available are {}'.format(func_info[0], all_drcfunc_dict.keys()))
            raise
