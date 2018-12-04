import os
import subprocess

from lymask import batch_main
from lytest import run_xor

test_dir = os.path.dirname(__file__)
dataprep_file = os.path.join(test_dir, 'example-dataprep.yml')
layout_file = os.path.join(test_dir, 'example_src.oas')
outfile = os.path.join(test_dir, 'example_run.oas')
reffile = os.path.join(test_dir, 'example_answer.oas')


# This one need Technology working
# def test_api():
#     batch_main(layout_file, ymlfile=dataprep_file, outfile=outfile)
#     run_xor(outfile, reffile)


def test_cm():
    command = ['lymask']
    command += [layout_file]
    command += [dataprep_file]
    command += [outfile]
    subprocess.check_call(command)
    run_xor(outfile, reffile)

