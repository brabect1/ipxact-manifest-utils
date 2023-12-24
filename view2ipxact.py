# Copyright 2023 Tomas Brabec
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import pathlib
import anytree
import logging
import argparse
import xml.etree.ElementTree as et
from typing import Iterable, Optional, List

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


def get_tag(tag: str, ns_uri: str = None):
    if ns_uri:
        return f'{{{ns_uri}}}{tag}';
    else:
        return tag;

#TODO # Declaring own SyntaxTree iterator that can search only
#TODO # within a certain depth of the tree.
#TODO class PreOrderDepthTreeIterator(verible_verilog_syntax._TreeIteratorBase):
#TODO   def __init__(self, tree: "Node",
#TODO                filter_: Optional[verible_verilog_syntax.CallableFilter] = None,
#TODO                reverse_children: bool = False,
#TODO                depth: int = -1):
#TODO     self.tree = tree
#TODO     self.reverse_children = reverse_children
#TODO     self.filter_ = filter_ if filter_ else lambda n: True
#TODO     self.depth = depth
#TODO 
#TODO   def _iter_tree_depth(self, tree: Optional["Node"], depth=-1) -> Iterable["Node"]:
#TODO     if self.filter_(tree):
#TODO       yield tree
#TODO     elif depth < 0 or depth > 0:
#TODO       if depth > 0: depth -= 1;
#TODO       for child in self._iter_children(tree):
#TODO         yield from self._iter_tree_depth(child,depth)
#TODO 
#TODO   def _iter_tree(self, tree: Optional["Node"]) -> Iterable["Node"]:
#TODO     yield from self._iter_tree_depth(tree, self.depth)


#TODO def node_depth(node: anytree.Node):
#TODO     if not node:
#TODO         return -1;
#TODO     cnt = 0;
#TODO     p = node.parent;
#TODO     while p is not None:
#TODO         cnt += 1;
#TODO         p = p.parent;
#TODO     return cnt;

parser = argparse.ArgumentParser(description='Adds IP view into IP-XACT 2014.');
parser.add_argument('-o', '--output', dest='output', required=False, type=pathlib.Path,
        help='IP-XACT output file, stdout if not given.');
#TODO parser.add_argument('-m', '--module', dest='module', required=False, type=str,
#TODO         help='Name of the root module.');
parser.add_argument('--xact', dest='xact', required=False, type=pathlib.Path,
        help='IP-XACT 2014 to be updated with view information.')
parser.add_argument('--xact-library', dest='library', required=False, type=str,
        help='IP-XACT component library name.');
parser.add_argument('--xact-version', dest='version', required=False, type=str,
        help='IP-XACT component version number.');
parser.add_argument('--xact-vendor', dest='vendor', required=False, type=str,
        help='IP-XACT component vendor name.');
parser.add_argument('--rwd', dest='rwd', required=False, type=pathlib.Path,
        help='Relative Working Directory (RWD), which to make file paths relative to. Applies only if `output` not specified.');
parser.add_argument('files', type=pathlib.Path, nargs='+',
        help='List of files in the view.');

# parse CLI options
opts = parser.parse_args();

# setup logging level
logging.basicConfig(level=logging.DEBUG);

# input files
file_paths = [str(f) for f in opts.files];

# output directory
# (`None` means to use absolute paths)
if opts.output:
    outputDir = str(opts.output.parent);
elif opts.rwd:
    outputDir = str(opts.rwd);
else:
    outputDir = None;

# IP-XACT  2014 namespace
ns = {'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
'xmlns:ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014",
'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
};

for p,u in ns.items():
    if p[:len('xmlns:')] == 'xmlns:':
        n = p[len('xmlns:'):];
        logging.debug(f"registering namespace {n}:{u}");
        et.register_namespace(n, u);

tree = None;
if opts.xact:
    try:
        tree = et.parse(str(opts.xact));
    except et.ParseError as e:
        logging.error(f"Failed to parse {opts.xact}: {e}");
        sys.exit(1);

if not tree:
    comp = et.Element('ipxact:component', ns);

    vendor = et.SubElement(comp, 'ipxact:vendor');
    library = et.SubElement(comp, 'ipxact:library');
    name = et.SubElement(comp, 'ipxact:name');
    version = et.SubElement(comp, 'ipxact:version');

    if opts.vendor:
        vendor.text = opts.vendor;
    else:
        vendor.text = 'vendor';

    if opts.library:
        library.text = opts.library;
    else:
        library.text = 'library';

    if hasattr(opts,'nanme') and opts.name:
        name.text = opts.name;
    else:
        name.text = 'name';

    if opts.version:
        version.text = opts.version;
    else:
        version.text = '0.0.0';

    tree = et.ElementTree(comp);
else:
    # test if root is an ipxact component
    comp = tree.getroot();
    if comp is None or comp.tag != get_tag('component', ns['xmlns:ipxact']):
        logging.error(f'Expecting `ipxact:component` root in {opts.xact}: {comp.tag}');
        sys.exit(1);

#    # sanity check: vendor
#    vendor = comp.find('vendor',ns);
#    if not vendor:
#        vendor = et.SubElement(comp, 'ipxact:vendor');
#        if opts.vendor:
#            logging.warning(f'Missing `ipxact:vendor` element in {opts.xact}!');
#            vendor.text = opts.vendor;
#        else:
#            logging.error(f'Missing `ipxact:vendor` element in {opts.xact}!');
#            vendor.text = 'vendor';
#    elif opts.vendor and opts.vendor != vendor.text:
#        logging.error(f'User `ipxact:vendor` element `{opts.vendor}` not match `{vendor.text}` in {opts.xact}');
#
#    # sanity check: library
#    library = comp.find('library',ns);
#    if not library:
#        library = et.SubElement(comp, 'ipxact:library');
#        if opts.library:
#            logging.warning(f'Missing `ipxact:library` element in {opts.xact}!');
#            library.text = opts.library;
#        else:
#            logging.error(f'Missing `ipxact:library` element in {opts.xact}!');
#            library.text = 'library';
#    elif opts.library and opts.library != library.text:
#        logging.error(f'User `ipxact:library` element `{opts.library}` not match `{library.text}` in {opts.xact}');
#
#    # sanity check: name
#    name = comp.find('name',ns);
#    if not name:
#        name = et.SubElement(comp, 'ipxact:name');
#        if hasattr(opts,'name') and opts.name:
#            logging.warning(f'Missing `ipxact:name` element in {opts.xact}!');
#            name.text = opts.name;
#        else:
#            logging.error(f'Missing `ipxact:name` element in {opts.xact}!');
#            name.text = opts.xact.name;
#            sl = opts.xact.suffixes;
#            if sl is not None and len(sl) > 0:
#                name.text = name.text[:-len(''.join(sl))];
#    elif hasattr(opts,'name') and opts.name and opts.name != name.text:
#        logging.error(f'User `ipxact:name` element `{opts.name}` not match `{name.text}` in {opts.xact}');
#
#    # sanity check: version
#    version = comp.find('version',ns);
#    if not version:
#        version = et.SubElement(comp, 'ipxact:version');
#        if opts.version:
#            logging.warning(f'Missing `ipxact:version` element in {opts.xact}!');
#            version.text = opts.version;
#        else:
#            logging.error(f'Missing `ipxact:version` element in {opts.xact}!');
#            version.text = '0.0.0';
#    elif opts.version and opts.version != version.text:
#        logging.error(f'User `ipxact:version` element `{opts.version}` not match `{version.text}` in {opts.xact}');

#_pretty_print(tree.getroot());

if opts.output:
    with open(str(opts.output), 'w') as f:
        tree.write(f, encoding='unicode', xml_declaration=True);
else:
    tree.write(sys.stdout, encoding='unicode', xml_declaration=True);

#TODO if len(modules) > 0:
#TODO     ns = {'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
#TODO     'xmlns:ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014",
#TODO     'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
#TODO     };
#TODO 
#TODO     module = None;
#TODO     if opts.module:
#TODO         for m in modules:
#TODO             if m['name'] == opts.module:
#TODO                 module = m;
#TODO                 break;
#TODO         if not module:
#TODO             logging.error(f'Failed to find module \'{opts.module}\'!');
#TODO             sys.exit(1);
#TODO     else:
#TODO         # use the first root module
#TODO         roots = [m for m in modules if m['is_root']];
#TODO         module = roots[0];
#TODO 
#TODO     print(anytree.RenderTree( get_module_hierarchy(modules, module['name']) ));
#TODO 
#TODO     comp = et.Element('ipxact:component', ns);
#TODO 
#TODO     vendor = et.SubElement(comp, 'ipxact:vendor');
#TODO     library = et.SubElement(comp, 'ipxact:library');
#TODO     name = et.SubElement(comp, 'ipxact:name');
#TODO     version = et.SubElement(comp, 'ipxact:version');
#TODO 
#TODO     if opts.vendor:
#TODO         vendor.text = opts.vendor;
#TODO     else:
#TODO         vendor.text = 'vendor';
#TODO 
#TODO     if opts.library:
#TODO         library.text = opts.library;
#TODO     else:
#TODO         library.text = 'library';
#TODO 
#TODO     name.text = module['name'];
#TODO 
#TODO     if opts.version:
#TODO         version.text = opts.version;
#TODO     else:
#TODO         version.text = '1.0.0';
#TODO 
#TODO     model = et.SubElement(comp, 'ipxact:model');
#TODO 
#TODO     views = et.SubElement(model, 'ipxact:views');
#TODO 
#TODO     rtlView = et.SubElement(views, 'ipxact:view');
#TODO     viewName = et.SubElement(rtlView, 'ipxact:name');
#TODO     viewName.text = 'rtl';
#TODO     compInstRef = et.SubElement(rtlView, 'ipxact:componentInstantiationRef');
#TODO     compInstRef.text = viewName.text + '_implementation';
#TODO 
#TODO     insts = et.SubElement(model, 'ipxact:instantiations');
#TODO     compInst = et.SubElement(insts, 'ipxact:componentInstantiation');
#TODO     instName = et.SubElement(compInst, 'ipxact:name');
#TODO     instName.text = compInstRef.text;
#TODO 
#TODO     if 'parameters' in module:
#TODO         params  = et.SubElement(compInst, 'ipxact:moduleParameters');
#TODO         for param in module['parameters']:
#TODO             params.append( param.etXact() );
#TODO 
#TODO     instFileSetRef = et.SubElement(compInst, 'ipxact:fileSetRef');
#TODO     instFileSetRef = et.SubElement(instFileSetRef, 'ipxact:localName');
#TODO     instFileSetRef.text = viewName.text + '_files';
#TODO 
#TODO     if 'ports' in module:
#TODO         ports  = et.SubElement(model, 'ipxact:ports');
#TODO         for port in module['ports']:
#TODO             ports.append( port.etXact() );
#TODO 
#TODO     fileSets = et.SubElement(comp, 'ipxact:fileSets');
#TODO     fileSet = et.SubElement(fileSets, 'ipxact:fileSet');
#TODO     fileSetName = et.SubElement(fileSet, 'ipxact:name');
#TODO     fileSetName.text = instFileSetRef.text;
#TODO 
#TODO     for p in get_files_in_hierarchy(modules, module['name']):
#TODO         f = pathlib.Path(p);
#TODO         fileSetFile = et.SubElement(fileSet, 'ipxact:file');
#TODO         fileSetFileName = et.SubElement(fileSetFile, 'ipxact:name');
#TODO 
#TODO         if outputDir:
#TODO             fileSetFileName.text = str(f.relative_to(outputDir));
#TODO         else:
#TODO             fileSetFileName.text = str(f.absolute());
#TODO 
#TODO         fileSetFileType = et.SubElement(fileSetFile, 'ipxact:fileType');
#TODO         fileExt = f.suffix;
#TODO         if fileExt:
#TODO             if fileExt == 'v' or fileExt == 'vh':
#TODO                 fileSetFileType.text = 'verilogSource';
#TODO             else:
#TODO                 fileSetFileType.text = 'systemVerilogSource';
#TODO         else:
#TODO             fileSetFileType.text = 'systemVerilogSource';
#TODO 
#TODO     _pretty_print(comp);
#TODO     tree = et.ElementTree(comp);
#TODO     #et.indent(tree, space="\t", level=0);
#TODO     #et.dump(tree);
#TODO 
#TODO     if opts.output:
#TODO         with open(str(opts.output), 'w') as f:
#TODO             tree.write(f, encoding='unicode', xml_declaration=True);
#TODO     else:
#TODO         tree.write(sys.stdout, encoding='unicode', xml_declaration=True);

