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

def xact_add_view(tree, viewname:str, files:List[pathlib.Path], outputDir:str = None):
    if tree is None:
        return;

    ns = XactNamespace();
    comp = tree.getroot();
    if comp is None or comp.tag != ns.compileTag('component'):
        logging.error(f'Expecting `ipxact:component` root in {opts.xact}: {comp.tag}');
        return;

    compinstname = viewname + '_implementation';
    filesetname = viewname + '_files';

    model = comp.find('ipxact:model',XactNamespace.ns);
    views = comp.find('ipxact:model/ipxact:views',XactNamespace.ns);
    insts = comp.find('ipxact:model/ipxact:instantiations',XactNamespace.ns);
    filesets = comp.find('ipxact:fileSets',XactNamespace.ns);

    # sanity check that the new view does not exit yet
    if views is not None:
        names = views.findall('ipxact:view/ipxact:name',XactNamespace.ns);
        for e in names:
            if e.text == viewname:
                logging.error(f'View `{viewname}` already exists!');
                return;

    # sanity check that the new componentInstantiation does not exit yet
    if insts is not None:
        names = insts.findall('ipxact:componentInstantiation/ipxact:name',XactNamespace.ns);
        for e in names:
            if e.text == compinstname:
                logging.error(f'Component instantiation `{compinstname}` already exists!');
                return;

    # sanity check that the new fileset does not exit yet
    if filesets is not None:
        names = filesets.findall('ipxact:fileset/ipxact:name',XactNamespace.ns);
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
        model = et.Element(ns.compileTag('model'));

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
        views = et.Element(ns.compileTag('views'));

        # `views` is the 1st element under `model`
        model.insert(0,views);

    # create new view element
    view = et.SubElement(views, ns.compileTag('view'));
    e = et.Element(ns.compileTag('name'));
    e.text = viewname;
    view.append(e);
    e = et.Element(ns.compileTag('componentInstantiationRef'));
    e.text = compinstname;
    view.append(e);

    # create new instantiations element (if needed)
    if insts is None:
        logging.warning(f'No `ipxact:instantiations` element found!');
        insts = et.Element(ns.compileTag('instantiations'));

        # `instantiations` is the 2nd element under `model`
        model.insert(1,insts);

    # create new component instantiation element
    compinst = et.SubElement(insts, ns.compileTag('componentInstantiation'));
    e = et.Element(ns.compileTag('name'));
    e.text = compinstname;
    compinst.append(e);
    e = et.Element(ns.compileTag('fileSetRef'));
    compinst.append(e);
    e = et.Element(ns.compileTag('localName'));
    e.text = filesetname;
    compinst[-1].append(e);

    # create new filesets element (if needed)
    if filesets is None:
        logging.warning(f'No `ipxact:filesets` element found!');
        filesets = et.Element(ns.compileTag('fileSets'));

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
    fileset = et.SubElement(filesets,ns.compileTag('fileSet'));
    e = et.Element(ns.compileTag('name'));
    e.text = filesetname;
    fileset.append(e);
    e = et.Element(ns.compileTag('localName'));
    e.text = filesetname;
    for f in files:
        fileSetFile = et.SubElement(fileset, ns.compileTag('file'));
        e = et.SubElement(fileSetFile, ns.compileTag('name'));

        if outputDir:
            e.text = str(f.relative_to(outputDir));
        else:
            e.text = str(f.absolute());

        e = et.SubElement(fileSetFile, ns.compileTag('fileType'));
        e.text = 'unknown';

    return;

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

ns = XactNamespace();
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
    'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
    };

    comp = et.Element(ns.compileTag('component'), xactns);

    # default XML element values (unless relevant options defined
    # through CLI options)
    defaults = {'version':'0.0.0', 'name':'manifest'};

    for tag in ['vendor', 'library', 'name', 'version', 'description']:
        e = et.SubElement(comp, ns.compileTag(tag));

        if hasattr(opts,tag) and getattr(opts,tag) is not None:
            e.text = str(getattr(opts,tag));
        elif tag in defaults:
            e.text = defaults[tag];
        else:
            e.text = tag;

    tree = et.ElementTree(comp);

else:
    # test if root is an ipxact component
    comp = tree.getroot();
    if comp is None or comp.tag != ns.compileTag('component'):
        logging.error(f'Expecting `ipxact:component` root in {opts.xact}: {comp.tag}');
        sys.exit(1);

    # sanity check for required VLNV elements
    for i,tag in enumerate(['vendor','library','name','version']):
        fulltag = 'ipxact:'+tag;
        elem = comp.find(fulltag, XactNamespace.ns);
        if elem is None:
            elem = et.Element(ns.compileTag(tag));
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

# reformat XML
_pretty_print(tree.getroot());

# print XML
if opts.output:
    with open(str(opts.output), 'w') as f:
        tree.write(f, encoding='unicode', xml_declaration=True);
else:
    tree.write(sys.stdout, encoding='unicode', xml_declaration=True);

