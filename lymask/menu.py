''' This stuff only runs in GUI mode '''
from lygadgets import pya
import glob
import os

from lymask.invocation import gui_main
from lymask.utilities import insert_layer_tab
from lymask.siepic_utils import tech_dataprep_layer_properties

DEFAULT_TECH = 'OLMAC'

def registerMenuItems():
    menu = pya.Application.instance().main_window().menu()
    s1 = "tools_menu.dataprep_menu"
    if not menu.is_menu(s1):
        menu.insert_menu('tools_menu.end', 'dataprep', 'Mask Dataprep')


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


def dataprep_yml_to_menu(dataprep_file):
    ''' Goes through all .yml files in the given directory and adds a menu item for each one
        These files are passed into the drc-like engine that uses Region to do dataprep steps in python
    '''
    menu = pya.Application.instance().main_window().menu()
    subloop_name = os.path.splitext(os.path.basename(dataprep_file))[0]
    action = _gen_dataprep_action(dataprep_file)
    action.title = 'Run {}.yml'.format(subloop_name)
    if subloop_name == 'test':
        action.shortcut = 'Shift+Ctrl+P'
        menu.insert_separator('tools_menu.dataprep.begin', 'SEP')
        menu.insert_item('tools_menu.dataprep.begin', subloop_name, action)
    else:
        menu.insert_item('tools_menu.dataprep.end', subloop_name, action)


def reload_dataprep_menu(tech_name=None):
    if tech_name is None:
        tech_name = DEFAULT_TECH
    dataprep_dir = pya.Technology.technology_by_name(tech_name).eff_path('dataprep')
    for dataprep_file in glob.iglob(dataprep_dir + '/*.yml'):
        dataprep_yml_to_menu(dataprep_file)
    # Now put in the layers refresh
    menu = pya.Application.instance().main_window().menu()
    layer_action = _gen_new_action(lambda: insert_layer_tab(tech_dataprep_layer_properties(), tab_name='Dataprep'))
    layer_action.title = 'Refresh layer display'
    # layer_action.shortcut = 'Shift+Ctrl+P'
    menu.insert_separator('tools_menu.dataprep.begin', 'SEP2')
    menu.insert_item('tools_menu.dataprep.begin', 'dataprep_layer_refresh', layer_action)
