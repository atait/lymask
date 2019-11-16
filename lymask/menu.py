''' This stuff only runs in GUI mode '''
from lygadgets import pya
import glob
import os

from lymask.invocation import gui_main, gui_drc_main
from lymask.utilities import reload_lys

DEFAULT_TECH = 'OLMAC'

def registerMenuItems():
    menu = pya.Application.instance().main_window().menu()
    s0 = "soen_menu"
    if not(menu.is_menu(s0)):
        menu.insert_menu('macros_menu', s0, 'SOEN PDK')

    s1 = "soen_menu.dataprep_menu"
    if not menu.is_menu(s1):
        menu.insert_menu('soen_menu.end', 'dataprep', 'Mask Dataprep')

    s1 = "soen_menu.drc_menu"
    if not menu.is_menu(s1):
        menu.insert_menu('soen_menu.end', 'drc', 'Design Rule Check')


global item_counter
item_counter = 0
def _gen_new_action(func):
    ''' There a strange bug where pya.Actions get managed to the same location in memory.
        Same with the _Signals that are created when on_triggered is set.

        Assigning them to global variables with different names seems to work.
        It also works if you step through in a debugger.
        It does NOT work if you use locals()

        This function will create functions and action triggers correctly
    '''
    global item_counter
    item_str = 'action_item%s' % item_counter
    func_str = 'action_function%s' % item_counter
    globals()[item_str] = pya.Action()
    globals()[func_str] = func
    globals()[item_str].on_triggered = globals()[func_str]
    item_counter += 1
    return globals()[item_str]


def _gen_dataprep_action(dataprep_file):
    def wrapped():
        gui_main(dataprep_file)
    return _gen_new_action(wrapped)

def _gen_drc_action(drc_file):
    def wrapped():
        gui_drc_main(drc_file)
    return _gen_new_action(wrapped)


def dataprep_yml_to_menu(dataprep_file, category='dataprep'):
    ''' Goes through all .yml files in the given directory and adds a menu item for each one
        These files are passed into the drc-like engine that uses Region to do dataprep steps in python
    '''
    menu = pya.Application.instance().main_window().menu()
    subloop_name = os.path.splitext(os.path.basename(dataprep_file))[0]
    if category == 'dataprep':
        action = _gen_dataprep_action(dataprep_file)
    elif category == 'drc':
        action = _gen_drc_action(dataprep_file)
    action.title = 'Run {}.yml'.format(subloop_name)
    if subloop_name == 'default':
        # action.shortcut = 'Shift+Ctrl+P'
        menu.insert_separator('soen_menu.{}.begin'.format(category), 'SEP')
        menu.insert_item('soen_menu.{}.begin'.format(category), subloop_name, action)
    else:
        menu.insert_item('soen_menu.{}.end'.format(category), subloop_name, action)


def reload_dataprep_menu(tech_name=None):
    if tech_name is None:
        tech_name = DEFAULT_TECH
    dataprep_dir = pya.Technology.technology_by_name(tech_name).eff_path('dataprep')
    for dataprep_file in glob.iglob(dataprep_dir + '/*.yml'):
        dataprep_yml_to_menu(dataprep_file, category='dataprep')

    # Now put in the layers refresh
    menu = pya.Application.instance().main_window().menu()
    layer_action = _gen_new_action(lambda *args: reload_lys(*args, dataprep=True))
    layer_action.title = 'Refresh layer display'
    layer_action.shortcut = 'Shift+Ctrl+P'
    menu.insert_separator('soen_menu.dataprep.begin', 'SEP2')
    menu.insert_item('soen_menu.dataprep.begin', 'dataprep_layer_refresh', layer_action)


def reload_drc_menu(tech_name=None):
    if tech_name is None:
        tech_name = DEFAULT_TECH
    drc_dir = pya.Technology.technology_by_name(tech_name).eff_path('drc')
    for drc_file in glob.iglob(drc_dir + '/*.yml'):
        dataprep_yml_to_menu(drc_file, category='drc')
