import sys
import os
import io
import pathlib
import argparse
from systemrdl import RDLCompiler, RDLCompileError
from peakrdl_ipxact import IPXACTImporter

from systemrdl import RDLListener, RDLWalker

# add `.` source tree into PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

import RDLWriter

# Instantiate the parser
parser = argparse.ArgumentParser(description='Converts IP-XACT register model to System RDL model.')
parser.add_argument('-o', '--output', dest='output', required=True, type=pathlib.Path,
        help='System RDL output file, stdout if not given')
parser.add_argument('-i', '--input', dest='file', required=True, type=pathlib.Path,
        help='IP-XACT file to convert')
opts = parser.parse_args()


rdlc = RDLCompiler()
ipxact = IPXACTImporter(rdlc)

root = None
iof = None
if opts.output is None:
    iof = io.StringIO()

try:
    ipxact.import_file( opts.file )

#    if opts.output is not None:
#        rdlc.compile_file( opts.output )

    root = rdlc.elaborate()
except RDLCompileError:
    sys.exit(1)

# Traverse the register model!
walker = RDLWalker(unroll=True)
listener = RDLWriter.RDLWriterListener()
walker.walk(root, listener)