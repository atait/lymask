'''
    Common functions used by the dataprep steps
'''
from __future__ import division, print_function, absolute_import
from functools import wraps
import pya
from lymask.utilities import active_technology, lys

try:
    dbu = active_technology().dbu
except AttributeError:
    dbu = .001


def as_region(cell, layname):
    ''' Just a convenience brevity function '''
    return pya.Region(cell.shapes(lys[layname]))


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
    tp.tile_size(2000., 2000.)
    tp.tile_border(5 * deviation, 5 * deviation)
    tp.threads = _thread_count
    tp.execute('Smoothing job')
    return output_region


_thread_count = None
def set_threads(thread_count):
    ''' Set to None to disable parallel processing '''
    global _thread_count
    if thread_count == 1:
        thread_count = None
    _thread_count = thread_count


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
        tp.tile_size(2000., 2000.)
        tp.tile_border(2 * xsize, 2 * xsize)
        tp.threads = _thread_count
        tp.execute('Sizing job')
        return output_region
