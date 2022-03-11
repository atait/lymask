from __future__ import division, print_function, absolute_import
import os
from lygadgets import isGUI, pya, message, message_loud, lyp_to_layerlist, patch_environment
from lygadgets.technology import Technology, klayout_last_open_technology

#: This global variable to be deprecated
_active_technology = None
def active_technology():
    ''' Gets active technology from GUI if in GUI, otherwise gives the stored variable, otherwise gives default last open
    '''
    global _active_technology
    if isGUI():
        return gui_active_technology()
    else:
        if _active_technology is None:
            _active_technology = Technology.technology_by_name(klayout_last_open_technology())
        return _active_technology


def set_active_technology(tech_name):
    if not Technology.has_technology(tech_name):
        raise ValueError('Technology not found. Available are {}'.format(Technology.technology_names()))
    if isGUI() and tech_name != gui_active_technology().name:
        raise RuntimeError('Cannot set technology via lymask while in GUI')
    global _active_technology
    _active_technology = Technology.technology_by_name(tech_name)
    reload_lys(tech_name, clear=True)
# end deprecation


def tech_layer_properties(pya_tech=None):
    ''' Returns the file containing the main layer properties
    '''
    if pya_tech is None:
        pya_tech = active_technology()
    return pya_tech.eff_path(pya_tech.eff_layer_properties_file())


def tech_dataprep_layer_properties(pya_tech=None):
    ''' Returns the file containing the dataprep layer properties
    '''
    if pya_tech is None:
        pya_tech = active_technology()
    dataprep_path = pya_tech.eff_path('dataprep')
    for root, dirnames, filenames in os.walk(dataprep_path, followlinks=True):
        for filename in filenames:
            if filename.endswith('.lyp'):
                return os.path.join(root, filename)
    else:
        return tech_layer_properties()


def gui_window():
    patch_environment()  # makes sure the Application attribute gets spoofed into the standalone
    import pya
    return pya.Application.instance().main_window()


def gui_view():
    lv = gui_window().current_view()
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


def gui_active_technology():
    technology = gui_window().initial_technology  # gets the technology from the selection menu
    tech_obj = Technology.technology_by_name(technology)
    return tech_obj


def func_info_to_func_and_kwargs(func_info):
    ''' There are several ways to specify commands in the YML file. This parses them into function name and arguments
        It can be a list where first element is a function and second is a dict of kwargs.
        It can be a dict where key is function and value is dict of kwargs.
    '''
    if isinstance(func_info, str):
        func_name = func_info
        kwargs = dict()
    elif isinstance(func_info, list):
        message('Deprecation warning: spefifying a step as a list is going to go. Use dicts.')
        message(func_info)
        func_name = func_info[0]
        if len(func_info) == 1:
            kwargs = dict()
        elif len(func_info) == 2:
            kwargs = func_info[1]
        else:
            raise TypeError('Function not specified correctly as a list (needs two elements): {}'.format(func_info))
    elif isinstance(func_info, dict):
        if len(func_info.keys()) != 1:
            raise TypeError('Function not specified correctly as a dictionary (needs one key): {}'.format(func_info))
        for k, v in func_info.items():
            func_name = k
            kwargs = v
    else:
        raise TypeError('Function not specified correctly. Need str, list, dict: {}'.format(func_info))
    return func_name, kwargs


class LayerSet(dict):
    ''' getitem returns the logical layer (integer) that can be used in pya functions,
        but you have to set the active_layout first

        It is keyed by the layer name such as 'si_wg',
        but it will succeed if the __getitem__ argument is
            1. integer, in which case, we assume it describes the physical layer to be converted to the logical layer
            2. pya.LayerInfo, in which case, it is ready to be processed by pya

        It also offers object-like attributes that can be gotten, set, and deleted like lys.si_wg.
        If you have a layer like "si_n+", you must use the __getitem__ style

        A note on iterating: this does not work because it side-steps the getitem code::

            for layname, lay in lys.items():

        Instead do this:

            for layname in lys.keys():
                lay = lys[layname]
    '''
    active_layout = None

    def __call__(self, *args, **kwargs):
        return self.__getitem__(args[0])

    def __getattr__(self, attrname):
        if attrname in self.keys():
            return self.__getitem__(attrname)

    def __setattr__(self, attrname, val):
        if attrname in ['active_layout']:  # exceptions
            self.__dict__[attrname] = val
        else:
            self.__setitem__(attrname, val)

    def __delattr__(self, attrname):
        del self[attrname]

    def get_as_LayerInfo(self, item):
        try:
            val = dict.__getitem__(self, item)
        except KeyError as err:
            if type(item) is int:
                val = pya.LayerInfo(item, 0)
            elif type(item) is pya.LayerInfo:
                val = item
            else:
                raise
        return val

    def __getitem__(self, item):
        val = self.get_as_LayerInfo(item)
        try:
            answer = self.active_layout.layer(val)
        except AttributeError as err:
            if "no attribute 'layer'" in err.args[0]:
                err.args = ('You didn\'t set active_layout for this LayerSet, so you can not get items from it', )
            raise
        return answer

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError('Key must be string. Got {}.'.format(type(key)))
        if not isinstance(value, pya.LayerInfo):
            raise TypeError('Value must be pya.LayerInfo. Got {}.'.format(type(value)))
        if not value.is_named():
            value.name = key
        dict.__setitem__(self, key, value)

    @classmethod
    def fromFile(cls, filename):
        new_obj = cls()
        all_layers = lyp_to_layerlist(filename)
        for one_layer in all_layers:
            try:
                group_members = one_layer['group-members']
            except KeyError:  # it is a real layer
                short_name = name2shortName(one_layer['name'])
                new_obj[short_name] = source2pyaLayerInfo(one_layer['source'])
            else:  # it is a group
                if not isinstance(group_members, list):
                    group_members = [group_members]
                for memb in group_members:
                    short_name = name2shortName(memb['name'])
                    new_obj[short_name] = source2pyaLayerInfo(memb['source'])
        return new_obj

    def append(self, other, doubles_ok=False):
        ''' When doubles_ok is True and there is a collision, the other takes precedence '''
        for layname in other.keys():
            if layname in self.keys() and not doubles_ok:
                raise ValueError('Layer is doubly defined: {}'.format(layname))
            self[layname] = other.get_as_LayerInfo(layname)

    def appendFile(self, filename, doubles_ok=False):
        other = LayerSet.fromFile(filename)
        other.active_layout = self.active_layout
        self.append(other, doubles_ok=True)


def name2shortName(name_str):
    ''' Good to have this function separate because
        it may differ for different naming conventions.

        Reassign with::

            lymask.utilities.name2shortName = someOtherFunction
    '''
    if name_str is None:
        raise IOError('This layer has no name')
    components = name_str.split(' - ')
    if len(components) > 1:
        short_name = components[1]
    else:
        short_name = components[0]
    return short_name


def source2pyaLayerInfo(source_str):
    layer_str = source_str.split('@')[0]
    layer, datatype = layer_str.split('/')
    return pya.LayerInfo(int(layer), int(datatype))


lys = LayerSet()
def reload_lys(technology=None, clear=False, dataprep=False):
    ''' Updates lys from the lyp files. Also updates the layer display in GUI mode.
        If any of the layers are already there, it does nothing.
        If no lyp is found, does nothing
    '''
    if technology is None:
        technology = active_technology()
    elif isinstance(technology, str):
        technology = Technology.technology_by_name(technology)

    if clear: lys.clear()
    try:
        lyp_file = tech_layer_properties(technology) if not dataprep else tech_dataprep_layer_properties(technology)
        lys.appendFile(lyp_file, doubles_ok=True)
    except (FileNotFoundError, AttributeError):
        message_loud('No lyp file found. Likely that technology hasn\'t loaded yet, or you don\'t have the standalone klayout')

    if isGUI():
        lv = gui_view()
        orig_list_index = lv.current_layer_list
        was_transacting = lv.is_transacting()
        if was_transacting:
            lv.commit()
        lv.load_layer_props(lyp_file)
        if was_transacting:
            lv.transaction('Bump transaction')
        lv.current_layer_list = orig_list_index

# reload_lys()

