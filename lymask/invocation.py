'''
    Entry points from GUI and API
'''
from __future__ import division, print_function, absolute_import
import os
import yaml
from lygadgets import pya, message, message_loud, Technology

from lymask.utilities import gui_view, gui_active_layout, gui_window, gui_active_technology, \
                             active_technology, set_active_technology, \
                             tech_layer_properties, \
                             lys, reload_lys, func_info_to_func_and_kwargs
from lymask.dataprep_steps import all_dpfunc_dict, assert_valid_dataprep_steps
from lymask.drc_steps import all_drcfunc_dict, assert_valid_drc_steps


def _main(layout, ymlfile, tech_obj=None):
    with open(ymlfile) as fx:
        step_list = yaml.load(fx, Loader=yaml.FullLoader)
    reload_lys(tech_obj, dataprep=True)
    assert_valid_dataprep_steps(step_list)
    for func_info in step_list:
        func_name, kwargs = func_info_to_func_and_kwargs(func_info)
        message('lymask doing {}: {}'.format(func_name, kwargs))
        func = all_dpfunc_dict[func_name]
        for TOP_ind in layout.each_top_cell():
            # call it
            try:
                func(layout.cell(TOP_ind), **kwargs)
            except Exception as err:
                message_loud(str(err))
                raise
    return layout


def _drc_main(layout, ymlfile, tech_obj=None):
    with open(ymlfile) as fx:
        step_list = yaml.load(fx, Loader=yaml.FullLoader)
    if func_info_to_func_and_kwargs(step_list[0])[0] != 'make_rdbcells':
        step_list.insert(0, 'make_rdbcells')
    reload_lys(tech_obj, dataprep=True)
    # assert_valid_drc_steps(step_list)

    rdb = pya.ReportDatabase('DRC: {}'.format(os.path.basename(ymlfile)))
    rdb.description = 'DRC: {}'.format(os.path.basename(ymlfile))

    for func_info in step_list:
        func_name, kwargs = func_info_to_func_and_kwargs(func_info)
        message('lymask doing {}: {}'.format(func_name, kwargs))
        func = all_drcfunc_dict[func_name]
        for TOP_ind in layout.each_top_cell():
            try:
                func(layout.cell(TOP_ind), rdb, **kwargs)
            except Exception as err:
                message_loud(str(err))
                raise
    return rdb


def gui_main(ymlfile=None):
    layout = gui_active_layout()
    lys.active_layout = layout
    tech_obj = gui_active_technology()

    gui_view().transaction('Mask Dataprep')
    try:
        processed = _main(layout, ymlfile=ymlfile, tech_obj=tech_obj)
    finally:
        gui_view().commit()


def gui_drc_main(ymlfile=None):
    layout = gui_active_layout()
    lys.active_layout = layout
    tech_obj = gui_active_technology()

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
        outfile = infile[:-4] + '_proc.oas'
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
    message('DRC violations:', rdb.num_items())
    message('Full report:', outfile)


def resolve_ymlspec(ymlspec=None, technology=None, category='dataprep'):
    ''' Find the yml file that describes the process. There are several options for inputs
        # Option 1: file path is specified directly
        # Option 2: search within a specified technology

        This also sets the active_technology stored in the module
    '''
    if ymlspec is not None and os.path.isfile(os.path.realpath(ymlspec)):
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
        # find path to tech
        if not ymlspec.endswith('.yml'):
            ymlspec += '.yml'
        ymlfile = tech_obj.eff_path(os.path.join(category, ymlspec))
    if not os.path.isfile(ymlfile):
        raise FileNotFoundError('Could not resolve YAML specification: {}'.format(ymlspec))
    return ymlfile
