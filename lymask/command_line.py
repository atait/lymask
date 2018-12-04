''' Launches klayout application from the command line to do dataprep stuff
'''
import argparse
import os
import subprocess

from lymask import batch_main
from lymask import __version__

parser = argparse.ArgumentParser(description="Command line mask dataprep")
parser.add_argument('infile', type=argparse.FileType('rb'),
                    help='the input gds file')
parser.add_argument('ymlfile', nargs='?', default=None,
                    help='YML file that describes the dataprep steps and parameters')
parser.add_argument('outfile', nargs='?', default=None,
                    help='The output file. Default is to tack "_proc" onto the end')
parser.add_argument('-v', '--version', action='version', version=f'%(prog)s v{__version__}')


def cm_main():
    ''' This calls klayout from command line using global variables '''
    args = parser.parse_args()

    klayout_call = ['klayout']
    klayout_call += ['-z']
    klayout_call += ['-rd', 'infile={}'.format(args.infile.name)]
    if args.ymlfile is not None:
        klayout_call += ['-rd', 'ymlfile={}'.format(args.ymlfile)]
    if args.outfile is not None:
        klayout_call += ['-rd', 'outfile={}'.format(args.outfile)]

    launcher = os.path.join(os.path.dirname(__file__), 'klayout_launcher.py')
    launcher = os.path.realpath(launcher)
    klayout_call += ['-r', launcher]

    print(' '.join(klayout_call), '\n')
    try:
        retstatus = subprocess.run(klayout_call, shell=False, check=True,
                                   stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        print(err.output.decode())

# When the technology starts working, use this instead

# def cm_main():
#     ''' This one uses the klayout standalone '''
#     args = parser.parse_args()
#     batch_main(args.infile.name, ymlfile=args.ymlfile, outfile=args.outfile)


