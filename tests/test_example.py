import os, sys
import subprocess
os.environ['KLAYOUT_HOME'] = os.path.dirname(os.path.realpath(__file__))

import lymask
from lymask import batch_main
from lytest import run_xor

test_dir = os.path.dirname(__file__)
dataprep_file = os.path.join(test_dir, 'tech', 'example_tech', 'dataprep', 'test.yml')
layout_file = os.path.join(test_dir, '1_src.oas')
outfile = os.path.join(test_dir, '1_run.oas')
reffile = os.path.join(test_dir, '1_answer.oas')


# This one need Technology working
def test_api():
    lymask.set_active_technology('example_tech')
    batch_main(layout_file, ymlspec=dataprep_file, outfile=outfile)
    run_xor(outfile, reffile)


def test_from_technology():
    # os.environ['KLAYOUT_HOME'] = os.path.dirname(os.path.realpath(__file__))
    batch_main(layout_file, ymlspec='test', outfile=outfile, technology='example_tech')
    run_xor(outfile, reffile)


# def test_cm():
#     command = ['lymask']
#     command += [layout_file]
#     command += [dataprep_file]
#     command += ['-o', outfile]
#     subprocess.check_call(command)
#     run_xor(outfile, reffile)

# def test_cm_from_tech():
#     # os.environ['KLAYOUT_HOME'] = os.path.dirname(os.path.realpath(__file__))
#     command = ['lymask']
#     command += [layout_file]
#     command += ['-o', outfile]
#     command += ['-t', 'example_tech']
#     subprocess.check_call(command)
#     run_xor(outfile, reffile)

