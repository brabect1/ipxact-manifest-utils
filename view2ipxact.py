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

def xact_add_view(tree, viewname:str, files:List[pathlib.Path], outputDir:str = None):
    if tree is None:
        return;

    ns = {'ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014"};
    comp = tree.getroot();
    if comp is None or comp.tag != get_tag('component', ns['ipxact']):
        logging.error(f'Expecting `ipxact:component` root in {opts.xact}: {comp.tag}');
        return;

    compinstname = viewname + '_implementation';
    filesetname = viewname + '_files';

    model = comp.find('ipxact:model',ns);
    views = comp.find('ipxact:model/ipxact:views',ns);
    insts = comp.find('ipxact:model/ipxact:instantiations',ns);
    filesets = comp.find('ipxact:fileSets',ns);

    # sanity check that the new view does not exit yet
    if views is not None:
        names = views.findall('ipxact:view/ipxact:name',ns);
        for e in names:
            if e.text == viewname:
                logging.error(f'View `{viewname}` already exists!');
                return;

    # sanity check that the new componentInstantiation does not exit yet
    if insts is not None:
        names = insts.findall('ipxact:componentInstantiation/ipxact:name',ns);
        for e in names:
            if e.text == compinstname:
                logging.error(f'Component instantiation `{compinstname}` already exists!');
                return;

    # sanity check that the new fileset does not exit yet
    if filesets is not None:
        names = filesets.findall('ipxact:fileset/ipxact:name',ns);
        for e in names:
            if e.text == filesetname:
                logging.error(f'File set `{filesetname}` already exists!');
                return;

    elemseq = ['vendor', 'library', 'name', 'version',
            'busInterfaces', 'indirectInterfaces', 'channels',
            'remapStates', 'addressSpaces', 'memoryMaps',
            'model', 'componentGenerators', 'choices',
            'fileSets', 'whiteboxElements', 'cpus',
            'otherClockDrivers', 'resetTypes', 'description',
            'parameters', 'assertions', 'vendorExtensions'];

    # create new model (if needed)
    if model is None:
        logging.warning(f'No `ipxact:model` element found!');
        model = et.Element('ipxact:model');

        predecesors = elemseq[:elemseq.index('model')];
        inserted = False;
        for i,e in enumerate(comp):
            _, _, tag = e.tag.rpartition('}');
            if tag not in predecesors:
                comp.insert(i,model);
                inserted = True;
                break;
        if not inserted: comp.append(model);

    # create new views element (if needed)
    if views is None:
        logging.warning(f'No `ipxact:views` element found!');
        views = et.Element('ipxact:views');

        # `views` is the 1st element under `model`
        model.insert(0,views);

    # create new view element
    view = et.SubElement(views, 'ipxact:view');
    e = et.Element('ipxact:name');
    e.text = viewname;
    view.append(e);
    e = et.Element('ipxact:componentInstantiationRef');
    e.text = compinstname;
    view.append(e);

    # create new instantiations element (if needed)
    if insts is None:
        logging.warning(f'No `ipxact:instantiations` element found!');
        views = et.Element('ipxact:instantiations');

        # `instantiations` is the 2nd element under `model`
        model.insert(1,views);

    # create new component instantiation element
    compinst = et.SubElement(insts, 'ipxact:componentInstantiation');
    e = et.Element('ipxact:name');
    e.text = compinstname;
    compinst.append(e);
    e = et.Element('ipxact:fileSetRef');
    compinst.append(e);
    e = et.Element('ipxact:localName');
    e.text = filesetname;
    compinst[-1].append(e);

    # create new filesets element (if needed)
    if filesets is None:
        logging.warning(f'No `ipxact:filesets` element found!');
        filesets = et.Element('ipxact:fileSets');

        predecesors = elemseq[:elemseq.index('fileSets')];
        inserted = False;
        for i,e in enumerate(comp):
            _, _, tag = e.tag.rpartition('}');
            if tag not in predecesors:
                comp.insert(i,filesets);
                inserted = True;
                break;
        if not inserted: comp.append(filesets);

    # create new fileset element
    fileset = et.SubElement(filesets,'ipxact:fileSet');
    e = et.Element('ipxact:name');
    e.text = filesetname;
    fileset.append(e);
    e = et.Element('ipxact:localName');
    e.text = filesetname;
    for f in files:
        fileSetFile = et.SubElement(fileset, 'ipxact:file');
        e = et.SubElement(fileSetFile, 'ipxact:name');

        if outputDir:
            e.text = str(f.relative_to(outputDir));
        else:
            e.text = str(f.absolute());

        e = et.SubElement(fileSetFile, 'ipxact:fileType');
        e.text = 'unknown';

    return;

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
parser.add_argument('-n', '--view-name', dest='viewname', required=True, type=str,
        help='IP view name.');
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

tree = None;
if opts.xact:
    try:
        tree = et.parse(str(opts.xact));
    except et.ParseError as e:
        logging.error(f"Failed to parse {opts.xact}: {e}");
        sys.exit(1);

if not tree:
    # proper IP-XACT 2014 XML namespaces
    xactns = {'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
    'xmlns:ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014",
    'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
    };

    comp = et.Element('ipxact:component', xactns);

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
    if comp is None or comp.tag != get_tag('component', ns['ipxact']):
        logging.error(f'Expecting `ipxact:component` root in {opts.xact}: {comp.tag}');
        sys.exit(1);

    # sanity check for required VLNV elements
    for i,tag in enumerate(['vendor','library','name','version']):
        fulltag = 'ipxact:'+tag;
        elem = comp.find(fulltag, ns);
        if elem is None:
            elem = et.Element(fulltag);
            comp.insert(i,elem);
            if hasattr(opts,tag) and getattr(opts,tag) is not None:
                logging.warning(f'Missing `{fulltag}` element in {opts.xact}!');
                elem.text = getattr(opts,tag);
            else:
                logging.error(f'Missing `{fulltag}` element in {opts.xact}!');
                elem.text = tag;
        elif hasattr(opts,tag):
            attr = getattr(opts,tag);
            if attr is not None and attr != elem.text:
                logging.error(f'User `{fulltag}` element `{attr}` not match `{elem.text}` in {opts.xact}');

    tree = et.ElementTree(comp);

# add new IP-XACT view
xact_add_view( tree, opts.viewname, opts.files, outputDir );
#TODO sys.exit(0);

# reformat XML
_pretty_print(tree.getroot());

# print XML
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

