''' This stuff only runs in GUI mode '''
from lygadgets import pya
import glob
import os

from lymask.invocation import gui_main, gui_drc_main
from lymask.utilities import reload_lys, active_technology


def registerMenuItems():
    menu = pya.Application.instance().main_window().menu()
    s0 = "lymask_menu"
    if not(menu.is_menu(s0)):
        menu.insert_menu('macros_menu', s0, 'lymask')

    s1 = "lymask_menu.dataprep_menu"
    if not menu.is_menu(s1):
        menu.insert_menu('lymask_menu.end', 'dataprep', 'Mask Dataprep')

    s1 = "lymask_menu.drc_menu"
    if not menu.is_menu(s1):
        menu.insert_menu('lymask_menu.end', 'drc', 'Design Rule Check')


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


def dataprep_yml_to_menu(dataprep_file, menu_path='lymask_menu.dataprep'):
    ''' Goes through all .yml files in the given directory and adds a menu item for each one
        These files are passed into the drc-like engine that uses Region to do dataprep steps in python
    '''
    menu = pya.Application.instance().main_window().menu()
    subloop_name = os.path.splitext(os.path.basename(dataprep_file))[0]
    if menu_path.endswith('dataprep'):
        action = _gen_dataprep_action(dataprep_file)
    elif menu_path.endswith('drc'):
        action = _gen_drc_action(dataprep_file)
    action.title = 'Run {}.yml'.format(subloop_name)
    if subloop_name == 'default':
        # action.shortcut = 'Shift+Ctrl+P'
        menu.insert_separator(menu_path + '.begin', 'SEP')
        menu.insert_item(menu_path + '.begin', subloop_name, action)
    else:
        menu.insert_item(menu_path + '.end', subloop_name, action)


def reload_lymask_menu(category='dataprep', tech_name=None):
    if tech_name is None:
        tech = active_technology()
    else:
        tech = pya.Technology.technology_by_name(tech_name)
    menu = pya.Application.instance().main_window().menu()

    if category == 'dataprep':
        ymlfile_dir = tech.eff_path('dataprep')
        menu_path = 'lymask_menu.dataprep'
    elif category == 'drc':
        ymlfile_dir = tech.eff_path('drc')
        menu_path = 'lymask_menu.drc'

    # clear old ones
    for item in menu.items(menu_path):
        menu.delete_item(item)
    # insert new ones
    for ymlfile in glob.iglob(ymlfile_dir + '/*.yml'):
        dataprep_yml_to_menu(ymlfile, menu_path=menu_path)

