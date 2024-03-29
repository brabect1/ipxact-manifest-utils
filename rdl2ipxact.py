# modified `examples/convert_to_ipxact.py` from https://github.com/SystemRDL/PeakRDL-ipxact
import sys
import io
import pathlib
import argparse
import logging

from typing import Union, Optional, TYPE_CHECKING, Any
from xml.dom import minidom
import xml.etree.ElementTree as et

from systemrdl import RDLCompiler, RDLCompileError
from systemrdl.node import AddressableNode, RootNode, Node
from systemrdl.node import AddrmapNode, MemNode
from systemrdl.node import RegNode, RegfileNode, FieldNode
from peakrdl_ipxact import IPXACTExporter, Standard


# https://stackoverflow.com/a/65808327
def _pretty_print(current, parent=None, index=-1, depth=0, indent='  '):
    for i, node in enumerate(current):
        _pretty_print(node, current, i, depth + 1, indent)
    if parent is not None:
        if index == 0:
            parent.text = '\n' + (indent * depth)
        else:
            parent[index - 1].tail = '\n' + (indent * depth)
        if index == len(parent) - 1:
            current.tail = '\n' + (indent * (depth - 1))


class XactNamespace(object):

    ns = {'ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014"};

    def __init__(self, ns = None):
        self.ns = ns;

    def compileTag(self, tag:str, prefix:str = 'ipxact'):
        ns = self.ns or XactNamespace.ns;
        if ns and prefix is not None:
            if prefix in ns:
                tag = f'{{{ns[prefix]}}}{tag}';
            else:
                logging.error(f"Unregistered namespace prefix (geistered: {''.join([i for i in ns])}): {prefix}");
                tag = prefix + ':' + tag;
        elif ns and prefix is None and len(ns) == 1:
            # when a sole namespace registered, then use it
            prefix = list(ns.values())[0];
            tag = f'{{{prefix}}}{tag}';
        elif prefix is not None:
            tag = prefix + ':' + tag;

        return tag;


def minidom2elementtree(node: minidom.Node):
    if node is None:
        return None;

    try:
        s = node.toxml();

        # ElementTree namespaces for XML parsing
        # (the proper IP-XACT/XML namespaces shall use `xmlns:` prefix to
        # namespace names; however, ElementTree does not support it for
        # `ElementTree.register_namespace()`.)
        ns = {'xsi':"http://www.w3.org/2001/XMLSchema-instance",
        'ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014"
        };

        for p,u in ns.items():
            logging.debug(f"registering namespace {p}:{u}");
            et.register_namespace(p, u);

        root = et.fromstring(s);
        return et.ElementTree(root);

    except Exception as e:
        logging.error(e);
        return None;


def add_mmap(node: Union[AddrmapNode, RootNode], comp: minidom.Element, ns: XactNamespace):
    if node is None or comp is None:
        return;

    if ns is None: ns = XactNamespace();

    dom = comp.ownerDocument;

    # get existing `memoryMaps` (if already exists)
    mmaps =  None;
    if comp.hasChildNodes():
        for n in comp.childNodes:
            if n.nodeType != minidom.Node.ELEMENT_NODE: continue;
            if n.tagName == ns.compileTag('memoryMaps'):
                mmaps = n;
                break;

    # create new `memoryMaps` (if none exists)
    if mmaps is None:
        mmaps = dom.createElement(ns.compileTag("memoryMaps"));

        # insert into correct position (so that resulting XML validates
        # to IP-XACT schema)
        inserted = False;
        if comp.hasChildNodes():
            elemseq = ['vendor', 'library', 'name', 'version',
                    'busInterfaces', 'indirectInterfaces', 'channels',
                    'remapStates', 'addressSpaces', 'memoryMaps',
                    'model', 'componentGenerators', 'choices',
                    'fileSets', 'whiteboxElements', 'cpus',
                    'otherClockDrivers', 'resetTypes', 'description',
                    'parameters', 'assertions', 'vendorExtensions'];

            predecesors = elemseq[:elemseq.index('memoryMaps')];
            for n in comp.childNodes:
                if n.nodeType != minidom.Node.ELEMENT_NODE: continue;
                _, _, tag = n.tagName.rpartition(':');
                if tag not in predecesors:
                    comp.insertBefore(mmaps,n);
                    inserted = True;
                    break;

        if not inserted:
            comp.appendChild(mmaps);

    # get existing `memoryMaps.memoryMap` (if already exists)
    #TODO ...

    exporter = IPXACTExporter();
    exporter.doc = dom;

    #---->>>> GPL licensed code (from peakrdl_ipxact.Exporter)
    # Determine if top-level node should be exploded across multiple
    # addressBlock groups
    explode = False

    # If top node is an addrmap, and it contains 1 or more children that
    # are:
    # - exclusively addrmap or mem
    # - and None of them are arrays
    # ... then it makes more sense to "explode" the
    # top-level node and make each of its children their own addressBlock
    # (explode --> True)
    #
    # Otherwise, do not "explode" the top-level node
    # (explode --> False)
    if isinstance(node, AddrmapNode):
        addrblockable_children = 0
        non_addrblockable_children = 0

        for child in node.children(skip_not_present=False):
            if not isinstance(child, AddressableNode):
                continue

            if isinstance(child, (AddrmapNode, MemNode)) and not child.is_array:
                addrblockable_children += 1
            else:
                non_addrblockable_children += 1

        if (non_addrblockable_children == 0) and (addrblockable_children >= 1):
            explode = True
    #<<<<----

    # Do the export!
    # --------------
    # top-node becomes the memoryMap
    mmap = dom.createElement(ns.compileTag("memoryMap"));
    mmaps.appendChild(mmap);

    #---->>>> GPL licensed code (from peakrdl_ipxact.Exporter)
    if explode:
        exporter.add_nameGroup(mmap,
            node.inst_name,
            node.get_property("name", default=None),
            node.get_property("desc")
        );

        # Top-node's children become their own addressBlocks
        for child in node.children(skip_not_present=False):
            if not isinstance(child, AddressableNode):
                continue;

            exporter.add_addressBlock(mmap, child);
    else:
        # Not exploding apart the top-level node

        # Wrap it in a dummy memoryMap that bears its name
        exporter.add_nameGroup(mmap, "%s_mmap" % node.inst_name);

        # Export top-level node as a single addressBlock
        exporter.add_addressBlock(mmap, node);
    #<<<<----


class CustomIPXACTExporter(IPXACTExporter):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs);

    def write_out(self, node: Union[AddrmapNode, RootNode], f: io.TextIOBase=sys.stdout, **kwargs: Any) -> None:
        """
        Parameters
        ----------
        node: AddrmapNode
            Top-level SystemRDL node to export.
        path:
            Path to save the exported XML file.
        component_name: str
            IP-XACT component name. If unspecified, uses the top node's name
            upon export.
        """

        self.msg = node.env.msg

        component_name = kwargs.pop("component_name", None) or node.inst_name

        # Check for stray kwargs
        if kwargs:
            raise TypeError("got an unexpected keyword argument '%s'" % list(kwargs.keys())[0])

        # If it is the root node, skip to top addrmap
        if isinstance(node, RootNode):
            node = node.top

        if not isinstance(node, (AddrmapNode, MemNode)):
            raise TypeError("'node' argument expects type AddrmapNode or MemNode. Got '%s'" % type(node).__name__)

        if isinstance(node, AddrmapNode) and node.get_property('bridge'):
            self.msg.warning(
                "IP-XACT generator does not have proper support for bridge addmaps yet. The 'bridge' property will be ignored.",
                node.inst.property_src_ref.get('bridge', node.inst.inst_src_ref)
            )

        # Initialize XML DOM
        self.doc = minidom.getDOMImplementation().createDocument(None, None, None)

        tmp = self.doc.createComment("Generated by PeakRDL IP-XACT (https://github.com/SystemRDL/PeakRDL-ipxact)")
        self.doc.appendChild(tmp)

        # Create top-level component
        comp = self.doc.createElement(self.ns + "component")
        if self.standard == Standard.IEEE_1685_2014:
            comp.setAttribute("xmlns:ipxact", "http://www.accellera.org/XMLSchema/IPXACT/1685-2014")
            comp.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
            comp.setAttribute("xsi:schemaLocation", "http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd")
        elif self.standard == Standard.IEEE_1685_2009:
            comp.setAttribute("xmlns:spirit", "http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009")
            comp.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
            comp.setAttribute("xsi:schemaLocation", "http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009 http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009/index.xsd")

        else:
            raise RuntimeError
        self.doc.appendChild(comp)

        # versionedIdentifier Block
        self.add_value(comp, self.ns + "vendor", self.vendor)
        self.add_value(comp, self.ns + "library", self.library)
        self.add_value(comp, self.ns + "name", component_name)
        self.add_value(comp, self.ns + "version", self.version)

        mmaps = self.doc.createElement(self.ns + "memoryMaps")
        comp.appendChild(mmaps)

        # Determine if top-level node should be exploded across multiple
        # addressBlock groups
        explode = False

        # If top node is an addrmap, and it contains 1 or more children that
        # are:
        # - exclusively addrmap or mem
        # - and None of them are arrays
        # ... then it makes more sense to "explode" the
        # top-level node and make each of its children their own addressBlock
        # (explode --> True)
        #
        # Otherwise, do not "explode" the top-level node
        # (explode --> False)
        if isinstance(node, AddrmapNode):
            addrblockable_children = 0
            non_addrblockable_children = 0

            for child in node.children(skip_not_present=False):
                if not isinstance(child, AddressableNode):
                    continue

                if isinstance(child, (AddrmapNode, MemNode)) and not child.is_array:
                    addrblockable_children += 1
                else:
                    non_addrblockable_children += 1

            if (non_addrblockable_children == 0) and (addrblockable_children >= 1):
                explode = True

        # Do the export!
        if explode:
            # top-node becomes the memoryMap
            mmap = self.doc.createElement(self.ns + "memoryMap")
            self.add_nameGroup(mmap,
                node.inst_name,
                node.get_property("name", default=None),
                node.get_property("desc")
            )
            mmaps.appendChild(mmap)

            # Top-node's children become their own addressBlocks
            for child in node.children(skip_not_present=False):
                if not isinstance(child, AddressableNode):
                    continue

                self.add_addressBlock(mmap, child)
        else:
            # Not exploding apart the top-level node

            # Wrap it in a dummy memoryMap that bears its name
            mmap = self.doc.createElement(self.ns + "memoryMap")
            self.add_nameGroup(mmap, "%s_mmap" % node.inst_name)
            mmaps.appendChild(mmap)

            # Export top-level node as a single addressBlock
            self.add_addressBlock(mmap, node)

        # Write out XML dom
        if f is None:
            f = sys.stdout;
        self.doc.writexml(
            f,
            addindent=self.xml_indent,
            newl=self.xml_newline,
            encoding="UTF-8"
        )

# Instantiate the parser
parser = argparse.ArgumentParser(description='Reads in System RDL file and exports it to IP-XACT register model.')
parser.add_argument('-o', '--output', dest='output', required=False, type=pathlib.Path,
        help='IP-XACT output file, stdout if not given')
#TODO parser.add_argument('-i', '--input', dest='file', required=True, type=pathlib.Path,
#TODO         help='System RDL file to convert')
parser.add_argument('--xact', dest='xact', required=False, type=pathlib.Path,
        help='IP-XACT 2014 to be updated with view information.')
parser.add_argument('--xact-library', dest='library', required=False, type=str,
        help='IP-XACT component library name.');
parser.add_argument('--xact-version', dest='version', required=False, type=str,
        help='IP-XACT component version number.');
parser.add_argument('--xact-vendor', dest='vendor', required=False, type=str,
        help='IP-XACT component vendor name.');
parser.add_argument('--xact-name', dest='name', required=False, type=str,
        help='IP-XACT component name.');
parser.add_argument('--rwd', dest='rwd', required=False, type=pathlib.Path,
        help='Relative Working Directory (RWD), which to make file paths relative to. Applies only if `output` not specified.');
parser.add_argument('--log-level', dest='loglevel', required=False, type=str, default='ERROR',
        help='Logging severity, one of: DEBUG, INFO, WARNING, ERROR, FATAL. Defaults to ERROR.');
parser.add_argument('-l', '--log-file', dest='logfile', required=False, type=pathlib.Path, default=None,
        help='Path to a log file. Defaults to stderr if none given.');
parser.add_argument('file', type=pathlib.Path,
        help='System RDL file to convert');

# parse CLI options
opts = parser.parse_args();

# default logging setup
logging.basicConfig(level=logging.ERROR);

# setup logging destination (file or stderr)
# (stderr is already set as default in the logging setup)
if opts.logfile is not None:
    logFileHandler = None;
    try:
        # using `'w'` will make the FileHandler overwrite the log file rather than
        # append to it
        logFileHandler = logging.FileHandler(str(opts.logfile),'w');
    except Exception as e:
        logging.error(e);

    if logFileHandler is not None:
        rootLogger = logging.getLogger();
        fmt = None;
        if len(rootLogger.handlers) > 0:
            fmt = rootLogger.handlers[0].formatter;
        if fmt is not None:
            logFileHandler.setFormatter(fmt);
        rootLogger.handlers = []; # remove default handlers
        rootLogger.addHandler(logFileHandler);

# setup logging level
try:
    logging.getLogger().setLevel(opts.loglevel);
except Exception as e:
    logging.error(e);

# output directory
# (`None` means to use absolute paths)
if opts.output:
    outputDir = str(opts.output.parent);
elif opts.rwd:
    outputDir = str(opts.rwd);
else:
    outputDir = None;

# Create an instance of the compiler
rdlc = RDLCompiler();

try:
    rdlc.compile_file(opts.file);
    root = rdlc.elaborate();
except RDLCompileError as e:
    # A compilation error occurred. Exit with error code
    logging.error(f"Failed to parse {opts.file}: {e}");
    sys.exit(1);

# Override `XactNamespace` mapping as it would otherwise yield ElementTree
# namespace prefix of `{uri}tag`. Setting it to `None` would make `compileTag()`
# yield the minidom expected `prefix:tag`.
XactNamespace.ns = None;

ns = XactNamespace();
dom = None;
if opts.xact:
    try:
        dom = minidom.parse(str(opts.xact));
    except Exception as e:
        logging.error(f"Failed to parse {opts.xact}: {e}");
        sys.exit(1);

if not dom:
    # proper IP-XACT 2014 XML namespaces
    xactns = {
            'xmlns:ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014",
            'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
            'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
            };

    dom = minidom.getDOMImplementation().createDocument(None, None, None);
    comp = dom.createElement(ns.compileTag('component'));
    dom.appendChild(comp);
    #TODO dom = minidom.getDOMImplementation().createDocument(
    #TODO         xactns['xmlns:ipxact'], ns.compileTag('component'), None);
    #TODO comp = dom.documentElement;
    for k,v in xactns.items():
        if k[:5] == 'xmlns:':
            comp.setAttributeNS('',k,v);
        else:
            comp.setAttribute(k,v);

    # default XML element values (unless relevant options defined
    # through CLI options)
    defaults = {'version':'0.0.0', 'name':'manifest'};

    for tag in ['vendor', 'library', 'name', 'version', 'description']:
        e = dom.createElement(ns.compileTag(tag));

        if hasattr(opts,tag) and getattr(opts,tag) is not None:
            text = str(getattr(opts,tag));
        elif tag in defaults:
            text = defaults[tag];
        else:
            text = tag;
        e.appendChild( dom.createTextNode(text) );
        comp.appendChild(e);

if dom:
    comp = dom.documentElement;
    add_mmap(root.top, comp, ns);

    #TODO # printing using minidom formattinf/pretty print
    #TODO sys.stdout.buffer.write( dom.toprettyxml(indent='  ', newl='\n', encoding='UTF-8'));

    # convert from minidom to ElementTree
    # (as minidom pretty print sucks)
    tree = minidom2elementtree(dom);

    # reformat XML
    _pretty_print(tree.getroot());

    # print XML
    if opts.output:
        with open(str(opts.output), 'w') as f:
            tree.write(f, encoding='unicode', xml_declaration=True);
    else:
        tree.write(sys.stdout, encoding='unicode', xml_declaration=True);

