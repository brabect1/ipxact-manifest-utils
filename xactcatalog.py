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

def xact_add_components(tree, files:List[pathlib.Path], outputDir:str = None):
    if tree is None:
        return;

    trees = [];
    for f in files:
        try:
            tree = et.parse(str(f));
            trees.append([tree,f]);
        except et.ParseError as e:
            logging.error(f"Failed to parse {opts.xact}: {e}");

    ns = {'ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014"};
    for [tree,path] in trees:
        comp = tree.getroot();
        if comp is None or comp.tag != get_tag('component', ns['ipxact']):
            logging.error(f'Expecting `ipxact:component` root in {path}: {comp.tag}');
            continue;

    pass; #TODO
#TODO
#TODO    compinstname = viewname + '_implementation';
#TODO    filesetname = viewname + '_files';
#TODO
#TODO    model = comp.find('ipxact:model',ns);
#TODO    views = comp.find('ipxact:model/ipxact:views',ns);
#TODO    insts = comp.find('ipxact:model/ipxact:instantiations',ns);
#TODO    filesets = comp.find('ipxact:fileSets',ns);
#TODO
#TODO    # sanity check that the new view does not exit yet
#TODO    if views is not None:
#TODO        names = views.findall('ipxact:view/ipxact:name',ns);
#TODO        for e in names:
#TODO            if e.text == viewname:
#TODO                logging.error(f'View `{viewname}` already exists!');
#TODO                return;
#TODO
#TODO    # sanity check that the new componentInstantiation does not exit yet
#TODO    if insts is not None:
#TODO        names = insts.findall('ipxact:componentInstantiation/ipxact:name',ns);
#TODO        for e in names:
#TODO            if e.text == compinstname:
#TODO                logging.error(f'Component instantiation `{compinstname}` already exists!');
#TODO                return;
#TODO
#TODO    # sanity check that the new fileset does not exit yet
#TODO    if filesets is not None:
#TODO        names = filesets.findall('ipxact:fileset/ipxact:name',ns);
#TODO        for e in names:
#TODO            if e.text == filesetname:
#TODO                logging.error(f'File set `{filesetname}` already exists!');
#TODO                return;
#TODO
#TODO    elemseq = ['vendor', 'library', 'name', 'version',
#TODO            'busInterfaces', 'indirectInterfaces', 'channels',
#TODO            'remapStates', 'addressSpaces', 'memoryMaps',
#TODO            'model', 'componentGenerators', 'choices',
#TODO            'fileSets', 'whiteboxElements', 'cpus',
#TODO            'otherClockDrivers', 'resetTypes', 'description',
#TODO            'parameters', 'assertions', 'vendorExtensions'];
#TODO
#TODO    # create new model (if needed)
#TODO    if model is None:
#TODO        logging.warning(f'No `ipxact:model` element found!');
#TODO        model = et.Element('ipxact:model');
#TODO
#TODO        predecesors = elemseq[:elemseq.index('model')];
#TODO        inserted = False;
#TODO        for i,e in enumerate(comp):
#TODO            _, _, tag = e.tag.rpartition('}');
#TODO            if tag not in predecesors:
#TODO                comp.insert(i,model);
#TODO                inserted = True;
#TODO                break;
#TODO        if not inserted: comp.append(model);
#TODO
#TODO    # create new views element (if needed)
#TODO    if views is None:
#TODO        logging.warning(f'No `ipxact:views` element found!');
#TODO        views = et.Element('ipxact:views');
#TODO
#TODO        # `views` is the 1st element under `model`
#TODO        model.insert(0,views);
#TODO
#TODO    # create new view element
#TODO    view = et.SubElement(views, 'ipxact:view');
#TODO    e = et.Element('ipxact:name');
#TODO    e.text = viewname;
#TODO    view.append(e);
#TODO    e = et.Element('ipxact:componentInstantiationRef');
#TODO    e.text = compinstname;
#TODO    view.append(e);
#TODO
#TODO    # create new instantiations element (if needed)
#TODO    if insts is None:
#TODO        logging.warning(f'No `ipxact:instantiations` element found!');
#TODO        views = et.Element('ipxact:instantiations');
#TODO
#TODO        # `instantiations` is the 2nd element under `model`
#TODO        model.insert(1,views);
#TODO
#TODO    # create new component instantiation element
#TODO    compinst = et.SubElement(insts, 'ipxact:componentInstantiation');
#TODO    e = et.Element('ipxact:name');
#TODO    e.text = compinstname;
#TODO    compinst.append(e);
#TODO    e = et.Element('ipxact:fileSetRef');
#TODO    compinst.append(e);
#TODO    e = et.Element('ipxact:localName');
#TODO    e.text = filesetname;
#TODO    compinst[-1].append(e);
#TODO
#TODO    # create new filesets element (if needed)
#TODO    if filesets is None:
#TODO        logging.warning(f'No `ipxact:filesets` element found!');
#TODO        filesets = et.Element('ipxact:fileSets');
#TODO
#TODO        predecesors = elemseq[:elemseq.index('fileSets')];
#TODO        inserted = False;
#TODO        for i,e in enumerate(comp):
#TODO            _, _, tag = e.tag.rpartition('}');
#TODO            if tag not in predecesors:
#TODO                comp.insert(i,filesets);
#TODO                inserted = True;
#TODO                break;
#TODO        if not inserted: comp.append(filesets);
#TODO
#TODO    # create new fileset element
#TODO    fileset = et.SubElement(filesets,'ipxact:fileSet');
#TODO    e = et.Element('ipxact:name');
#TODO    e.text = filesetname;
#TODO    fileset.append(e);
#TODO    e = et.Element('ipxact:localName');
#TODO    e.text = filesetname;
#TODO    for f in files:
#TODO        fileSetFile = et.SubElement(fileset, 'ipxact:file');
#TODO        e = et.SubElement(fileSetFile, 'ipxact:name');
#TODO
#TODO        if outputDir:
#TODO            e.text = str(f.relative_to(outputDir));
#TODO        else:
#TODO            e.text = str(f.absolute());
#TODO
#TODO        e = et.SubElement(fileSetFile, 'ipxact:fileType');
#TODO        e.text = 'unknown';
#TODO
#TODO    return;


parser = argparse.ArgumentParser(description='Creates or adds to references to IP-XACT 2014 components into IP-XACT 2014 catalog.');
parser.add_argument('-o', '--output', dest='output', required=False, type=pathlib.Path,
        help='IP-XACT output file, stdout if not given.');
#TODO parser.add_argument('-m', '--module', dest='module', required=False, type=str,
#TODO         help='Name of the root module.');
parser.add_argument('--xact', dest='xact', required=False, type=pathlib.Path,
        help='IP-XACT 2014 catalog to be updated with component refereces.')
parser.add_argument('--xact-library', dest='library', required=False, type=str,
        help='IP-XACT catalog library name.');
parser.add_argument('--xact-version', dest='version', required=False, type=str,
        help='IP-XACT catalog version number.');
parser.add_argument('--xact-vendor', dest='vendor', required=False, type=str,
        help='IP-XACT catalog vendor name.');
parser.add_argument('--xact-name', dest='name', required=False, type=str, default='mainfest',
        help='IP-XACT catalog name.');
parser.add_argument('--rwd', dest='rwd', required=False, type=pathlib.Path,
        help='Relative Working Directory (RWD), which to make file paths relative to. Applies only if `output` not specified.');
parser.add_argument('files', type=pathlib.Path, nargs='+',
        help='List of IP-XACT 2014 component files to be added to the catalog.');

# parse CLI options
opts = parser.parse_args();

# setup logging level
logging.basicConfig(level=logging.DEBUG);

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

    # new root element
    catalog = et.Element('ipxact:catalog', xactns);

    # default XML element values (unless relevant options defined
    # through CLI options)
    defaults = {'version':'0.0.0', 'name':'manifest'};

    for tag in ['vendor', 'library', 'name', 'version']:
        e = et.SubElement(catalog, 'ipxact:'+tag);

        if hasattr(opts,tag) and getattr(opts,tag) is not None:
            e.text = str(getattr(opts,tag));
        elif tag in defaults:
            e.text = defaults[tag];
        else:
            e.text = tag;

    tree = et.ElementTree(catalog);

else:
    # test if root is an ipxact component
    catalog = tree.getroot();
    if catalog is None or catalog.tag != get_tag('catalog', ns['ipxact']):
        logging.error(f'Expecting `ipxact:catalog` root in {opts.xact}: {catalog.tag}');
        sys.exit(1);

    # sanity check for required VLNV elements
    for i,tag in enumerate(['vendor','library','name','version']):
        fulltag = 'ipxact:'+tag;
        elem = catalog.find(fulltag, ns);
        if elem is None:
            elem = et.Element(fulltag);
            catalog.insert(i,elem);
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

    tree = et.ElementTree(catalog);

# add new IP-XACT view
xact_add_components( tree, opts.files, outputDir );
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

