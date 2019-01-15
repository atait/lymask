from __future__ import division, print_function, absolute_import
from lygadgets import isGUI, pya, lyp_to_layerlist
from lygadgets.technology import Technology, klayout_last_open_technology


#: This global variable to be deprecated
_active_technology = Technology.technology_by_name(klayout_last_open_technology())
def active_technology():
    return _active_technology


def set_active_technology(tech_name):
    if not Technology.has_technology(tech_name):
        raise ValueError('Technology not found. Available are {}'.format(Technology.technology_names()))
    global _active_technology
    _active_technology = Technology.technology_by_name(tech_name)
    reload_lys(tech_name)
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
    import pya
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


def gui_active_technology():
    pass # todo

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

    def append(self, other):
        for layname in other.keys():
            if layname in self.keys():
                raise ValueError('Layer is doubly defined: {}'.format(layname))
            self[layname] = other.get_as_LayerInfo(layname)

    def appendFile(self, filename):
        other = LayerSet.fromFile(filename)
        other.active_layout = self.active_layout
        self.append(other)


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


def insert_layer_tab(lyp_file=None, tab_name=None):
    ''' Also updates lys, but if any of the layers are already there, it does nothing.
        If lyp_file is None, creates an empty layer list or does nothing if not in GUI mode.
    '''
    if lyp_file is not None and lys is not None:
        try:
            lys.appendFile(lyp_file)
        except ValueError as err:
            if 'doubly defined' in err.args[0]:
                return
            else:
                raise
    if isGUI():
        lv = gui_view()
        i_new_tab = lv.num_layer_lists()
        lv.rename_layer_list(0, 'Designer')
        lv.insert_layer_list(i_new_tab)
        lv.current_layer_list = i_new_tab
        if lyp_file is not None:
            lv.load_layer_props(lyp_file)
        if tab_name is not None:
            lv.rename_layer_list(i_new_tab, tab_name)


lys = LayerSet()
def reload_lys(technology=None):
    global lys
    lys.clear()
    try:
        lyp_file = tech_layer_properties(Technology.technology_by_name(technology))
        lys.appendFile(lyp_file)
    except (FileNotFoundError, AttributeError):
        print('No lyp file found. Likely that technology hasn\'t loaded yet, or you don\'t have the standalone klayout')


reload_lys()

