from lymask import batch_main
from lytest import run_xor
import subprocess

dataprep_file = 'example-dataprep.yml'
layout_file = 'example_src.oas'
outfile = 'example_run.oas'
reffile = 'example_answer.oas'


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

