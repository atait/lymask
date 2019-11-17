'''
    Entry points from GUI and API
'''
from __future__ import division, print_function, absolute_import
import os
import yaml
from lygadgets import pya, message, Technology

from lymask.utilities import gui_view, gui_active_layout, gui_window, gui_active_technology, \
                             active_technology, set_active_technology, \
                             tech_layer_properties, \
                             lys, reload_lys
from lymask.dataprep_steps import all_dpfunc_dict, assert_valid_dataprep_steps
from lymask.drc_steps import all_drcfunc_dict, assert_valid_drc_steps


def _main(layout, ymlfile, tech_obj=None):
    # todo: figure out which technology we will be using and its layer properties
    with open(ymlfile) as fx:
        step_list = yaml.load(fx)
    reload_lys(tech_obj, dataprep=True)
    assert_valid_dataprep_steps(step_list)
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
    if step_list[0][0] != 'make_rdbcells':
        step_list.insert(0, ['make_rdbcells'])
    reload_lys(tech_obj, dataprep=True)
    # assert_valid_drc_steps(step_list)

    rdb = pya.ReportDatabase('DRC: {}'.format(os.path.basename(ymlfile)))
    rdb.description = 'DRC: {}'.format(os.path.basename(ymlfile))

    for func_info in step_list:
        func, kwargs = func_info_to_func_and_kwargs(func_info)
        message('lymask doing {}'.format(func.__name__))
        for TOP_ind in layout.each_top_cell():
            func(layout.cell(TOP_ind), rdb, **kwargs)
    return rdb


def func_info_to_func_and_kwargs(func_info):
    ''' There are several ways to specify it in the YML file.
        It can be a list where first element is a function and second is a dict of kwargs.
        It can be a dict where key is function and value is dict of kwargs.
    '''
    if isinstance(func_info, list):
        message('Deprecation warning: spefifying a step as a list is going to go. Use dicts.')
        if len(func_info) == 1:
            func_info.append(dict())
        if len(func_info) != 2:
            raise TypeError('Function not specified correctly as a list (needs two elements): {}'.format(func_info))
        func = all_drcfunc_dict[func_info[0]]
        kwargs = func_info[1]
    elif isinstance(func_info, dict):
        if len(func_info.keys()) != 1:
            raise TypeError('Function not specified correctly as a dictionary (needs one key): {}'.format(func_info))
        for k, v in func_info.items():
            func = all_drcfunc_dict[k]
            kwargs = v
    return func, kwargs


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
