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
import logging

# add required source code into PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.vlog2ipxact import Port, PreOrderDepthTreeIterator, TypeDimension


def parse_verilog(vlogSyntax):
    parser_path='verible-verilog-syntax';
    parser = verible_verilog_syntax.VeribleVerilogSyntax(executable=parser_path);
    data = parser.parse_string(vlogSyntax);
    return data;


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


def get_ports(module_data: verible_verilog_syntax.SyntaxData):
    ports = [];

    # in Verilog syntax, port direction and type are defined outside
    # module port list. In Verible CST, this information is contained
    # within a 'kModuleItemList' node.
    portDeclarations = {};
    moduleItems = module_data.find({'tag':['kModuleItemList']});
    if moduleItems:
        declSpecs = {
                'kModulePortDeclaration': {
                    'portItem': 'kIdentifierUnpackedDimensions',
                    'typeItem': None,
                    },
                'kNetDeclaration': {
                    'portItem': 'kNetVariable',
                    'typeItem': 'kDataType',
                    'typeIterClass': PreOrderDepthTreeIterator,
                    'typeIterKwargs': {'depth':1},
                    },
                'kDataDeclaration': {
                    'portItem': 'kRegisterVariable',
                    'typeItem': 'kDataTypePrimitive',
                    'typeIterClass': verible_verilog_syntax.LevelOrderTreeIterator,
                    'typeIterKwargs': {}, # don't care
                    },
                };
        for decl in moduleItems.iter_find_all({'tag': ['kModulePortDeclaration', 'kNetDeclaration', 'kDataDeclaration']}):
            # get packed dimensions
            _packedDimensions = None;
            for packedDimensions in decl.iter_find_all({'tag': ['kPackedDimensions']}):
                _packedDimensions = get_dimensions(packedDimensions,_packedDimensions);

            if decl.tag in declSpecs:
                portItemName = declSpecs[decl.tag]['portItem'];
                datatypeItemName = declSpecs[decl.tag]['typeItem'];
            else:
                raise NotImplementedError('unexpected case');


            # go through individual port declarations
            for port in decl.iter_find_all({'tag': [portItemName]}):

                # get name
                name = port.find({"tag": ["SymbolIdentifier", "EscapedIdentifier"]});
                if name is None: continue;
                name = name.text;

                # sanity check
                # ('kModulePortDeclaration' shall come before any other kind of module items)
                if decl.tag == 'kModulePortDeclaration' and name in portDeclarations:
                    raise Exception(f'Module item \'{name}\' already exists!');

                # get direction
                direction = None;
                if decl.tag == 'kModulePortDeclaration':
                    direction = decl.children[0].text;
                elif name in portDeclarations:
                    direction = portDeclarations[name][1];

                # get data type
                datatype = None;
                if datatypeItemName is not None:
                    datatype = decl.find_all({'tag':[datatypeItemName]},
                            iter_ = declSpecs[decl.tag]['typeIterClass'],
                            **declSpecs[decl.tag]['typeIterKwargs'],
                            );
                    datatype = datatype[0].text;

                # get unpacked dimensions
                dimensions = None;
                for unpackedDimensions in port.iter_find_all({'tag': ['kUnpackedDimensions']}):
                    dimensions = get_dimensions(unpackedDimensions,dimensions);

                # add packed dimensions (if defined)
                if _packedDimensions is not None:
                    if dimensions:
                        dimensions += _packedDimensions;
                    else:
                        dimensions = _packedDimensions;

                # add port declaration into the list
                logging.debug(f'port declaration: {decl.tag}, name={name}, dir={direction}, type={datatype}, dims={dimensions}');
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


def test_vlog_multiple_ports():
    data = '''
    module test(
    input logic[7:0] a[0:1], b, c[1:4]
    );
    endmodule
    '''
    data = '''
    module test(a,b);
    input[0:1] a;
    inout[1:0] b;
    wire[1:0] b;
    endmodule
    '''
    data = '''
    module test(a,b,c,a1,b1,c1);
    input a[1:2],a1;
    inout[1:0] b,b1;
    output[7:0] c,c1[1:4];
    wire[1:0] b,b1;
    reg[7:0] c,c1[1:4];
    reg r;
    endmodule
    '''

    cst = parse_verilog(data);
    module = cst.tree.find({"tag": "kModuleDeclaration"});
    ports = get_ports(module);

    for port in ports:
        print( port.toDict() );


if __name__ == '__main__':

    # default logging setup
    logging.basicConfig(level=logging.ERROR);

    #test_single_input_typed_vector_multidim_packed_unpacked();
    test_vlog_multiple_ports()

