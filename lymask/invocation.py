from __future__ import division, print_function, absolute_import
from lygadgets import pya, message
import os
from lymask.siepic_utils import get_layout_variables_no_tech, active_technology, tech_dataprep_layer_properties
from lymask.soen_utils import lys, insert_layer_tab
from functools import wraps


### Helpers ###

try:
    dbu = active_technology().dbu
except AttributeError:
    dbu = .001


def as_region(cell, layname):
    ''' Just a convenience brevity function '''
    return pya.Region(cell.shapes(lys[layname]))


def filter_large_polygons(unfiltered_region, threshold_points=20):
    '''
        For each polygon, if it has too many points, its bbox will be returned instead.
        This is used to accelerate later sizing operations.
    '''
    filtered = pya.Region()
    # unfiltered_region.merged_semantics = False
    # unfiltered_region.smooth(.05 / dbu)
    for ss in unfiltered_region.each():
        if ss.num_points() > threshold_points:
            filtered.insert(ss.bbox())
        else:
            filtered.insert(ss)
    return filtered


all_func_dict = {}
def dpStep(step_fun):
    ''' Each step must accept one argument that is cell, plus optionals, and not return

        steps are added to all_steps *in the order they are defined*
    '''
    all_func_dict[step_fun.__name__] = step_fun
    return step_fun


### Entry points ###
import yaml
def _main(layout, ymlfile):
    with open(ymlfile) as fx:
        step_list = yaml.load(fx)
    for func_info in step_list:
        func = all_func_dict[func_info[0]]
        try:
            kwargs = func_info[1]
        except IndexError:
            kwargs = dict()
        for TOP_ind in layout.each_top_cell():
            # call it
            func(layout.cell(TOP_ind), **kwargs)
    return layout


def gui_main(ymlfile=None):
    lv, layout, _ = get_layout_variables_no_tech()
    lys.active_layout = layout

    insert_layer_tab(tech_dataprep_layer_properties(), tab_name='Dataprep')

    lv.transaction('Mask Dataprep')
    try:
        processed = _main(layout, ymlfile=ymlfile)
    finally:
        lv.commit()


def batch_main(infile, ymlfile=None, outfile=None):
    if outfile is None:
        outfile = infile[:-4] + '_proc.gds'
    # Load it
    layout = pya.Layout()
    layout.read(infile)
    lys.active_layout = layout
    # Find the yml file
    if ymlfile is None:
        # default dataprep test
        ymlfile = active_technology().eff_path('dataprep/test.yml')
    elif os.path.exists(os.path.realpath(ymlfile)):
        pass
    else:
        # find path to tech
        ymlfile = active_technology().eff_path(os.path.join('dataprep', ymlfile))
    # Process it
    lys.appendFile(tech_dataprep_layer_properties())
    processed = _main(layout, ymlfile=ymlfile)
    # Write it
    processed.write(outfile)
