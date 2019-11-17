''' Command line entry points for dataprep and drc
'''
import argparse
from lymask import __version__
import textwrap
from lymask.invocation import batch_main, batch_drc_main

top_parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=textwrap.dedent('''\
        Available commands are
          dataprep: do some mask dataprep
          drc: do some design rule checking

        Type "lytest <command> -h" for help on specific commands
        '''))
top_parser.add_argument('command', type=str, choices=['dataprep', 'drc'], metavar='<command>')
top_parser.add_argument('args', nargs=argparse.REMAINDER)
top_parser.add_argument('-v', '--version', action='version', version='%(prog)s v{}'.format(__version__))

def cm_main():
    args = top_parser.parse_args()
    if args.command == 'dataprep':
        cm_dataprep(args.args)
    if args.command == 'drc':
        cm_drc(args.args)


def add_common_args(sub_parser):
    sub_parser.add_argument('infile', type=argparse.FileType('rb'),
                        help='the input gds file')
    sub_parser.add_argument('ymlspec', nargs='?', default=None,
                        help='YML file that describes the steps and parameters. Can be relative to technology')
    sub_parser.add_argument('-o', '--outfile', nargs='?', default=None,
                        help='The output file. Dataprep default is to tack "_proc" onto the end. DRC default is to put .lyrdb on the end')
    sub_parser.add_argument('-t', '--technology', nargs='?', default=None,
                        help='The name of technology to use. Must be visible in installed technologies')


dataprep_parser = argparse.ArgumentParser(prog='lymask dataprep' ,description="Command line mask dataprep")
add_common_args(dataprep_parser)

def cm_dataprep(args):
    dataprep_args = dataprep_parser.parse_args(args)
    batch_main(dataprep_args.infile.name, ymlspec=dataprep_args.ymlspec, outfile=dataprep_args.outfile, technology=dataprep_args.technology)


drc_parser = argparse.ArgumentParser(prog='lymask drc' ,description="Command line design rule check")
add_common_args(drc_parser)

def cm_drc(args):
    drc_args = drc_parser.parse_args(args)
    batch_drc_main(drc_args.infile.name, ymlspec=drc_args.ymlspec, outfile=drc_args.outfile, technology=drc_args.technology)
