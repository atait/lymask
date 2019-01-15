from __future__ import division, print_function, absolute_import
''' These functions and objects are in the SiEPIC-Tools project.

    Since we don't need very many they are rewritten to keep compatibility
'''
import pya
from lygadgets.technology import Technology, klayout_last_open_technology
from lygadgets import patch_environment


#: This global variable to be deprecated
_active_technology_name = klayout_last_open_technology()
def active_technology():
    return Technology.technology_by_name(_active_technology_name)


def set_active_technology(tech_name):
    if not Technology.has_technology(tech_name):
        raise ValueError('Technology not found. Available are {}'.format(Technology.technology_names()))
    global _active_technology_name
    _active_technology_name = tech_name
# end deprecation

def tech_layer_properties(pya_tech=None):
    ''' Returns the file containing the main layer properties
    '''
    if pya_tech is None:
        pya_tech = active_technology()
    return pya_tech.eff_path(pya_tech.eff_layer_properties_file())


def tech_dataprep_layer_properties(pya_tech=None):
    ''' Returns the file containing the main layer properties
    '''
    if pya_tech is None:
        pya_tech = active_technology()
    return pya_tech.eff_path('dataprep/klayout_layers_dataprep.lyp')


def gui_view():
    patch_environment()  # makes sure the Application attribute gets spoofed into the standalone
    lv = pya.Application.instance().main_window().current_view()
    if lv is None:
        raise UserWarning("No view selected. Make sure you have an open layout.")
    return lv


def gui_active_layout():
    ly = gui_view().active_cellview().layout()
    if ly is None:
        raise UserWarning("No layout. Make sure you have an open layout.")
    return ly


def gui_active_cell():
    cell = gui_view().active_cellview().cell
    if cell is None:
        raise UserWarning("No cell. Make sure you have an open layout.")
    return cell
