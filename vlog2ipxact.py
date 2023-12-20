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
import anytree
import logging
import argparse
import verible_verilog_syntax
import xml.etree.ElementTree as et
from typing import Iterable, Optional

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
        p = et.Element('ipxact:port');

        name = et.SubElement(p, 'ipxact:name');
        name.text = self.name;

        signal = et.SubElement(p, 'ipxact:wire');

        direction = et.SubElement(signal, 'ipxact:direction');
        if self.direction in Port.lutDirection:
            direction.text = Port.lutDirection[self.direction];
        else:
            #TODO report error/warning
            direction.text = Port.lutDirection['input'];

        if self.dimensions and len(self.dimensions) > 0:
            vectors= et.SubElement(signal, 'ipxact:vectors');
            for dimension in self.dimensions:
                vectors.append(dimension.etXact());

        if self.datatype:
            wiredefs = et.SubElement(signal, 'ipxact:wireTypeDefs');
            wiredef = et.SubElement(wiredefs, 'ipxact:wireTypeDef');
            typename = et.SubElement(wiredef, 'ipxact:typeName');
            typename.text = self.datatype;

        return p;


def get_ports(module_data: verible_verilog_syntax.SyntaxData):
    ports = [];
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
            portDimensions = lastPortDecl.find({'tag': ['kDeclarationDimensions']});
            if portDimensions:
                dimensions = [];
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

            datatype = lastPortDecl.find({'tag': ['kDataTypePrimitive']});
            if datatype:
                datatype = datatype.text;
            else:
                if hasattr(lastPortDecl.children[1], 'tag'):
                    datatype = lastPortDecl.children[1].text;
                else:
                    datatype = None;

            direction = lastPortDecl.children[0].text;
        #TODO print(anytree.RenderTree(port));
        #TODO print(port.children[0]);
        ports.append( Port(name, direction=direction, datatype=datatype, dimensions=dimensions) );

    return ports;

def process_file_data(path: str, data: verible_verilog_syntax.SyntaxData):
    modules = [];

    for module in data.tree.iter_find_all({"tag": "kModuleDeclaration"}):
        name = module.find({"tag": "kModuleHeader"});
        if name:
            name = name.find({"tag": ["SymbolIdentifier", "EscapedIdentifier"]},iter_=anytree.PreOrderIter);
            if name:
                name = name.text;

        if name:
            print(f"[{name}]");

        ports = get_ports(module);
        if ports:
            for port in ports:
                print(f"\t{port}");

        modules.append( {'name':name, 'ports':ports} );
    return modules;

parser = argparse.ArgumentParser(description='Creates IP-XACT 2014 file from a SystemVerilog file.')
parser.add_argument('-o', '--output', dest='output', required=False, type=pathlib.Path,
        help='IP-XACT output file, stdout if not given')
parser.add_argument('-i', '--input', dest='infile', required=True, type=pathlib.Path,
        help='SystemVerilog')

# parse CLI options
opts = parser.parse_args()

# setup logging level
logging.basicConfig(level=logging.DEBUG)

parser_path = sys.argv[1];
file_path = sys.argv[2];

parser = verible_verilog_syntax.VeribleVerilogSyntax(executable=parser_path);
try:
    file_data = parser.parse_file(file_path);
except verible_verilog_syntax.Error as e:
    logging.error(f"Failed to parse {file_path}: {e}");
    sys.exit(1);

modules = process_file_data(file_path, file_data);

if len(modules) > 0:
    ns = {'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
    'xmlns:ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014",
    'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
    };

    module = modules[0];
    comp = et.Element('ipxact:component', ns);

    vendor = et.SubElement(comp, 'ipxact:vendor');
    library = et.SubElement(comp, 'ipxact:library');
    name = et.SubElement(comp, 'ipxact:name');
    version = et.SubElement(comp, 'ipxact:version');

    vendor.text = 'vendor';
    library.text = 'library';
    name.text = 'name';
    version.text = '1.0.0';

    model = et.SubElement(comp, 'ipxact:model');

    if 'ports' in module:
        ports  = et.SubElement(model, 'ipxact:ports');
        for port in module['ports']:
            ports.append( port.etXact() );

    _pretty_print(comp);
    tree = et.ElementTree(comp);
    #et.indent(tree, space="\t", level=0);
    et.dump(tree);
    with open('output.xml', 'wb') as f:
        tree.write(f)
