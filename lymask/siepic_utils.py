from __future__ import division, print_function, absolute_import
''' These functions and objects are in the SiEPIC-Tools project.

    Since we don't need very many they are rewritten to keep compatibility
'''
from lygadgets.environment import pya


_active_technology_name = 'OLMAC'
def active_technology():
    if pya is None:
        return None
    return pya.Technology.technology_by_name(_active_technology_name)


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


def get_layout_variables_no_tech(cell=None):
    ''' Similar to get_layout_variables, except without looking at TECHNOLOGY
        and with the option to specify a cell
    '''
    lv = pya.Application.instance().main_window().current_view()
    if lv == None:
        print("No view selected")
        raise UserWarning("No view selected. Make sure you have an open layout.")
    if cell is None:
        # Find the currently selected layout.
        ly = lv.active_cellview().layout()
        if ly is None:
            raise UserWarning("No layout. Make sure you have an open layout.")
        # find the currently selected cell:
        cell = lv.active_cellview().cell
        if cell is None:
            raise UserWarning("No cell. Make sure you have an open layout.")
    else:
        ly = cell.layout()
    return lv, ly, cell
