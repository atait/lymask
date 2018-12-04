from lymask import batch_main

global infile, ymlfile, outfile
try:
    ymlfile
except NameError:
    ymlfile = None
try:
    outfile
except NameError:
    outfile = None

batch_main(infile, ymlfile=ymlfile, outfile=outfile)
