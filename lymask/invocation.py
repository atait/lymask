'''
    Entry points from GUI, command line, and API
'''
from __future__ import division, print_function, absolute_import
import os
import yaml
import argparse
from lygadgets import pya, message, Technology

from lymask import __version__
from lymask.utilities import gui_view, gui_active_layout, gui_window, \
                             active_technology, set_active_technology, \
                             tech_layer_properties, \
                             lys, reload_lys
from lymask.dataprep_steps import all_dpfunc_dict, assert_valid_step_list
from lymask.drc_steps import all_drcfunc_dict


parser = argparse.ArgumentParser(description="Command line mask dataprep")
parser.add_argument('infile', type=argparse.FileType('rb'),
                    help='the input gds file')
parser.add_argument('ymlspec', nargs='?', default=None,
                    help='YML file that describes the dataprep steps and parameters. Can be relative to technology')
parser.add_argument('-o', '--outfile', nargs='?', default=None,
                    help='The output file. Default is to tack "_proc" onto the end')
parser.add_argument('-t', '--technology', nargs='?', default=None,
                    help='The name of technology to use. Must be visible in installed technologies')
parser.add_argument('-v', '--version', action='version', version=f'%(prog)s v{__version__}')

def cm_main():
    ''' This one uses the klayout standalone '''
    args = parser.parse_args()
    batch_main(args.infile.name, ymlspec=args.ymlspec, outfile=args.outfile, technology=args.technology)


def _main(layout, ymlfile, tech_obj=None):
    # todo: figure out which technology we will be using and its layer properties
    with open(ymlfile) as fx:
        step_list = yaml.load(fx)
    reload_lys(tech_obj, dataprep=True)
    assert_valid_step_list(step_list)
    for func_info in step_list:
        message('lymask doing {}'.format(func_info[0]))
        func = all_dpfunc_dict[func_info[0]]
        try:
            kwargs = func_info[1]
        except IndexError:
            kwargs = dict()
        for TOP_ind in layout.each_top_cell():
            # call it
            func(layout.cell(TOP_ind), **kwargs)
    return layout


def _drc_main(layout, ymlfile, tech_obj=None):
    with open(ymlfile) as fx:
        step_list = yaml.load(fx)
    reload_lys(tech_obj, dataprep=True)

    rdb = pya.ReportDatabase('DRC: {}'.format(os.path.basename(ymlfile)))
    rdb.description = 'DRC: {}'.format(os.path.basename(ymlfile))

    for func_info in step_list:
        message('lymask doing {}'.format(func_info[0]))
        func = all_drcfunc_dict[func_info[0]]
        try:
            kwargs = func_info[1]
        except IndexError:
            kwargs = dict()
        for TOP_ind in layout.each_top_cell():
            # call it
            func(layout.cell(TOP_ind), rdb, **kwargs)
    return rdb


def gui_main(ymlfile=None):
    layout = gui_active_layout()
    lys.active_layout = layout
    technology = gui_view().active_cellview().technology  # gets the technology from the selection menu
    tech_obj = Technology.technology_by_name(technology)

    gui_view().transaction('Mask Dataprep')
    try:
        processed = _main(layout, ymlfile=ymlfile, tech_obj=tech_obj)
    finally:
        gui_view().commit()


def gui_drc_main(ymlfile=None):
    layout = gui_active_layout()
    lys.active_layout = layout
    technology = gui_view().active_cellview().technology  # gets the technology from the selection menu
    tech_obj = Technology.technology_by_name(technology)

    lv = gui_view()
    lv.transaction('lymask DRC')
    try:
        rdb = _drc_main(layout, ymlfile=ymlfile, tech_obj=tech_obj)
    finally:
        lv.commit()
    rdix = lv.add_rdb(rdb)
    lv.show_rdb(rdix, lv.active_cellview().index())
    # Bring the marker browser window to the front
    gui_window().menu().action('tools_menu.browse_markers').trigger()


def batch_main(infile, ymlspec=None, technology=None, outfile=None):
    # covers everything that is not GUI
    if outfile is None:
        outfile = infile[:-4] + '_proc.gds'
    # Load it
    layout = pya.Layout()
    layout.read(infile)
    lys.active_layout = layout
    ymlfile = resolve_ymlspec(ymlspec, technology, category='dataprep')  # this also sets the technology
    tech_obj = active_technology()
    # Process it
    processed = _main(layout, ymlfile=ymlfile, tech_obj=tech_obj)
    # Write it
    processed.write(outfile)


def batch_drc_main(infile, ymlspec=None, technology=None, outfile=None):
    # covers everything that is not GUI
    if outfile is None:
        outfile = infile[:-4] + '.lyrdb'
    # Load it
    layout = pya.Layout()
    layout.read(infile)
    lys.active_layout = layout
    ymlfile = resolve_ymlspec(ymlspec, technology, category='drc')  # this also sets the technology
    tech_obj = active_technology()
    # Process it
    rdb = _drc_main(layout, ymlfile=ymlfile, tech_obj=tech_obj)
    # Write it
    rdb.save(outfile)
    # Brief report
    print('DRC violations:', rdb.num_items())
    print('Full report:', outfile)


def resolve_ymlspec(ymlspec=None, technology=None, category='dataprep'):
    ''' Find the yml file that describes the process. There are several options for inputs
        # Option 1: file path is specified directly
        # Option 2: search within a specified technology
    '''
    if ymlspec is not None and os.path.exists(os.path.realpath(ymlspec)):
        # Option 1: file path is specified directly
        ymlfile = ymlspec
        if technology is not None:
            set_active_technology(technology)
        tech_obj = active_technology()
        if technology is None:
            message('Using the last used technology: {}'.format(tech_obj.name))
    else:
        # Option 2: search within a specified technology
        if technology is None:
            raise ValueError('When specifying a relative dataprep file, you must also provide a technology.')

        tech_obj = Technology.technology_by_name(technology)
        set_active_technology(technology)
        if ymlspec is None:
            # default dataprep test
            ymlspec = 'default'
        else:
            # find path to tech
            if not ymlspec.endswith('.yml'):
                ymlspec += '.yml'
            ymlfile = tech_obj.eff_path(os.path.join(category, ymlspec))
    return ymlfile