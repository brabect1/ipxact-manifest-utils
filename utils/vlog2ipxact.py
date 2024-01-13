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
import verible_verilog_syntax
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

# Declaring own SyntaxTree iterator that can search only
# within a certain depth of the tree.
class PreOrderDepthTreeIterator(verible_verilog_syntax._TreeIteratorBase):
  def __init__(self, tree: "Node",
               filter_: Optional[verible_verilog_syntax.CallableFilter] = None,
               reverse_children: bool = False,
               depth: int = -1):
    self.tree = tree
    self.reverse_children = reverse_children
    self.filter_ = filter_ if filter_ else lambda n: True
    self.depth = depth

  def _iter_tree_depth(self, tree: Optional["Node"], depth=-1) -> Iterable["Node"]:
    if self.filter_(tree):
      yield tree
    elif depth < 0 or depth > 0:
      if depth > 0: depth -= 1;
      for child in self._iter_children(tree):
        yield from self._iter_tree_depth(child,depth)

  def _iter_tree(self, tree: Optional["Node"]) -> Iterable["Node"]:
    yield from self._iter_tree_depth(tree, self.depth)


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


class TypeDimension(object):

    def __init__(self, left, right):
        self.left = left;
        self.right = right;

    def __str__(self):
        return '['+str(self.left)+':'+str(self.right)+']';

    def etXact(self):
        vector = et.Element('ipxact:vector');
        left = et.SubElement(vector, 'ipxact:left');
        left.text = self.left;
        right = et.SubElement(vector, 'ipxact:right');
        right.text = self.right;
        return vector;


class Port(object):

    attrs = ['direction', 'datatype', 'dimensions', 'name'];

    lutDirection = {'input': 'in', 'output': 'out', 'inout': 'inout'};

    def __init__(self, name, **kwargs):
        self.name = name;

        for attr in Port.attrs:
            if hasattr(self,attr):
                continue;

            if attr in kwargs:
                setattr(self,attr,kwargs[attr]);
            else:
                setattr(self,attr,None);

        if self.direction is None:
            self.direction = 'input';

    def __str__(self):
        attrs = [];
        for attr in Port.attrs:
            val = getattr(self,attr);
            if val:
                # dimensions need to be treated specifically as it is
                # a list of `TypeDimension` instances
                if attr=='dimensions':
                    attrs.append(''.join([str(d) for d in val]));
                else:
                    attrs.append(val);

        return ' '.join(attrs);

    def etXact(self):
        ns = XactNamespace();
        p = et.Element(ns.compileTag('port'));

        name = et.SubElement(p, ns.compileTag('name'));
        name.text = self.name;

        signal = et.SubElement(p, ns.compileTag('wire'));

        direction = et.SubElement(signal, ns.compileTag('direction'));
        if self.direction in Port.lutDirection:
            direction.text = Port.lutDirection[self.direction];
        else:
            #TODO report error/warning
            direction.text = Port.lutDirection['input'];

        if self.dimensions and len(self.dimensions) > 0:
            vectors= et.SubElement(signal, ns.compileTag('vectors'));
            for dimension in self.dimensions:
                vectors.append(dimension.etXact());

        if self.datatype:
            wiredefs = et.SubElement(signal, ns.compileTag('wireTypeDefs'));
            wiredef = et.SubElement(wiredefs, ns.compileTag('wireTypeDef'));
            typename = et.SubElement(wiredef, ns.compileTag('typeName'));
            typename.text = self.datatype;

        return p;

    def toDict(self):
        d = {'name': self.name};

        if self.direction in Port.lutDirection:
            d['dir'] = Port.lutDirection[self.direction];
        else:
            #TODO report error/warning
            d['dir'] = Port.lutDirection['input'];

        if self.datatype:
            d['type'] = self.datatype;
        else:
            d['type'] = None;

        if self.dimensions and len(self.dimensions) > 0:
            d['dimensions'] = [];
            for dimension in self.dimensions:
                d['dimensions'].append([dimension.left,dimension.right]);

        return d;


class Parameter(object):

    attrs = ['datatype', 'dimensions', 'name', 'value'];

    def __init__(self, name, **kwargs):
        self.name = name;

        for attr in Parameter.attrs:
            if hasattr(self,attr):
                continue;

            if attr in kwargs:
                setattr(self,attr,kwargs[attr]);
            else:
                setattr(self,attr,None);

    def __str__(self):
        attrs = [];
        for attr in Parameter.attrs:
            val = getattr(self,attr);
            if val:
                # dimensions need to be treated specifically as it is
                # a list of `TypeDimension` instances
                if attr=='dimensions':
                    attrs.append(''.join([str(d) for d in val]));
                elif attr=='value':
                    attrs.append('=');
                    attrs.append(val);
                else:
                    attrs.append(val);

        return ' '.join(attrs);

    def etXact(self, elementTag='moduleParameter'):
        ns = XactNamespace();
        p = et.Element(ns.compileTag(elementTag));

        name = et.SubElement(p, ns.compileTag('name'));
        name.text = self.name;

        value = et.SubElement(p, ns.compileTag('value'));
        if hasattr(self,'value') and self.value:
            value.text = str(self.value);
        else:
            # use the parameter name as "symolic" value
            value.text = self.name;

        if self.datatype:
            p.set('dataType', self.datatype);

        return p;


def get_dimensions(data: verible_verilog_syntax.SyntaxData, dimensions = None):
    if data is not None:
        for portDimensions in data.iter_find_all({'tag': ['kDeclarationDimensions']}):
            #print(anytree.RenderTree(portDimensions));
            if dimensions is None: dimensions = [];
            portDimensions = portDimensions.find_all({'tag': ['kDimensionRange','kDimensionScalar']});
            for portDimension in portDimensions:
                if portDimension.tag == 'kDimensionRange':
                    dimensionRange = portDimension.find_all({'tag':['kExpression']}, iter_ = PreOrderDepthTreeIterator, depth=1);
                    left = dimensionRange[0].text;
                    right = dimensionRange[1].text;
                    dimensions.append( TypeDimension(left,right) );
                elif portDimension.tag == 'kDimensionScalar':
                    size = portDimension.find({'tag':['kExpressionList']});
                    if size:
                        dimensions.append( TypeDimension('0',size.text+'-1') );

    return dimensions


def get_instances(module_data: verible_verilog_syntax.SyntaxData):
    insts = None;
    for inst in module_data.iter_find_all({"tag": ["kInstantiationBase"]}):
        instname = inst.find({"tag": ["kGateInstance"]});
        if not instname: continue;

        insttype = inst.find({"tag": ["kInstantiationType"]});
        if insttype:
            modulename = insttype.find({"tag": ["kUnqualifiedId"]});
            if not modulename: continue;

            if len(modulename.children) > 0 and hasattr(modulename.children[0],'tag') and modulename.children[0].tag == 'SymbolIdentifier':
                name = modulename.children[0].text;
                if not insts: insts = [];
                insts.append(name);

    return insts;

def get_parameters(module_data: verible_verilog_syntax.SyntaxData):
    params = [];

    paramlist = module_data.find({"tag": ["kFormalParameterList"]});
    if not paramlist:
        return params;

    lastParamDecl = None;
    for param in paramlist.iter_find_all({"tag": ["kParamDeclaration"]}):
        if param.tag == 'kParamDeclaration':
            lastParamDecl = param;

        name = param.find({"tag": ["kUnqualifiedId", "SymbolIdentifier", "EscapedIdentifier"]});
        if name:
            name = name.text;
        else:
            name = 'undefined_port';

        dimensions = None;
        datatype = None;
        value = None;

        if lastParamDecl:
            for paramDimensions in lastParamDecl.iter_find_all({'tag': ['kDeclarationDimensions']}):
                if dimensions is None: dimensions = [];
                paramDimensions = paramDimensions.find_all({'tag': ['kDimensionRange','kDimensionScalar']});
                for paramDimension in paramDimensions:
                    if paramDimension.tag == 'kDimensionRange':
                        dimensionRange = paramDimension.find_all({'tag':['kExpression']}, iter_ = PreOrderDepthTreeIterator, depth=1);
                        left = dimensionRange[0].text;
                        right = dimensionRange[1].text;
                        dimensions.append( TypeDimension(left,right) );
                    elif paramDimension.tag == 'kDimensionScalar':
                        size = paramDimension.find({'tag':['kExpressionList']});
                        if size:
                            dimensions.append( TypeDimension('0',size.text+'-1') );

            datatype = lastParamDecl.find({'tag': ['kTypeInfo']});
            if datatype:
                datatype = datatype.text;
                if len(datatype) == 0:
                    datatype = None;
            else:
                if hasattr(lastParamDecl.children[1], 'tag'):
                    datatype = lastParamDecl.children[1].text;
                else:
                    datatype = None;

            value = lastParamDecl.find({'tag': ['kTrailingAssign']});
            if value:
                value = value.find({'tag': ['kExpression']});
                if value:
                    value = value.text;

        #TODO print(anytree.RenderTree(param));
        #TODO print(param.children[0]);
        params.append( Parameter(name, datatype=datatype, dimensions=dimensions, value=value) );

    return params;


def get_ports(module_data: verible_verilog_syntax.SyntaxData):
    ports = [];

    # in Verilog syntax, port direction and type are defined outside
    # module port list. In Verible CST, this information is contained
    # within a 'kModuleItemList' node.
    portDeclarations = {};
    moduleItems = module_data.find({'tag':['kModuleItemList']});
    if moduleItems:
        for decl in moduleItems.iter_find_all({'tag': ['kModulePortDeclaration', 'kNetDeclaration', 'kDataDeclaration']}):
            for name in decl.iter_find_all({"tag": ["SymbolIdentifier", "EscapedIdentifier"]}):
                name = name.text;

                if name in portDeclarations:
                    dimensions,direction,datatype = portDeclarations[name];
                else:
                    dimensions = None;
                    direction = None;
                    datatype = None;

                if decl.tag == 'kModulePortDeclaration':
                    direction = decl.children[0].text;

                if datatype is None:
                    datatype = decl.find({'tag': ['kDataType']});
                    if datatype and len(datatype.children) > 0:
                        primitivetype = decl.find({'tag': ['kDataTypePrimitive']});
                        if primitivetype:
                            datatype = primitivetype.text;
                        else:
                            if datatype.text:
                                datatype = datatype.text;
                            else:
                                datatype = None;

                if dimensions is None:
                    dimensions = get_dimensions(decl,dimensions);

                portDeclarations[name] = [dimensions,direction,datatype];

    lastPortDecl = None;
    for port in module_data.iter_find_all({"tag": ["kPortDeclaration", "kPort"]}):
        if port.tag == 'kPortDeclaration':
            lastPortDecl = port;

        name = port.find({"tag": ["SymbolIdentifier", "EscapedIdentifier"]});
        if name:
            name = name.text;
        else:
            name = 'undefined_port';

        dimensions = None;
        direction = 'input ';
        datatype = None;

        if lastPortDecl:

            # get unpacked dimensions first
            if port.tag != 'kPortDeclaration':
                # when the tree node is a 'kPort', then it may have port-specific
                # unpacked dimensions
                dimensions = get_dimensions(port,dimensions);
            elif port.tag == 'kPortDeclaration':
                for unpackedDimensions in port.iter_find_all({'tag': ['kUnpackedDimensions']}):
                    dimensions = get_dimensions(unpackedDimensions,dimensions);
            else:
                raise NotImplementedError('unexpected case');

            # add packed dimensions from the port declaration
            for packedDimensions in lastPortDecl.iter_find_all({'tag': ['kPackedDimensions']}):
                dimensions = get_dimensions(packedDimensions,dimensions);

            datatype = lastPortDecl.find({'tag': ['kDataTypePrimitive']});
            if datatype:
                datatype = datatype.text;
            else:
                if hasattr(lastPortDecl.children[1], 'tag'):
                    datatype = lastPortDecl.children[1].text;
                else:
                    datatype = None;

            direction = lastPortDecl.children[0].text;
        elif name in portDeclarations:
            dimensions,direction,datatype = portDeclarations[name];

        #TODO print(anytree.RenderTree(port));
        #TODO print(port.children[0]);
        ports.append( Port(name, direction=direction, datatype=datatype, dimensions=dimensions) );

    return ports;

def process_files(parser: verible_verilog_syntax.VeribleVerilogSyntax, files: List[str]):
    modules = [];

    for f in files:
        try:
            data = parser.parse_file(f);
        except verible_verilog_syntax.Error as e:
            logging.error(f"Failed to parse {f}: {e}");
            continue;

        for module in data.tree.iter_find_all({"tag": "kModuleDeclaration"}):
            name = module.find({"tag": "kModuleHeader"});
            if name:
                name = name.find({"tag": ["SymbolIdentifier", "EscapedIdentifier"]},iter_=anytree.PreOrderIter);
                if name:
                    name = name.text;

            if name:
                logging.debug(f"[{name}]");

            ports = get_ports(module);
            if ports:
                for port in ports:
                    logging.debug(f"\t{port}");

            params = get_parameters(module);
            if params:
                for param in params:
                    logging.debug(f"\t# {param}");

            insts = get_instances(module);
            if insts:
                for inst in insts:
                    logging.debug(f"\t[{inst}]");
            modules.append( {'name':name, 'path':f, 'ports':ports, 'parameters':params, 'instances':insts} );

    # add "is_leaf" attribute
    for m in modules:
        m['is_leaf'] = m['instances'] is None;

    # add "is_root" attribute
    for m in modules:
        if 'is_root' not in m:
            m['is_root'] = True;
        if m['instances']:
            for s in [sm for sm in modules if sm['name'] in m['instances']]:
                s['is_root'] = False;

    roots = ','.join([m['name'] for m in modules if m['is_root']]);
    logging.debug(f"roots: {roots}");

    return modules;


def node_depth(node: anytree.Node):
    if not node:
        return -1;
    cnt = 0;
    p = node.parent;
    while p is not None:
        cnt += 1;
        p = p.parent;
    return cnt;


def get_module_hierarchy(modules: List, root: str):
    if not modules:
        return None;

    module = None;
    for m in modules:
        if m['name'] == root:
            module = m;
            break;

    if not module:
        return None;

    mdict = {};
    for m in modules:
        mdict[m['name']] = m;

    r = anytree.Node(module['name']);
    nodes = [];
    nodes.append( r );
    while len(nodes) > 0:
        n = nodes.pop(0);

        # sanity check
        if node_depth(n) > len(modules):
            logging.error('Something wrong with module hierarchy!');
            raise Exception('Too deep module hierarchy, cycle may exist.');

        m = mdict[n.name];
        if not m['is_leaf']:
            l = [];
            for i in m['instances']:
                if i not in l:
                    l.append(i);
                    s = anytree.Node(i, parent=n);
                    nodes.append( s );

    return r;


# returns module file paths in a reverse dependency order
def get_files_in_hierarchy(modules: List, root: str):
    hierarchy = get_module_hierarchy(modules, root);
    paths = [];

    if hierarchy:
        l = [node.name for node in anytree.PreOrderIter(hierarchy)];
        l.reverse();

        pdict = {};
        for m in modules:
            pdict[m['name']] = m['path'];

        for n in l:
            if n in pdict:
                p = pdict[n];
                if p not in paths:
                    paths.append(p);
                del pdict[n];
    return paths;


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Extracts SystemVerilog/Verilog module interface into IP-XACT 2014.');
    parser.add_argument('-o', '--output', dest='output', required=False, type=pathlib.Path,
            help='IP-XACT output file, stdout if not given.');
    parser.add_argument('-m', '--module', dest='module', required=False, type=str,
            help='Name of the root module.');
    parser.add_argument('--xact', dest='xact', required=False, type=pathlib.Path,
            help='IP-XACT 2014 to be updated with module information.')
    parser.add_argument('--verible', dest='verible', required=False, type=pathlib.Path,
            help='Path to `verible-verilog-syntax` binary.');
    parser.add_argument('--xact-library', dest='library', required=False, type=str,
            help='IP-XACT component library name.');
    parser.add_argument('--xact-version', dest='version', required=False, type=str,
            help='IP-XACT component version number.');
    parser.add_argument('--xact-vendor', dest='vendor', required=False, type=str,
            help='IP-XACT component vendor name.');
    parser.add_argument('--rwd', dest='rwd', required=False, type=pathlib.Path,
            help='Relative Working Directory (RWD), which to make file paths relative to. Applies only if `output` not specified.');
    parser.add_argument('--log-level', dest='loglevel', required=False, type=str, default='ERROR',
            help='Logging severity, one of: DEBUG, INFO, WARNING, ERROR, FATAL. Defaults to ERROR.');
    parser.add_argument('-l', '--log-file', dest='logfile', required=False, type=pathlib.Path, default=None,
            help='Path to a log file. Defaults to stderr if none given.');
    parser.add_argument('files', type=pathlib.Path, nargs='+',
            help='List of SystemVerilog/Verilog files to process.');

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

    # `verible` parser binary
    parser_path='verible-verilog-syntax';
    if opts.verible:
        parser_path = str(opts.verible);

    # input SystemVerilog/Verilog file
    file_paths = [str(f) for f in opts.files];

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

    parser = verible_verilog_syntax.VeribleVerilogSyntax(executable=parser_path);
    modules = process_files(parser, file_paths);

    if len(modules) > 0:
        module = None;
        if opts.module:
            for m in modules:
                if m['name'] == opts.module:
                    module = m;
                    break;
            if not module:
                logging.error(f'Failed to find module \'{opts.module}\'!');
                sys.exit(1);
        else:
            # use the first root module
            roots = [m for m in modules if m['is_root']];
            module = roots[0];

        logging.debug(anytree.RenderTree( get_module_hierarchy(modules, module['name']) ));

        xactns = {'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
        'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
        };
        ns = XactNamespace();

        comp = et.Element(ns.compileTag('component'), xactns);

        # default XML element values (unless relevant options defined
        # through CLI options)
        defaults = {'version':'0.0.0', 'name':'manifest'};

        for tag in ['vendor', 'library', 'name', 'version']:
            e = et.SubElement(comp, ns.compileTag(tag));

            # treat `name` element specifically
            if tag == 'name':
                e.text = module['name'];
                continue;

            if hasattr(opts,tag) and getattr(opts,tag) is not None:
                e.text = str(getattr(opts,tag));
            elif tag in defaults:
                e.text = defaults[tag];
            else:
                e.text = tag;

        model = et.SubElement(comp, ns.compileTag('model'));

        views = et.SubElement(model, ns.compileTag('views'));

        rtlView = et.SubElement(views, ns.compileTag('view'));
        viewName = et.SubElement(rtlView, ns.compileTag('name'));
        viewName.text = 'rtl';
        compInstRef = et.SubElement(rtlView, ns.compileTag('componentInstantiationRef'));
        compInstRef.text = viewName.text + '_implementation';

        insts = et.SubElement(model, ns.compileTag('instantiations'));
        compInst = et.SubElement(insts, ns.compileTag('componentInstantiation'));
        instName = et.SubElement(compInst, ns.compileTag('name'));
        instName.text = compInstRef.text;

        if 'parameters' in module:
            params  = et.SubElement(compInst, ns.compileTag('moduleParameters'));
            for param in module['parameters']:
                params.append( param.etXact() );

        instFileSetRef = et.SubElement(compInst, ns.compileTag('fileSetRef'));
        instFileSetRef = et.SubElement(instFileSetRef, ns.compileTag('localName'));
        instFileSetRef.text = viewName.text + '_files';

        if 'ports' in module:
            ports  = et.SubElement(model, ns.compileTag('ports'));
            for port in module['ports']:
                ports.append( port.etXact() );

        fileSets = et.SubElement(comp, ns.compileTag('fileSets'));
        fileSet = et.SubElement(fileSets, ns.compileTag('fileSet'));
        fileSetName = et.SubElement(fileSet, ns.compileTag('name'));
        fileSetName.text = instFileSetRef.text;

        for p in get_files_in_hierarchy(modules, module['name']):
            f = pathlib.Path(p);
            fileSetFile = et.SubElement(fileSet, ns.compileTag('file'));
            fileSetFileName = et.SubElement(fileSetFile, ns.compileTag('name'));

            if outputDir:
                fileSetFileName.text = str(f.relative_to(outputDir));
            else:
                fileSetFileName.text = str(f.absolute());

            fileSetFileType = et.SubElement(fileSetFile, ns.compileTag('fileType'));
            fileExt = f.suffix;
            if fileExt:
                if fileExt == 'v' or fileExt == 'vh':
                    fileSetFileType.text = 'verilogSource';
                else:
                    fileSetFileType.text = 'systemVerilogSource';
            else:
                fileSetFileType.text = 'systemVerilogSource';

        _pretty_print(comp);
        tree = et.ElementTree(comp);

        if opts.output:
            with open(str(opts.output), 'w') as f:
                tree.write(f, encoding='unicode', xml_declaration=True);
        else:
            tree.write(sys.stdout, encoding='unicode', xml_declaration=True);

