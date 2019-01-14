from __future__ import division, print_function, absolute_import
''' These functions and objects are in the SiEPIC-Tools project.

    Since we don't need very many they are rewritten to keep compatibility
'''
import pya
from lygadgets.technology_patch import init_klayout_technologies, klayout_last_open_technology


init_klayout_technologies()
_active_technology_name = klayout_last_open_technology()

def active_technology():
    if pya is None:
        return None
    return pya.Technology.technology_by_name(_active_technology_name)


def set_active_technology(tech_name):
    if tech_name not in pya.Technology.technology_names():
        raise ValueError('Technology not found. Have you run "init_klayout_technologies"?')
    global _active_technology_name
    _active_technology_name = tech_name


def tech_layer_properties():
    ''' Returns the file containing the main layer properties
    '''
    pya_tech = active_technology()
    return pya_tech.eff_path(pya_tech.eff_layer_properties_file())


def tech_dataprep_layer_properties():
    ''' Returns the file containing the main layer properties
    '''
    pya_tech = active_technology()
    return pya_tech.eff_path('dataprep/klayout_layers_dataprep.lyp')


## Getting GUI layout variables
## See https://github.com/lukasc-ubc/SiEPIC-Tools/blob/28deaa79533a9e213fcd664a50bc73a60e78fcbd/klayout_dot_config/python/SiEPIC/utils/__init__.py#L405

def gui_view():
    lv = pya.Application.instance().main_window().current_view()
    if lv == None:
        raise UserWarning("No view selected. Make sure you have an open layout.")
    return lv


def gui_active_layout():
    ly = gui_view().active_cellview().layout()
    if ly == None:
        raise UserWarning("No layout. Make sure you have an open layout.")
    return ly


def gui_active_cell():
    cell = gui_view().active_cellview().cell
    if cell == None:
        raise UserWarning("No cell. Make sure you have an open layout.")
    return cell
