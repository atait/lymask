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


def _normal_smoothed(unfiltered_region, deviation=0.1):
    smoothed_region = unfiltered_region.dup()
    smoothed_region.merged_semantics = False
    smoothed_region.smooth(deviation / dbu)
    return smoothed_region


def fast_smoothed(unfiltered_region, deviation=0.1):
    ''' Removes any points that would change the shape by less than this deviation.
        This is used to significantly decrease the number of points prior to sizing

        Note: multicore does not work well with this, but it turns out to be pretty fast
    '''
    # if something goes wrong, you can fall back to regular here by uncommenting
    return _normal_smoothed(unfiltered_region, deviation)

    temp_region = unfiltered_region.dup()
    temp_region.merged_semantics = False

    output_region = pya.Region()
    tp = pya.TilingProcessor()
    tp.input('in1', temp_region)
    tp.output('out1', output_region)
    tp.queue("_output(out1, in1.smoothed({}))".format(deviation / dbu))
    tp.tile_size(2000., 2000.)
    tp.tile_border(5 * deviation, 5 * deviation)
    tp.threads = _thread_count
    tp.execute('Smoothing job')
    return output_region


_thread_count = None
def set_threads(thread_count):
    ''' Set to None to disable parallel processing '''
    global _thread_count
    if thread_count == 1:
        thread_count = None
    _thread_count = thread_count


def fast_sized(input_region, xsize):
    # if something goes wrong, you can fall back to regular here by uncommenting
    if _thread_count is None:
        return input_region.sized(xsize)
    else:
        output_region = pya.Region()
        tp = pya.TilingProcessor()
        tp.input('in1', input_region)
        tp.output('out1', output_region)
        tp.queue("_output(out1, in1.sized({}))".format(xsize))
        tp.tile_size(2000., 2000.)
        tp.tile_border(2 * xsize, 2 * xsize)
        tp.threads = _thread_count
        tp.execute('Sizing job')
        return output_region


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
