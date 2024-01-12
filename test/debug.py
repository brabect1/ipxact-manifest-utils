# Copyright 2024 Tomas Brabec
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

import os
import sys
import verible_verilog_syntax
import anytree

# add required source code into PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.vlog2ipxact import Port, PreOrderDepthTreeIterator, TypeDimension


def parse_verilog(vlogSyntax):
    parser_path='verible-verilog-syntax';
    parser = verible_verilog_syntax.VeribleVerilogSyntax(executable=parser_path);
    data = parser.parse_string(vlogSyntax);
    return data;


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
            for portDimensions in lastPortDecl.iter_find_all({'tag': ['kDeclarationDimensions']}):
                print(anytree.RenderTree(portDimensions));
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


def test_single_input_typed_vector_multidim_packed_unpacked():
    data = '''
    module foo(
        input logic[7:0][3:0] b[1:3][4:5]
    );
    endmodule
    '''

    cst = parse_verilog(data);
    module = cst.tree.find({"tag": "kModuleDeclaration"});
    ports = get_ports(module);

    print( ports[0].toDict() );


if __name__ == '__main__':
    test_single_input_typed_vector_multidim_packed_unpacked();

