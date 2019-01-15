from __future__ import division, print_function, absolute_import
import os
import yaml
from functools import wraps

from lygadgets import pya, message, Technology
from lymask.soen_utils import gui_view, gui_active_layout, active_technology, set_active_technology, tech_dataprep_layer_properties
from lymask.soen_utils import lys, insert_layer_tab


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

def _main(layout, ymlfile, technology=None):
    # todo: figure out which technology we will be using and its layer properties
    # todo: reload lys using technology
    with open(ymlfile) as fx:
        step_list = yaml.load(fx)
    insert_layer_tab(tech_dataprep_layer_properties(technology), tab_name='Dataprep')
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
    layout = gui_active_layout()
    lys.active_layout = layout

    gui_view().transaction('Mask Dataprep')
    try:
        processed = _main(layout, ymlfile=ymlfile, technology=None)  # todo: get the technology from the selection menu
    finally:
        gui_view().commit()


def batch_main(infile, ymlspec=None, technology=None, outfile=None):
    if outfile is None:
        outfile = infile[:-4] + '_proc.gds'
    # Load it
    layout = pya.Layout()
    layout.read(infile)
    lys.active_layout = layout
    # Find the yml file
    if ymlspec is not None and os.path.exists(os.path.realpath(ymlspec)):
        ymlfile = ymlspec
        if technology is None:
            tech_obj = active_technology()
            message('Using the last used technology: {}'.format(tech_obj.name))
    else:
        if technology is None:
            raise ValueError('When specifying a relative dataprep file, you must also provide a technology.')

        tech_obj = Technology.technology_by_name(technology)
        set_active_technology(technology)
        if ymlspec is None:
            # default dataprep test
            ymlfile = tech_obj.eff_path('dataprep/test.yml')
        else:
            # find path to tech
            if not ymlspec.endswith('.yml'):
                ymlspec += '.yml'
            ymlfile = tech_obj.eff_path(os.path.join('dataprep', ymlspec))
    # Process it
    # lys.appendFile(tech_dataprep_layer_properties(tech_obj))
    processed = _main(layout, ymlfile=ymlfile, technology=technology)
    # Write it
    processed.write(outfile)
