from __future__ import division, print_function, absolute_import
from functools import wraps
from lygadgets import pya, isGUI, message, message_loud

from lymask.utilities import lys, LayerSet, gui_view
from lymask.library import dbu, as_region, fast_sized, fast_smoothed, set_threads


all_drcfunc_dict = {}
def drcStep(step_fun):
    ''' Each step must accept one argument that is cell, plus optionals, and not return

        steps are added to all_steps *in the order they are defined*
    '''
    all_drcfunc_dict[step_fun.__name__] = step_fun
    return step_fun


@drcStep
def processor(cell, rdb, thread_count=1, remote_host=None):
    if remote_host is not None:
        message_loud('Automatic remote hosting is not yet supported')
    set_threads(thread_count)


@drcStep
def make_rdbcells(cell, rdb):
    rdb.topcell = cell.name
    rdb_cell = rdb.create_cell(cell.name)


@drcStep
def width(cell, rdb, **kwargs):
    rdb_cell = rdb.cell_by_qname(cell.name)
    for layname, wid in kwargs.items():
        rdb_category = rdb.create_category('{}_Width'.format(layname))
        rdb_category.description = '{} [{:1.3f} um] - Minimum feature width violation'.format(layname, wid)

        # do it
        polys = as_region(cell, layname)
        violations = polys.width_check(wid / dbu)

        trans_to_um = pya.CplxTrans(dbu)
        rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, violations)


@drcStep
def space(cell, rdb, **kwargs):
    rdb_cell = rdb.cell_by_qname(cell.name)
    for layname, wid in kwargs.items():
        rdb_category = rdb.create_category('{}_Space'.format(layname))
        rdb_category.description = '{} [{:1.3f} um] - Minimum feature spacing violation'.format(layname, wid)

        # do it
        polys = as_region(cell, layname)
        violations = polys.space_check(wid / dbu)

        trans_to_um = pya.CplxTrans(dbu)
        rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, violations)


@drcStep
def inclusion(cell, rdb, inner, outer, include):
    rdb_cell = rdb.cell_by_qname(cell.name)
    rdb_category = rdb.create_category('{} in {}'.format(inner, outer))
    rdb_category.description = '{} in {} [{:1.3f} um] - Minimum inclusion violation'.format(inner, outer, include)

    # do it
    rin = as_region(cell, inner)
    rout = as_region(cell, outer)
    outside = rin - rout
    too_close = rout.enclosing_check(rin, include / dbu)

    # in_region_expanded = fast_sized(as_region(cell, inner), include)
    # out_region = as_region(cell, outer)
    # violations = in_region_expanded - out_region

    trans_to_um = pya.CplxTrans(dbu)
    rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, outside)
    rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, too_close)


@drcStep
def exclusion(cell, rdb, lay1, lay2, exclude):
    rdb_cell = rdb.cell_by_qname(cell.name)
    rdb_category = rdb.create_category('{} from {}'.format(lay1, lay2))
    rdb_category.description = '{} from {} [{:1.3f} um] - Minimum exclusion violation'.format(lay1, lay2, exclude)

    # do it
    r1 = as_region(cell, lay1)
    r2 = as_region(cell, lay2)
    overlaps = r1 & r2
    too_close = r1.separation_check(r2, exclude / dbu)

    trans_to_um = pya.CplxTrans(dbu)
    rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, overlaps)
    rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, too_close)


def assert_valid_drc_steps(step_list):
    ''' This runs before starting calculations to make sure there aren't typos
        that only show up after waiting for for all of the long steps
    '''
    # check function names
    for func_info in step_list:
        try:
            func = all_drcfunc_dict[func_info[0]]
        except KeyError as err:
            message_loud('Function not supported. Available are {}'.format(all_drcfunc_dict.keys()))
            raise
