import os, sys
import subprocess
import pytest
import pya

import lymask
from lymask import batch_main
from lytest import run_xor

from conftest import test_dir
dataprep_file = os.path.join(test_dir, 'tech', 'lymask_example_tech', 'dataprep', 'default.yml')
layout_file = os.path.join(test_dir, '1_src.oas')
outfile = os.path.join(test_dir, '1_run.oas')
reffile = os.path.join(test_dir, '1_answer.oas')


# This one need Technology working
def test_api():
    lymask.set_active_technology('lymask_example_tech')
    batch_main(layout_file, ymlspec=dataprep_file, outfile=outfile)
    run_xor(outfile, reffile)


def test_lyp_loading():
    from lymask.utilities import set_active_technology, reload_lys, lys
    layout = pya.Layout()
    layout.read(layout_file)
    lys.active_layout = layout

    lymask.set_active_technology('lymask_example_tech')
    lymask.utilities.reload_lys()

    assert lys['m5_wiring'] is lys('m5_wiring') is lys.m5_wiring

    with pytest.raises(KeyError):
        batch_main(layout_file, ymlspec='bad_masks', technology='lymask_example_tech')


def test_from_technology():
    batch_main(layout_file, ymlspec='default', outfile=outfile, technology='lymask_example_tech')
    run_xor(outfile, reffile)


def test_cm_from_tech():
    # this also checks that it defaults to default.yml
    command = ['lymask', 'dataprep']
    command += [layout_file]
    command += ['-o', outfile]
    command += ['-t', 'lymask_example_tech']
    subprocess.check_call(command)
    run_xor(outfile, reffile)

