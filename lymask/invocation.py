'''
    Entry points from GUI, command line, and API
'''
from __future__ import division, print_function, absolute_import
import os
import yaml
import argparse
from lygadgets import pya, message, Technology

from lymask import __version__
from lymask.utilities import gui_view, gui_active_layout, \
                             active_technology, set_active_technology, \
                             tech_dataprep_layer_properties, \
                             lys, insert_layer_tab
from lymask.steps import all_func_dict


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
    # todo: reload lys using technology
    with open(ymlfile) as fx:
        step_list = yaml.load(fx)
    insert_layer_tab(tech_dataprep_layer_properties(tech_obj), tab_name='Dataprep')
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
        if technology is not None:
            set_active_technology(technology)
        tech_obj = active_technology()
        if technology is None:
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
    processed = _main(layout, ymlfile=ymlfile, tech_obj=tech_obj)
    # Write it
    processed.write(outfile)
