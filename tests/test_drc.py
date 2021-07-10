import os, sys
import subprocess
import xmltodict

import lymask
from lymask import batch_drc_main

from conftest import test_dir
drc_file = os.path.join(test_dir, 'tech', 'lymask_example_tech', 'drc', 'default.yml')
layout_file = os.path.join(test_dir, '2_drc_src.oas')
outfile = os.path.join(test_dir, '2_drc_run.lyrdb')
reffile = os.path.join(test_dir, '2_drc_answer.lyrdb')


class DRC_difference(Exception):
    pass


def assert_equal(rdb_file1, rdb_file2):
    ''' Errors if the rdbs are different.
        This is done with dictionaries not the XML text itself
        Note, ordering of lists matters currently (although it shouldn't). Dict key order does not (appropriately).
    '''
    with open(rdb_file1, 'r') as fx:
        rdbspec1 = xmltodict.parse(fx.read(), process_namespaces=True)
    with open(rdb_file2, 'r') as fx:
        rdbspec2 = xmltodict.parse(fx.read(), process_namespaces=True)
    if rdbspec1 != rdbspec2:
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

