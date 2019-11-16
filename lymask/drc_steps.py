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
    for layname, wid in kwargs.items():
        rdb_category = rdb.create_category('{}_Width'.format(layname))
        rdb_category.description = '{} [{:1.3f} um] - Minimum feature width violation'.format(layname, wid)

        # do it
        wid /= dbu
        polys = as_region(cell, layname)
        edge_pairs = polys.width_check(wid)

        rdb_cell = rdb.cell_by_qname(cell.name)
        trans_to_um = pya.CplxTrans(dbu)
        rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, edge_pairs)


@drcStep
def space(cell, rdb, **kwargs):
    for layname, wid in kwargs.items():
        rdb_category = rdb.create_category('{}_Space'.format(layname))
        rdb_category.description = '{} [{:1.3f} um] - Minimum feature spacing violation'.format(layname, wid)

        # do it
        wid /= dbu
        polys = as_region(cell, layname)
        edge_pairs = polys.space_check(wid)

        rdb_cell = rdb.cell_by_qname(cell.name)
        trans_to_um = pya.CplxTrans(dbu)
        rdb.create_items(rdb_cell.rdb_id(), rdb_category.rdb_id(), trans_to_um, edge_pairs)


def assert_valid_step_list(step_list):
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
