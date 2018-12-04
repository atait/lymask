from __future__ import division, print_function, absolute_import
from lygadgets import isGUI, pya, xml_to_dict
from lymask.siepic_utils import tech_layer_properties, get_layout_variables_no_tech


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
        with open(filename, 'r') as fx:
            all_layers = xml_to_dict(fx.read())['layer-properties']['properties']
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

            soen.soen_utils.name2shortName = someOtherFunction
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
    lv, _, _ = get_layout_variables_no_tech()
    i_new_tab = lv.num_layer_lists()
    if lyp_file is not None:
        try:
            lys.appendFile(lyp_file)
        except ValueError as err:
            if 'doubly defined' in err.args[0]:
                return
            else:
                raise
    if isGUI():
        lv.rename_layer_list(0, 'Designer')
        lv.insert_layer_list(i_new_tab)
        lv.current_layer_list = i_new_tab
        if lyp_file is not None:
            lv.load_layer_props(lyp_file)
        if tab_name is not None:
            lv.rename_layer_list(i_new_tab, tab_name)


#: Load the layerset for OLMAC as the module variable "lys"
try:
    lys = LayerSet.fromFile(tech_layer_properties())
except (FileNotFoundError, AttributeError):
    print('No lyp file found. Likely that technology hasn\'t loaded yet, or you don\'t have the standalone klayout')
    lys = None
