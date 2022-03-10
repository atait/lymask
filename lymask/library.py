'''
    Common functions used by the dataprep steps
'''
from __future__ import division, print_function, absolute_import
from functools import wraps
from lymask.utilities import active_technology, lys
from lygadgets import pya, message, message_loud

try:
    dbu = active_technology().dbu
except AttributeError:
    dbu = .001


# Metrics enum was added in v0.27
try:
    Euclidian = pya.Region.Euclidian
except AttributeError:
    Euclidian = pya.Region.Metrics.Euclidian


def as_region(cell, layname):
    ''' Mostly a convenience brevity function.
        If a layer isn't in the layer set, return an empty region instead of crashing
        If a list, will return the union of the listed layers
    '''
    if isinstance(layname, (list, tuple)):
        union = pya.Region()
        for one_lay in layname:
            union += as_region(cell, one_lay)
        return union
    else:
        try:
            pya_layer = lys[layname]
        except KeyError:
            message(f'{layname} not found in layerset.')
            return pya.Region()
        return pya.Region(cell.shapes(pya_layer))


_thread_count = None
_tiles = None
def set_threads(thread_count, tiles=2):
    ''' Set to None to disable parallel processing '''
    global _thread_count, _tiles
    if thread_count == 1:
        thread_count = None
    _thread_count = thread_count
    _tiles = tiles


def _normal_smoothed(unfiltered_region, deviation=0.1):
    smoothed_region = unfiltered_region.dup()
    smoothed_region.merged_semantics = False
    smoothed_region.smooth(deviation / dbu)
    return smoothed_region


def fast_smoothed(unfiltered_region, deviation=0.1):
    ''' Removes any points that would change the shape by less than this deviation.
        This is used to significantly decrease the number of points prior to sizing

        Note: multicore does not work well with this, but it turns out to be pretty fast
    '''
    # if something goes wrong, you can fall back to regular here by uncommenting
    return _normal_smoothed(unfiltered_region, deviation)

    temp_region = unfiltered_region.dup()
    temp_region.merged_semantics = False

    output_region = pya.Region()
    tp = pya.TilingProcessor()
    tp.input('in1', temp_region)
    tp.output('out1', output_region)
    tp.queue("_output(out1, in1.smoothed({}))".format(deviation / dbu))
    # tp.tile_size(2000., 2000.)  # Not sure why this was here
    tp.tiles(_tiles, _tiles)
    tp.tile_border(5 * deviation, 5 * deviation)
    tp.threads = _thread_count
    tp.execute('Smoothing job')
    return output_region


def fast_sized(input_region, xsize):
    # if something goes wrong, you can fall back to regular here by uncommenting
    if _thread_count is None:
        return input_region.sized(xsize)
    else:
        output_region = pya.Region()
        tp = pya.TilingProcessor()
        tp.input('in1', input_region)
        tp.output('out1', output_region)
        tp.queue("_output(out1, in1.sized({}))".format(xsize))
        tp.tiles(_tiles, _tiles)
        tp.tile_border(2 * xsize, 2 * xsize)
        tp.threads = _thread_count
        tp.execute('Sizing job')
        return output_region


def fast_width(input_region, width, angle=90):
    # if something goes wrong, you can fall back to regular here by uncommenting
    if _thread_count is None:
        return input_region.width_check(width, False, Euclidian, angle)
    else:
        output_edge_pairs = pya.EdgePairs()
        tp = pya.TilingProcessor()
        tp.input('in1', input_region)
        tp.output('out1', output_edge_pairs)
        tp.queue("_output(out1, in1.width_check({}, false, Region.Euclidian, {}, nil, nil))".format(width, angle))

        border = 1.1 * width
        tp.tile_border(border, border)
        tp.tiles(_tiles, _tiles)
        tp.threads = _thread_count
        tp.execute('Width check job')
        return output_edge_pairs


def fast_space(input_region, spacing, angle=90):
    # if something goes wrong, you can fall back to regular here by uncommenting
    if _thread_count is None:
        return input_region.space_check(spacing, False, Euclidian, angle)
    else:
        output_edge_pairs = pya.EdgePairs()
        tp = pya.TilingProcessor()
        tp.input('in1', input_region)
        tp.output('out1', output_edge_pairs)
        # tp.queue("_output(out1, in1.space_check({}))".format(spacing))
        tp.queue("_output(out1, in1.space_check({}, false, Region.Euclidian, {}, nil, nil))".format(spacing, angle))

        border = 1.1 * spacing
        tp.tile_border(border, border)
        tp.tiles(_tiles, _tiles)
        tp.threads = _thread_count
        tp.execute('Spacing check job')
        return output_edge_pairs


def fast_separation(r1, r2, exclude):
    # if something goes wrong, you can fall back to regular here by uncommenting
    if _thread_count is None:
        return r1.separation_check(r2, exclude)
    else:
        output_edge_pairs = pya.EdgePairs()
        tp = pya.TilingProcessor()
        tp.input('in1', r1)
        tp.input('in2', r2)
        tp.output('out1', output_edge_pairs)
        tp.queue("_output(out1, in1.separation_check(in2, {}))".format(exclude))

        border = 2 * exclude
        tp.tile_border(border, border)
        tp.tiles(_tiles, _tiles)
        tp.threads = _thread_count
        tp.execute('Separation check job')
        return output_edge_pairs


def turbo(input_region, meth_name, meth_args, tile_border=1, job_name='Tiling job'):
    ''' Speeds things up by tiling. Parameters are determined by _thread_count and _tiles
        if _thread_count is 1, it does not invoke tile processor at all
        tile_border is in microns. Recommended that you make it 1.1 * the critical dimension.
        args is a list.
    '''
    if not isinstance(meth_args, (list, tuple)):
        meth_args = [meth_args]
    if _thread_count is None:
        return getattr(input_region, meth_name)(*meth_args)
    else:
        output_region = pya.Region()
        tp = pya.TilingProcessor()
        tp.input('in1', input_region)
        tp.output('out1', output_region)

        clean_args = list()
        for arg in meth_args:
            if arg is True:
                clean_args.append('true')
            elif arg is False:
                clean_args.append('false')
            elif arg is None:
                clean_args.append('nil')
            elif isinstance(arg, (pya.Region, pya.EdgePairs)):
                tp.input('in2', arg)
                clean_args.append('in2')
            else:
                clean_args.append(str(arg))
        job_str = '_output(out1, in1.{}({}))'.format(meth_name, ', '.join(clean_args))
        tp.queue(job_str)

        tp.tile_border(tile_border, tile_border)
        tp.tiles(_tiles, _tiles)
        tp.threads = _thread_count
        tp.execute(job_name)
        return output_region


def rdb_create(rdb, cell, category, violations):
    rdb_cell = rdb.cell_by_qname(cell.name)
    trans_to_um = pya.CplxTrans(dbu)
    drc_exclude = as_region(cell, 'DRC_exclude')
    if isinstance(violations, pya.EdgePairs):
        # This handles edge pairs
        cleaned_violations = pya.EdgePairs()
        for ep in violations.each():
            edges = pya.Edges([ep.first, ep.second])
            # If drc_exclude touches it at all, don't add it
            if drc_exclude.interacting(edges).is_empty():
                cleaned_violations.insert(ep)
    else:
        # Everything else
        cleaned_violations = violations.outside(drc_exclude)
    rdb.create_items(rdb_cell.rdb_id(), category.rdb_id(), trans_to_um, cleaned_violations)

