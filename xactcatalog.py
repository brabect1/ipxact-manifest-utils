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

def strip_tag(element: et.Element):
    if element is None:
        return None;
    _, _, tag = element.tag.rpartition('}');
    return tag;


class Vlnv(object):
    
    attrs = ['vendor', 'library', 'name', 'version'];

    def __init__(self, **kwargs):
        for a in Vlnv.attrs:
            if kwargs is not None and a in kwargs:
                setattr(self,a,kwargs[a]);
            else:
                setattr(self,a,None);

    def __str__(self):
        l = [];
        for a in Vlnv.attrs:
            l.append(f'{a}={getattr(self,a)}');
        return ', '.join(l);

    def __eq__(self, other):
        if other is None or not isinstance(other,Vlnv):
            return False;
        else:
            res = True;
            for a in Vlnv.attrs:
                res = res and (getattr(self,a) == getattr(other,a));
            return res;

    def isComplete(self):
        return len([a for a in Vlnv.attrs if getattr(self,a) == None]) == 0;

    def toList(self):
        return [getattr(self,a) for a in Vlnv.attrs];

    def toDict(self):
        return {a: getattr(self,a) for a in Vlnv.attrs};

    @classmethod
    def fromElement(cls, element: et.Element):
        if element is None:
            return None;
    
        vlnv = {};
        for i,tag in enumerate(Vlnv.attrs):
            fulltag = 'ipxact:'+tag;
            value = None;
            for e in element:
                if tag != strip_tag(e):
                    continue;
                else:
                    value = e.text;
                    break;
            if value is None:
                logging.error(f'Missing `{fulltag}` element in {strip_tag(element)}!');
            vlnv[tag] = value;
    
        return Vlnv(**vlnv);


def xact_add_components(tree, files:List[pathlib.Path], outputDir:str = None):
    if tree is None:
        return;

    catalog = tree.getroot();

    trees = [];
    for f in files:
        try:
            tree = et.parse(str(f));
            trees.append([tree,f]);
        except et.ParseError as e:
            logging.error(f"Failed to parse {f}: {e}");

    if len(trees) == 0:
        return;

    ns = XactNamespace();
    components = catalog.find('ipxact:components',XactNamespace.ns);

    elemseq = ['vendor', 'library', 'name', 'version',
            'description', 'catalogs'
            'busDefinitions', 'abstractionDefinitions', 'components',
            'abstractors', 'designs', 'designConfigurations',
            'generatorChains',
            'vendorExtensions'];

    for [comptree,path] in trees:
        comp = comptree.getroot();
        if comp is None or comp.tag != ns.compileTag('component'):
            logging.error(f'Expecting `ipxact:component` root in {path}: {comp.tag}');
            continue;

        vlnv = Vlnv.fromElement(comp);
        logging.debug(f'{path} vlnv: {vlnv}');

        # skip adding a new element if not all VLNV defined
        if not vlnv.isComplete():
            logging.error(f'Missing complete VLNV information in {path}!');
            continue;

        # create new `components` element (if needed)
        if components is None:
            logging.warning(f'No `ipxact:components` element found!');
            components = et.Element(ns.compileTag('components'));
    
            predecesors = elemseq[:elemseq.index('components')];
            inserted = False;
            for i,e in enumerate(catalog):
                tag = strip_tag(e);
                if tag not in predecesors:
                    catalog.insert(i,components);
                    inserted = True;
                    break;
            if not inserted: catalog.append(components);

        # check if component already registered
        comp = None;
        for i,e in enumerate(components):

            # sanity check of the components sub-element type
            tag = strip_tag(e);
            if tag != 'ipxactFile':
                logging.error(f'Unexpected element under `ipxact:components`: {tag}');
                continue;

            # check vlnv
            if vlnv == Vlnv.fromElement(e):
                logging.error(f'Component already regoistered: {path}');
                comp = e;
                break;

        # add new component
        if comp is None:
            comp = et.Element(ns.compileTag('ipxactFile'));
            e = et.Element(ns.compileTag('vlnv'), **vlnv.toDict());
            comp.append(e);
            e = et.Element(ns.compileTag('name'));
            if outputDir:
                e.text = str(path.relative_to(outputDir));
            else:
                e.text = str(path.absolute());
            comp.append(e);
            components.append(comp);

    return;


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
parser.add_argument('--xact-description', dest='description', required=False, type=str, default='mainfest',
        help='IP-XACT catalog/library description.');
parser.add_argument('--rwd', dest='rwd', required=False, type=pathlib.Path,
        help='Relative Working Directory (RWD), which to make file paths relative to. Applies only if `output` not specified.');
parser.add_argument('--log-level', dest='loglevel', required=False, type=str, default='ERROR',
        help='Logging severity, one of: DEBUG, INFO, WARNING, ERROR, FATAL. Defaults to ERROR.');
parser.add_argument('-l', '--log-file', dest='logfile', required=False, type=pathlib.Path, default=None,
        help='Path to a log file. Defaults to stderr if none given.');
parser.add_argument('files', type=pathlib.Path, nargs='+',
        help='List of IP-XACT 2014 component files to be added to the catalog.');

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

    # new root element
    catalog = et.Element(ns.compileTag('catalog'), xactns);

    # default XML element values (unless relevant options defined
    # through CLI options)
    defaults = {'version':'0.0.0', 'name':'manifest'};

    for tag in ['vendor', 'library', 'name', 'version', 'description']:
        e = et.SubElement(catalog, ns.compileTag(tag));

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
    if catalog is None or catalog.tag != ns.compileTag('catalog'):
        logging.error(f'Expecting `ipxact:catalog` root in {opts.xact}: {catalog.tag}');
        sys.exit(1);

    # sanity check for required VLNV elements
    for i,tag in enumerate(['vendor','library','name','version']):
        fulltag = 'ipxact:'+tag;
        elem = catalog.find(fulltag, XactNamespace.ns);
        if elem is None:
            elem = et.Element(ns.compileTag(tag));
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

# add description (if defined)
if opts.description:
    description = catalog.find('ipxact:description', XactNamespace.ns);
    if description is None:
        logging.warning(f'No `ipxact:description` element found in catalog!');
        description = et.Element(ns.compileTag('description'));
    
        predecesors = ['vendor','library','name','version'];
        inserted = False;
        for i,e in enumerate(tree.getroot()):
            tag = strip_tag(e);
            if tag not in predecesors:
                tree.getroot().insert(i,description);
                inserted = True;
                break;
        if not inserted: tree.getroot().append(description);

    description.text = opts.description;

# add new IP-XACT view
xact_add_components( tree, opts.files, outputDir );

# reformat XML
_pretty_print(tree.getroot());

# print XML
if opts.output:
    with open(str(opts.output), 'w') as f:
        tree.write(f, encoding='unicode', xml_declaration=True);
else:
    tree.write(sys.stdout, encoding='unicode', xml_declaration=True);

