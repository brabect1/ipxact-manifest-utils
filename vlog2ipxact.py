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
import verible_verilog_syntax
import xml.etree.ElementTree as et

# https://stackoverflow.com/a/65808327
def _pretty_print(current, parent=None, index=-1, depth=0):
    for i, node in enumerate(current):
        _pretty_print(node, current, i, depth + 1)
    if parent is not None:
        if index == 0:
            parent.text = '\n' + ('\t' * depth)
        else:
            parent[index - 1].tail = '\n' + ('\t' * depth)
        if index == len(parent) - 1:
            current.tail = '\n' + ('\t' * (depth - 1))

class Port(object):

    attrs = ['direction', 'datatype', 'dimensions', 'name'];

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
                attrs.append(val);

        return ' '.join(attrs);

    def etXact(self):
        p = et.Element('ipxact:port');

        n = et.SubElement(p, 'ipxact:name');
        n.text = self.name;

        d = et.Element('ipxact:direction');
        d.text = self.direction;

        s = et.SubElement(p, 'ipxact:wire');
        s.append(d);

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
            nodes = lastPortDecl.find_all({'tag': ['kDimensionRange']});
            if len(nodes) > 0:
                dimensions = ''.join([node.text for node in nodes]);

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


parser_path = sys.argv[1];
file_path = sys.argv[2];

parser = verible_verilog_syntax.VeribleVerilogSyntax(executable=parser_path);
file_data = parser.parse_file(file_path);

modules = process_file_data(file_path, file_data);

if len(modules) > 0:
    ns = {'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
    'xmlns:ipxact':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014",
    'xsi:schemaLocation':"http://www.accellera.org/XMLSchema/IPXACT/1685-2014 http://www.accellera.org/XMLSchema/IPXACT/1685-2014/index.xsd"
    };

    module = modules[0];
    comp = et.Element('ipxact:component', ns);
    model = et.SubElement(comp, 'ipxact:model');

    if 'ports' in module:
        ports  = et.SubElement(model, 'ipxact:ports');
        for port in module['ports']:
            ports.append( port.etXact() );

    _pretty_print(comp);
    tree = et.ElementTree(comp);
    #et.indent(tree, space="\t", level=0);
    et.dump(tree);
