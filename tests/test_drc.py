import os, sys
import subprocess
import xmltodict
from collections import OrderedDict

import lymask
from lymask import batch_drc_main

from conftest import test_dir
drc_file = os.path.join(test_dir, 'tech', 'lymask_example_tech', 'drc', 'default.yml')
layout_file = os.path.join(test_dir, '2_drc_src.oas')
outfile = os.path.join(test_dir, '2_drc_run.lyrdb')
outfile_multithread = os.path.join(test_dir, '2_drc_multithread_run.lyrdb')
reffile = os.path.join(test_dir, '2_drc_answer.lyrdb')


class DRC_difference(Exception):
    pass


def assert_equal(rdb_file1, rdb_file2):
    ''' Errors if the rdbs are different.
        This is done with dictionaries not the XML text itself
        Order should not matter, so we use frozenset. In order to sort, we need to hash dicts,
        so we make frozendict. No need to mutate these, so it should be fine
    '''
    class frozendict(dict):
        def __hash__(self):
            return hash(tuple(sorted(self.items())))
        def __lt__(self, other):
            return hash(self) < hash(other)

    def strip_order(hierarchy):
        if isinstance(hierarchy, (dict, OrderedDict)):
            new_dict = {k: strip_order(v) for k,v in hierarchy.items()}
            return frozendict(new_dict)
        elif isinstance(hierarchy, (list, tuple)):
            new_list = [strip_order(el) for el in hierarchy]
            return frozenset(sorted(new_list))
        elif isinstance(hierarchy, str) and hierarchy.startswith('DRC:'):
            # Don't compare descriptions
            return 'DRC file'
        else:
            return hierarchy

    with open(rdb_file1, 'r') as fx:
        rdbspec1 = xmltodict.parse(fx.read(), process_namespaces=True)
    with open(rdb_file2, 'r') as fx:
        rdbspec2 = xmltodict.parse(fx.read(), process_namespaces=True)
    if strip_order(rdbspec1) != strip_order(rdbspec2):
        raise DRC_difference()


# This one need Technology working
def test_api():
    lymask.set_active_technology('lymask_example_tech')
    batch_drc_main(layout_file, ymlspec=drc_file, outfile=outfile)
    assert_equal(outfile, reffile)


def test_from_technology():
    batch_drc_main(layout_file, ymlspec='default', outfile=outfile, technology='lymask_example_tech')
    assert_equal(outfile, reffile)


def test_cm_from_tech():
    # this also checks that it defaults to default.yml
    command = ['lymask', 'drc']
    command += [layout_file]
    command += ['-o', outfile]
    command += ['-t', 'lymask_example_tech']
    subprocess.check_call(command)
    assert_equal(outfile, reffile)

def test_multithreaded():
    batch_drc_main(layout_file, ymlspec='multithreaded', outfile=outfile_multithread, technology='lymask_example_tech')
    assert_equal(outfile_multithread, reffile)

